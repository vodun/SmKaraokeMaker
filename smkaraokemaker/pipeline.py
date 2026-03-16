"""Оркестратор пайплайна SMKaraokeMaker."""

from __future__ import annotations

import logging
import signal
import time
from typing import Callable

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
    TaskID,
)

from smkaraokemaker.config import KaraokeConfig, PipelineContext
from smkaraokemaker.utils.temp_manager import TempManager
from smkaraokemaker.utils.ffmpeg_utils import probe_media
from smkaraokemaker.utils.validators import (
    validate_input_file,
    validate_ffmpeg_available,
    validate_disk_space,
    ValidationError,
)

logger = logging.getLogger(__name__)
console = Console()

# (название, модуль, функция, имя шага для кэша)
STEPS: list[tuple[str, str, str]] = [
    ("Извлечение аудио", "modules.audio_extractor", "extract_audio"),
    ("Разделение вокала и музыки", "modules.vocal_separator", "separate_vocals"),
    ("Распознавание текста и таймингов", "modules.speech_recognizer", "recognize_speech"),
    ("Генерация караоке-субтитров", "modules.subtitle_renderer", "render_subtitles"),
    ("Рендер финального видео", "modules.video_composer", "compose_video"),
]


def run_pipeline(config: KaraokeConfig) -> None:
    """Запустить полный пайплайн обработки."""
    if config.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s: %(message)s")

    # Валидация
    try:
        validate_input_file(config.input_video)
        validate_ffmpeg_available()
        validate_disk_space(config.input_video)
    except ValidationError as e:
        console.print(f"[bold red]Ошибка:[/] {e}")
        raise SystemExit(1)

    # Проверка ML-зависимостей
    _check_ml_dependencies()

    # Метаданные для информации
    info = probe_media(config.input_video)
    if not info["has_audio"]:
        console.print("[bold red]Ошибка:[/] Файл не содержит аудиодорожки")
        raise SystemExit(1)

    has_video = info["has_video"]
    duration = info["duration"]

    # Для видео-входа устанавливаем resolution из метаданных
    if has_video:
        config.resolution = f"{info['width']}x{info['height']}"

    if has_video:
        console.print(
            f"[bold]Входной файл:[/] {config.input_video.name} "
            f"({info['width']}x{info['height']}, "
            f"{duration:.0f} сек, {info['fps']:.0f} fps)"
        )
    else:
        console.print(
            f"[bold]Входной файл:[/] {config.input_video.name} "
            f"(аудио, {duration:.0f} сек) → видео {config.resolution}"
        )
    console.print()

    with TempManager(config.input_video, keep_temp=config.keep_temp) as tm:
        ctx = PipelineContext(
            input_video=config.input_video,
            output_video=config.output_video,
            temp_dir=tm.temp_dir,
            config=config,
            has_video=has_video,
        )

        # Восстановление контекста из кэша
        _restore_context_from_cache(ctx, tm)

        total = len(STEPS)
        interrupted = False

        # Обработка Ctrl+C (первый раз — мягкое, второй — принудительное)
        original_handler = signal.getsignal(signal.SIGINT)

        def _handle_interrupt(signum, frame):
            nonlocal interrupted
            if interrupted:
                console.print("\n[bold red]Принудительное завершение.[/]")
                signal.signal(signal.SIGINT, original_handler)
                raise KeyboardInterrupt
            interrupted = True
            console.print("\n[yellow]Прерывание... завершаю текущий шаг. Нажмите Ctrl+C ещё раз для принудительного выхода.[/]")

        signal.signal(signal.SIGINT, _handle_interrupt)

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                for i, (name, module_path, func_name) in enumerate(STEPS, 1):
                    if interrupted:
                        break

                    task = progress.add_task(f"[{i}/{total}] {name}", total=100)

                    # Проверяем кэш
                    if tm.is_step_done(func_name):
                        progress.update(
                            task,
                            completed=100,
                            description=f"[{i}/{total}] {name} [dim](кэш)[/dim]",
                        )
                        continue

                    start_time = time.time()

                    module = __import__(
                        f"smkaraokemaker.{module_path}", fromlist=[func_name]
                    )
                    step_func = getattr(module, func_name)
                    ctx = step_func(ctx)
                    elapsed = time.time() - start_time

                    # Определяем выходной файл для кэша
                    output_file = _get_step_output(ctx, func_name)
                    tm.mark_step_done(func_name, output_file)

                    progress.update(task, completed=100)

                    if config.verbose:
                        console.print(
                            f"  [dim]└ {name}: {elapsed:.1f} сек[/dim]"
                        )

            if interrupted:
                console.print("[yellow]Прервано. Для продолжения запустите ту же команду.[/]")
                raise SystemExit(130)

            console.print()
            size_mb = config.output_video.stat().st_size / (1024 * 1024)
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            console.print(
                f"[bold green]✓ Готово:[/] {config.output_video} "
                f"({size_mb:.0f} МБ, {minutes}:{seconds:02d})"
            )

        except (KeyboardInterrupt, SystemExit):
            raise
        except NotImplementedError as e:
            console.print(f"\n[yellow]Шаг ещё не реализован:[/] {e}")
            raise SystemExit(1)
        except Exception as e:
            console.print(f"\n[bold red]Ошибка:[/] {e}")
            if config.verbose:
                console.print_exception()
            raise SystemExit(1)
        finally:
            signal.signal(signal.SIGINT, original_handler)


def _get_step_output(ctx: PipelineContext, func_name: str) -> "Path | None":
    """Получить путь выходного файла для данного шага."""
    from pathlib import Path

    mapping: dict[str, Path | None] = {
        "extract_audio": ctx.audio_path,
        "separate_vocals": ctx.vocals_path,
        "recognize_speech": ctx.temp_dir / "transcript.json" if ctx.transcript else None,
        "render_subtitles": ctx.subtitle_path,
        "compose_video": ctx.output_video,
    }
    return mapping.get(func_name)


def _restore_context_from_cache(ctx: PipelineContext, tm: TempManager) -> None:
    """Восстановить контекст из кэшированных файлов."""
    audio = tm.get_path("audio_full.wav")
    if audio.exists():
        ctx.audio_path = audio

    vocals = tm.get_path("vocals.wav")
    if vocals.exists():
        ctx.vocals_path = vocals

    instrumental = tm.get_path("instrumental.wav")
    if instrumental.exists():
        ctx.instrumental_path = instrumental

    transcript_file = tm.get_path("transcript.json")
    if transcript_file.exists():
        import json
        from smkaraokemaker.models import Segment

        try:
            data = json.loads(transcript_file.read_text())
            ctx.transcript = [Segment.model_validate(s) for s in data]
        except Exception:
            pass

    subtitle = tm.get_path("karaoke.ass")
    if subtitle.exists():
        ctx.subtitle_path = subtitle


def _check_ml_dependencies() -> None:
    """Проверить ML-зависимости перед запуском пайплайна."""
    errors = []

    try:
        import torch
    except ImportError:
        errors.append("PyTorch не установлен")

    try:
        from demucs.pretrained import get_model
        from demucs.apply import apply_model
        from demucs.audio import AudioFile
    except ImportError:
        errors.append("Demucs не установлен")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        errors.append("faster-whisper не установлен")

    # Проверяем FFmpeg фильтр ass
    import subprocess
    r = subprocess.run(["ffmpeg", "-filters"], capture_output=True, text=True)
    has_ass = any(
        line.strip().startswith(".. ass") or line.strip().startswith("T. ass")
        for line in r.stdout.splitlines()
    )
    if not has_ass:
        errors.append("FFmpeg без поддержки libass (нужен для субтитров)")

    if errors:
        console.print("[bold red]Предстартовая проверка не пройдена:[/]")
        for err in errors:
            console.print(f"  [red]✗[/] {err}")
        console.print("\n[dim]Установите зависимости: pip install 'smkaraokemaker[ml]'")
        console.print("Проверьте всё: smkaraokemaker check[/]")
        raise SystemExit(1)
