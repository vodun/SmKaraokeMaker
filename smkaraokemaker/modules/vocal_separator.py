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
        logger.info("Demucs: модель=%s, устройство=%s", self.MODEL, device)

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

        # Сепарация
        sources = apply_model(model, wav[None], device=device, progress=True)[0]

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


def get_separator(name: str) -> SeparatorBackend:
    """Фабрика для получения бэкенда сепарации."""
    backends = {
        "demucs": DemucsBackend,
        "spleeter": SpleeterBackend,
    }
    cls = backends.get(name)
    if cls is None:
        available = ", ".join(backends.keys())
        raise ValueError(f"Неизвестный сепаратор '{name}'. Доступные: {available}")
    return cls()


def separate_vocals(ctx: PipelineContext) -> PipelineContext:
    """Разделить аудио на вокал и инструментал."""
    if ctx.audio_path is None:
        raise RuntimeError("Аудиофайл не найден. Сначала выполните извлечение аудио.")

    backend = get_separator(ctx.config.separator)
    vocals_path, instrumental_path = backend.separate(ctx.audio_path, ctx.temp_dir)

    ctx.vocals_path = vocals_path
    ctx.instrumental_path = instrumental_path
    return ctx
