"""Разделение аудио на вокал и инструментальную дорожку."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

import numpy as np
import wave

from smkaraokemaker.config import PipelineContext

logger = logging.getLogger(__name__)


def _save_wav(tensor, path: Path, samplerate: int) -> None:
    """Сохранить torch.Tensor в WAV через стандартный модуль wave (без torchaudio)."""
    import torch

    # tensor shape: (channels, samples)
    wav = tensor.clamp(-1, 1)
    # Конвертируем в int16
    data = (wav.numpy() * 32767).astype(np.int16)
    channels = data.shape[0]
    # Interleave каналов: (channels, samples) → (samples, channels) → flatten
    data = data.T.flatten()

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(samplerate)
        wf.writeframes(data.tobytes())


class SeparatorBackend(Protocol):
    """Протокол для бэкенда сепарации."""

    def separate(self, audio_path: Path, output_dir: Path) -> tuple[Path, Path]:
        """Разделить аудио на вокал и инструментал.

        Returns:
            (vocals_path, instrumental_path)
        """
        ...


class DemucsBackend:
    """Сепарация через Demucs (htdemucs_ft)."""

    MODEL = "htdemucs_ft"

    def __init__(self, shifts: int = 1, overlap: float = 0.25) -> None:
        self.shifts = shifts
        self.overlap = overlap

    def separate(self, audio_path: Path, output_dir: Path) -> tuple[Path, Path]:
        try:
            import torch
            from demucs.pretrained import get_model
            from demucs.apply import apply_model
            from demucs.audio import AudioFile
        except ImportError as e:
            raise RuntimeError(
                f"Demucs не установлен. Установите: pip install 'smkaraokemaker[ml]'\n{e}"
            )

        device = self._get_device()
        logger.info(
            "Demucs: модель=%s, устройство=%s, shifts=%d, overlap=%.2f",
            self.MODEL, device, self.shifts, self.overlap,
        )

        # Загрузка модели
        model = get_model(self.MODEL)
        model.to(device)

        # Загрузка аудио через demucs AudioFile (не зависит от torchcodec)
        wav = AudioFile(audio_path).read(
            streams=0, samplerate=model.samplerate, channels=model.audio_channels
        )

        # Нормализация
        ref = wav.mean(0)
        wav = (wav - ref.mean()) / ref.std()
        wav = wav.to(device)

        # Сепарация с улучшенными параметрами:
        # shifts > 1 — усреднение нескольких прогонов со сдвигом (лучше изоляция вокала)
        # overlap — перекрытие сегментов (меньше артефактов на стыках)
        sources = apply_model(
            model, wav[None], device=device, progress=True,
            shifts=self.shifts, overlap=self.overlap,
        )[0]

        # Денормализация
        sources = sources * ref.std() + ref.mean()

        # Demucs htdemucs_ft: sources = drums, bass, other, vocals
        source_names = model.sources
        vocals_idx = source_names.index("vocals")

        vocals = sources[vocals_idx].cpu()

        # Инструментал = всё кроме вокала
        instrumental = sum(
            sources[i].cpu() for i in range(len(source_names)) if i != vocals_idx
        )

        vocals_path = output_dir / "vocals.wav"
        instrumental_path = output_dir / "instrumental.wav"

        _save_wav(vocals, vocals_path, model.samplerate)
        _save_wav(instrumental, instrumental_path, model.samplerate)

        logger.info("Сепарация завершена: %s, %s", vocals_path, instrumental_path)
        return vocals_path, instrumental_path

    @staticmethod
    def _get_device() -> str:
        import torch

        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"


class SpleeterBackend:
    """Сепарация через Spleeter (2stems). Заглушка для будущей реализации."""

    def separate(self, audio_path: Path, output_dir: Path) -> tuple[Path, Path]:
        raise NotImplementedError(
            "Spleeter ещё не реализован. Используйте --separator demucs"
        )


def get_separator(name: str, quality: str = "high") -> SeparatorBackend:
    """Фабрика для получения бэкенда сепарации.

    Параметры качества для Demucs:
      draft:  shifts=0, overlap=0.25  — быстро, базовое качество
      high:   shifts=1, overlap=0.25  — хороший баланс скорость/качество
      ultra:  shifts=5, overlap=0.5   — максимальное качество изоляции вокала
    """
    quality_params = {
        "draft": {"shifts": 0, "overlap": 0.25},
        "high": {"shifts": 1, "overlap": 0.25},
        "ultra": {"shifts": 5, "overlap": 0.5},
    }
    params = quality_params.get(quality, quality_params["high"])

    backends = {
        "demucs": lambda: DemucsBackend(**params),
        "spleeter": lambda: SpleeterBackend(),
    }
    factory = backends.get(name)
    if factory is None:
        available = ", ".join(backends.keys())
        raise ValueError(f"Неизвестный сепаратор '{name}'. Доступные: {available}")
    return factory()


def separate_vocals(ctx: PipelineContext) -> PipelineContext:
    """Разделить аудио на вокал и инструментал."""
    if ctx.audio_path is None:
        raise RuntimeError("Аудиофайл не найден. Сначала выполните извлечение аудио.")

    backend = get_separator(ctx.config.separator, ctx.config.quality.value)
    vocals_path, instrumental_path = backend.separate(ctx.audio_path, ctx.temp_dir)

    ctx.vocals_path = vocals_path
    ctx.instrumental_path = instrumental_path
    return ctx
