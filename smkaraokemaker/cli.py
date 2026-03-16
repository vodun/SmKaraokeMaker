"""CLI interface for SMKaraokeMaker."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from smkaraokemaker import __version__
from smkaraokemaker.config import KaraokeConfig, QualityProfile

console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"SMKaraokeMaker v{__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="smkaraokemaker",
    help="Karaoke video generator from music videos.",
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
    version: Annotated[
        Optional[bool],
        typer.Option("--version", callback=_version_callback, is_eager=True),
    ] = None,
) -> None:
    """SMKaraokeMaker — karaoke video generator from music videos."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command("run")
def run(
    input_video: Annotated[
        Path,
        typer.Argument(help="Path to media file (video or audio)", exists=True),
    ],
    output: Annotated[
        Optional[Path],
        typer.Option("-o", "--output", help="Path to output file"),
    ] = None,
    lang: Annotated[
        str,
        typer.Option("--lang", help="Recognition language (ISO 639-1)"),
    ] = "auto",
    model: Annotated[
        str,
        typer.Option("--model", help="Whisper model size"),
    ] = "large-v3",
    font: Annotated[
        Optional[Path],
        typer.Option("--font", help="Path to .ttf font for subtitles"),
    ] = None,
    font_size: Annotated[
        int,
        typer.Option("--font-size", help="Font size in pixels"),
    ] = 48,
    color_active: Annotated[
        str,
        typer.Option("--color-active", help="Current word color (hex)"),
    ] = "#FFD700",
    color_inactive: Annotated[
        str,
        typer.Option("--color-inactive", help="Upcoming words color (hex)"),
    ] = "#FFFFFF",
    color_done: Annotated[
        str,
        typer.Option("--color-done", help="Already sung words color (hex)"),
    ] = "#AAAAAA",
    position: Annotated[
        str,
        typer.Option("--position", help="Text position: top, center, bottom"),
    ] = "bottom",
    separator: Annotated[
        str,
        typer.Option("--separator", help="Separation engine: demucs or spleeter"),
    ] = "demucs",
    lyrics: Annotated[
        Optional[Path],
        typer.Option("--lyrics", help="Pre-made lyrics file (.txt / .lrc)"),
    ] = None,
    keep_temp: Annotated[
        bool,
        typer.Option("--keep-temp", help="Keep intermediate files"),
    ] = False,
    quality: Annotated[
        QualityProfile,
        typer.Option("--quality", help="Output quality: draft, high, ultra"),
    ] = QualityProfile.HIGH,
    resolution: Annotated[
        str,
        typer.Option("--resolution", help="Video resolution for audio input (WxH)"),
    ] = "1280x720",
    verbose: Annotated[
        bool,
        typer.Option("-v", "--verbose", help="Verbose output"),
    ] = False,
) -> None:
    """Convert a media file (video or audio) to karaoke."""
    from smkaraokemaker.utils.validators import is_audio_only_format

    output_path = output or input_video.with_stem(f"{input_video.stem}_karaoke")
    # Force .mp4 extension for audio input
    if is_audio_only_format(input_video) and output_path.suffix.lower() != ".mp4":
        output_path = output_path.with_suffix(".mp4")

    config = KaraokeConfig(
        input_video=input_video,
        output_video=output_path,
        lang=lang,
        model=model,
        font=font,
        font_size=font_size,
        color_active=color_active,
        color_inactive=color_inactive,
        color_done=color_done,
        position=position,
        separator=separator,
        lyrics=lyrics,
        keep_temp=keep_temp,
        quality=quality,
        resolution=resolution,
        verbose=verbose,
    )

    from smkaraokemaker.pipeline import run_pipeline

    run_pipeline(config)


@app.command("check")
def check_dependencies() -> None:
    """Check all dependencies and readiness."""
    console.print(f"[bold]SMKaraokeMaker v{__version__} — dependency check\n")

    all_ok = True

    def _check(name: str, check_fn, fix: str = "") -> bool:
        nonlocal all_ok
        try:
            result = check_fn()
            console.print(f"  [green]✓[/] {name}: {result}")
            return True
        except Exception as e:
            all_ok = False
            msg = f"  [red]✗[/] {name}: {e}"
            if fix:
                msg += f"\n    [dim]→ {fix}[/dim]"
            console.print(msg)
            return False

    import sys
    _check("Python", lambda: f"{sys.version.split()[0]}")

    import shutil
    def check_ffmpeg():
        if shutil.which("ffmpeg") is None:
            raise RuntimeError("not found")
        import subprocess
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        ver = r.stdout.split("\n")[0].split(" ")[2] if r.stdout else "unknown"
        return ver
    _check("FFmpeg", check_ffmpeg, "brew tap homebrew-ffmpeg/ffmpeg && brew install homebrew-ffmpeg/ffmpeg/ffmpeg")

    def check_libass():
        import subprocess
        r = subprocess.run(["ffmpeg", "-filters"], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            if line.strip().startswith(".. ass") or line.strip().startswith("T. ass"):
                return "available"
        raise RuntimeError("ass filter not found")
    _check("FFmpeg libass", check_libass, "brew install homebrew-ffmpeg/ffmpeg/ffmpeg")

    def check_torch():
        import torch
        device = "MPS" if torch.backends.mps.is_available() else "CUDA" if torch.cuda.is_available() else "CPU"
        return f"{torch.__version__} ({device})"
    _check("PyTorch", check_torch, "pip install 'smkaraokemaker[ml]'")

    def check_demucs():
        from demucs.pretrained import get_model
        from demucs.apply import apply_model
        from demucs.audio import AudioFile, save_audio
        import demucs
        return demucs.__version__
    _check("Demucs", check_demucs, "pip install 'smkaraokemaker[ml]'")

    def check_whisper():
        from faster_whisper import WhisperModel
        import faster_whisper
        return faster_whisper.__version__
    _check("faster-whisper", check_whisper, "pip install 'smkaraokemaker[ml]'")

    def check_font():
        from smkaraokemaker.utils.fonts import get_default_font
        p = get_default_font()
        return str(p.name)
    _check("Default font", check_font)

    console.print()
    if all_ok:
        console.print("[bold green]All dependencies are in order. Ready to go!")
    else:
        console.print("[bold yellow]Some dependencies are missing. Fix them and run the check again.")
