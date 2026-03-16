"""Separating audio into vocals and instrumental tracks."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

import numpy as np
import wave

from smkaraokemaker.config import PipelineContext

logger = logging.getLogger(__name__)


def _save_wav(tensor, path: Path, samplerate: int) -> None:
    """Save torch.Tensor to WAV using the standard wave module (no torchaudio)."""
    import torch

    # tensor shape: (channels, samples)
    wav = tensor.clamp(-1, 1)
    # Convert to int16
    data = (wav.numpy() * 32767).astype(np.int16)
    channels = data.shape[0]
    # Interleave channels: (channels, samples) → (samples, channels) → flatten
    data = data.T.flatten()

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(samplerate)
        wf.writeframes(data.tobytes())


class SeparatorBackend(Protocol):
    """Protocol for separation backend."""

    def separate(self, audio_path: Path, output_dir: Path) -> tuple[Path, Path]:
        """Separate audio into vocals and instrumental.

        Returns:
            (vocals_path, instrumental_path)
        """
        ...


class DemucsBackend:
    """Separation via Demucs (htdemucs_ft)."""

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
                f"Demucs is not installed. Install: pip install 'smkaraokemaker[ml]'\n{e}"
            )

        device = self._get_device()
        logger.info(
            "Demucs: model=%s, device=%s, shifts=%d, overlap=%.2f",
            self.MODEL, device, self.shifts, self.overlap,
        )

        # Load model
        model = get_model(self.MODEL)
        model.to(device)

        # Load audio via demucs AudioFile (no torchcodec dependency)
        wav = AudioFile(audio_path).read(
            streams=0, samplerate=model.samplerate, channels=model.audio_channels
        )

        # Normalization
        ref = wav.mean(0)
        wav = (wav - ref.mean()) / ref.std()
        wav = wav.to(device)

        # Separation with improved parameters:
        # shifts > 1 — averaging multiple shifted passes (better vocal isolation)
        # overlap — segment overlap (fewer artifacts at boundaries)
        sources = apply_model(
            model, wav[None], device=device, progress=True,
            shifts=self.shifts, overlap=self.overlap,
        )[0]

        # Denormalization
        sources = sources * ref.std() + ref.mean()

        # Demucs htdemucs_ft: sources = drums, bass, other, vocals
        source_names = model.sources
        vocals_idx = source_names.index("vocals")

        vocals = sources[vocals_idx].cpu()

        # Instrumental = everything except vocals
        instrumental = sum(
            sources[i].cpu() for i in range(len(source_names)) if i != vocals_idx
        )

        vocals_path = output_dir / "vocals.wav"
        instrumental_path = output_dir / "instrumental.wav"

        _save_wav(vocals, vocals_path, model.samplerate)
        _save_wav(instrumental, instrumental_path, model.samplerate)

        logger.info("Separation complete: %s, %s", vocals_path, instrumental_path)
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
    """Separation via Spleeter (2stems). Stub for future implementation."""

    def separate(self, audio_path: Path, output_dir: Path) -> tuple[Path, Path]:
        raise NotImplementedError(
            "Spleeter is not yet implemented. Use --separator demucs"
        )


def get_separator(name: str, quality: str = "high") -> SeparatorBackend:
    """Factory for obtaining a separation backend.

    Quality parameters for Demucs:
      draft:  shifts=0, overlap=0.25  — fast, basic quality
      high:   shifts=1, overlap=0.25  — good speed/quality balance
      ultra:  shifts=5, overlap=0.5   — maximum vocal isolation quality
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
        raise ValueError(f"Unknown separator '{name}'. Available: {available}")
    return factory()


def separate_vocals(ctx: PipelineContext) -> PipelineContext:
    """Separate audio into vocals and instrumental."""
    if ctx.audio_path is None:
        raise RuntimeError("Audio file not found. Run audio extraction first.")

    backend = get_separator(ctx.config.separator, ctx.config.quality.value)
    vocals_path, instrumental_path = backend.separate(ctx.audio_path, ctx.temp_dir)

    ctx.vocals_path = vocals_path
    ctx.instrumental_path = instrumental_path
    return ctx
