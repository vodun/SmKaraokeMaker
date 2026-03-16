🌍 *English | [Русский](README.ru.md)*

# SMKaraokeMaker

**Karaoke video generator from music clips and audio files**

A CLI application for macOS that takes a music video or audio file as input and automatically converts it into a karaoke video: separates vocals from instrumentals, recognizes lyrics with word-level timestamps, overlays synchronized subtitles with current word highlighting, and outputs a ready-to-use MP4 file. For audio-only input, a black background video is generated automatically.

```
$ smkaraokemaker run input.mp4 -o karaoke_output.mp4

Input file: input.mp4 (1920x1080, 222 sec, 30 fps)

 [1/5] Extracting audio               ██████████ 100%  0:00:02
 [2/5] Separating vocals and music     ██████████ 100%  0:03:12
 [3/5] Recognizing text and timings    ██████████ 100%  0:01:45
 [4/5] Generating karaoke subtitles    ██████████ 100%  0:00:01
 [5/5] Rendering final video           ██████████ 100%  0:01:08

✓ Done: karaoke_output.mp4 (134 MB, 3:42)
```

---

## Features

- **Automatic vocal separation** — Demucs (htdemucs_ft) by Meta, best-in-class source separation quality
- **Word-level speech recognition** — faster-whisper (large-v3), supports 90+ languages
- **Karaoke subtitles** — ASS format with `\kf` tags for smooth left-to-right word fill effect
- **Caching** — completed steps are skipped on re-runs with the same input file
- **Apple Silicon** — native MPS acceleration support (PyTorch) on M1/M2/M3/M4
- **Audio file support** — accepts MP3, FLAC, WAV, OGG, M4A, AAC, WMA, Opus, AIFF — generates video with black background
- **Highly customizable** — colors, fonts, subtitle position, quality profiles, video resolution
- **Auto language detection** — or explicit selection via `--lang`

---

## Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| macOS | 12+ | Apple Silicon recommended |
| Python | 3.11+ | Runtime |
| FFmpeg | 6.0+ | Audio/video processing, **with libass support** |

### Installing FFmpeg with libass

The default `brew install ffmpeg` **does not include** ASS subtitle support. You need the version from a tap:

```bash
brew tap homebrew-ffmpeg/ffmpeg
brew install homebrew-ffmpeg/ffmpeg/ffmpeg
```

Verify support:

```bash
ffmpeg -filters 2>/dev/null | grep ass
# Should show: .. ass  V->V  Render ASS subtitles...
```

---

## Installation

### Quick start (recommended)

```bash
git clone https://github.com/vodun/SmKaraokeMaker.git
cd SmKaraokeMaker
./init.sh
```

The `init.sh` script automatically:
- Checks Python 3.11+ and Homebrew (offers to install if missing)
- Installs FFmpeg with libass support (via `homebrew-ffmpeg` tap)
- Creates a `.venv` virtual environment
- Installs all dependencies (core + ML + dev)
- Runs `smkaraokemaker check` to verify everything works

> **Important:** after `init.sh` completes (or when opening a new terminal), activate the environment:
> ```bash
> source .venv/bin/activate
> ```
> The `smkaraokemaker` command will then be available.

### Running

```bash
# Activate the environment (required for each new terminal session)
source .venv/bin/activate

# Verify everything works
smkaraokemaker check

# Create a karaoke video
smkaraokemaker run video.mp4

# Run tests
pytest
```

### Manual install

```bash
git clone https://github.com/vodun/SmKaraokeMaker.git
cd SmKaraokeMaker

# Install Python 3.12 (if you don't have 3.11+)
brew install python@3.12

# Install FFmpeg with libass
brew tap homebrew-ffmpeg/ffmpeg
brew install homebrew-ffmpeg/ffmpeg/ffmpeg

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install with ML dependencies
pip install -e ".[ml]"

# Or minimal install (no ML — for development/testing)
pip install -e ".[dev]"

# Verify dependencies
smkaraokemaker check
```

### Dependencies

**Core** (installed automatically):
- `typer` — CLI interface
- `rich` — progress bars and formatted output
- `pydantic` — data validation
- `ffmpeg-python` — FFmpeg wrapper
- `Pillow` — image processing
- `numpy` — array operations

**ML** (group `[ml]`):
- `torch` — ML backend (MPS on Apple Silicon)
- `demucs` — vocal separation (Meta)
- `faster-whisper` — speech recognition (CTranslate2)

---

## Usage

### Basic usage

```bash
smkaraokemaker run video.mp4
# Output: video_karaoke.mp4
```

### Specify output and language

```bash
smkaraokemaker run video.mp4 -o karaoke.mp4 --lang en
```

### Quick draft (for preview)

```bash
smkaraokemaker run video.mp4 --quality draft
```

### Custom colors

```bash
smkaraokemaker run video.mp4 \
  --color-active "#FF4444" \
  --color-inactive "#CCCCCC" \
  --color-done "#666666"
```

### Custom font and size

```bash
smkaraokemaker run video.mp4 --font /path/to/MyFont.ttf --font-size 64
```

### Verbose output (debugging)

```bash
smkaraokemaker run video.mp4 -v --keep-temp
```

### Check dependencies

```bash
smkaraokemaker check
```

---

## Flags and Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `INPUT_FILE` | path | — | Path to input media file: video or audio (required) |
| `-o, --output` | path | `<input>_karaoke.mp4` | Output file path |
| `--lang` | str | `auto` | Recognition language ([ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)) |
| `--model` | str | `large-v3` | Whisper model: `tiny`, `base`, `small`, `medium`, `large-v3` |
| `--font` | path | NotoSans-Bold | Path to .ttf font |
| `--font-size` | int | `64` | Font size (px) |
| `--color-active` | str | `#FFD700` | Current word color (gold) |
| `--color-inactive` | str | `#FFFFFF` | Upcoming words color (white) |
| `--color-done` | str | `#AAAAAA` | Sung words color (gray) |
| `--position` | str | `bottom` | Position: `top`, `center`, `bottom` |
| `--separator` | str | `demucs` | Separation engine: `demucs` |
| `--lyrics` | path | — | Pre-existing lyrics (.txt / .lrc) for forced alignment |
| `--keep-temp` | flag | `false` | Keep intermediate files |
| `--quality` | str | `high` | Profile: `draft`, `high`, `ultra` |
| `--resolution` | str | `1280x720` | Video resolution for audio-only input (e.g. `1920x1080`) |
| `-v, --verbose` | flag | `false` | Verbose logging |
| `--version` | flag | — | Show version |

---

## Quality Profiles

| Profile | FFmpeg Preset | CRF | Audio | Speed | Use case |
|---------|--------------|-----|-------|-------|----------|
| `draft` | ultrafast | 28 | 128k AAC | Fast | Preview, timing check |
| `high` | medium | 18 | 192k AAC | Medium | Default mode |
| `ultra` | slow | 14 | 320k AAC | Slow | Maximum quality |

---

## How It Works

### Architecture

A linear pipeline of 5 modules — each receives the output of the previous one:

```
input.mp4
    │
    ▼
[1. Audio Extractor]     FFmpeg → WAV (44100 Hz, 16-bit, stereo)
    │
    ▼
[2. Vocal Separator]     Demucs htdemucs_ft → vocals.wav + instrumental.wav
    │
    ▼
[3. Speech Recognizer]   faster-whisper → words + timestamps (word-level)
    │
    ▼
[4. Subtitle Renderer]   ASS generation with \kf tags (karaoke fill effect)
    │
    ▼
[5. Video Composer]      FFmpeg: video + instrumental + subtitles → MP4
    │
    ▼
karaoke_output.mp4
```

### Karaoke Effect

Subtitles use the ASS (Advanced SubStation Alpha) format with `\kf` tags — smooth left-to-right fill of each word synchronized with singing:

```ass
Dialogue: 0,0:01:05.00,0:01:10.00,Karaoke,,0,0,0,,{\kf50}Never {\kf30}gonna {\kf40}give {\kf60}you {\kf30}up
```

Colors:
- **Gold** (`#FFD700`) — word being sung right now (fill effect)
- **White** (`#FFFFFF`) — upcoming words
- **Gray** (`#AAAAAA`) — already sung words

### Caching

On re-runs with the same file, SMKaraokeMaker automatically skips completed steps:

```
$ smkaraokemaker run video.mp4 -o karaoke.mp4

 [1/5] Extracting audio (cache)        ██████████ 100%
 [2/5] Separating vocals (cache)       ██████████ 100%
 [3/5] Recognizing text (cache)        ██████████ 100%
 [4/5] Generating subtitles (cache)    ██████████ 100%
 [5/5] Rendering final video           ██████████ 100%  0:01:08
```

Cache is stored in `/tmp/smkaraokemaker_<hash>/` and is tied to the SHA256 hash of the input file. To force a full re-run, delete the temp directory or modify the input file.

---

## Performance Estimates

Approximate processing time for a **4-minute** video:

| Step | Apple Silicon (M2) | CPU (Intel) |
|------|-------------------|-------------|
| Audio extraction | 2 sec | 2 sec |
| Separation (Demucs) | ~3 min | ~8 min |
| Recognition (Whisper large-v3) | ~2 min | ~6 min |
| Subtitle generation (ASS) | <1 sec | <1 sec |
| Video composition | ~1 min | ~2 min |
| **Total** | **~6 min** | **~16 min** |

For quick preview: `--quality draft --model small` reduces processing time by 3-4x.

---

## Project Structure

```
SmKaraokeMaker/
├── init.sh                       # Environment setup script
├── pyproject.toml                 # Dependencies, entry point
├── smkaraokemaker/
│   ├── __init__.py                # Package version
│   ├── __main__.py                # python -m smkaraokemaker
│   ├── cli.py                     # Typer CLI with 14 flags
│   ├── pipeline.py                # Orchestrator: progress, cache, errors
│   ├── config.py                  # KaraokeConfig, PipelineContext
│   ├── models.py                  # Word, Segment, SubtitleStyle
│   ├── modules/
│   │   ├── audio_extractor.py     # FFmpeg → WAV
│   │   ├── vocal_separator.py     # Demucs separation
│   │   ├── speech_recognizer.py   # faster-whisper + grouping
│   │   ├── subtitle_renderer.py   # ASS generator with \kf
│   │   └── video_composer.py      # Final composition
│   ├── utils/
│   │   ├── ffmpeg_utils.py        # FFmpeg/ffprobe wrappers
│   │   ├── temp_manager.py        # Cache, temp files
│   │   ├── validators.py          # Input validation
│   │   └── fonts.py               # Bundled font
│   └── assets/fonts/
│       └── NotoSans-Bold.ttf      # Default font
└── tests/                         # 49 tests
    ├── test_models.py
    ├── test_audio_extractor.py
    ├── test_speech_recognizer.py
    ├── test_subtitle_renderer.py
    ├── test_video_composer.py
    ├── test_temp_manager.py
    └── test_validators.py
```

---

## Development

```bash
# Install dev dependencies
pip install -e ".[dev,ml]"

# Run tests
pytest tests/ -v

# Run without ML (fast tests)
pytest tests/ -v -m "not slow"
```

### Whisper Models

| Model | Size | VRAM | Quality | Speed |
|-------|------|------|---------|-------|
| `tiny` | 39 MB | ~1 GB | Low | Very fast |
| `base` | 74 MB | ~1 GB | Medium | Fast |
| `small` | 244 MB | ~2 GB | Good | Medium |
| `medium` | 769 MB | ~5 GB | Excellent | Slow |
| `large-v3` | 1550 MB | ~10 GB | Best | Very slow |

For testing, `--model small` or `--model base` is recommended.

---

## Supported Formats

**Input video:** `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.m4v`

**Input audio:** `.mp3`, `.wav`, `.flac`, `.ogg`, `.m4a`, `.aac`, `.wma`, `.opus`, `.aiff`

**Output:** `.mp4` (H.264 + AAC)

---

## Error Handling

| Situation | Behavior |
|-----------|----------|
| File not found | Error message + exit code 1 |
| Unsupported format | List of supported formats + exit code 1 |
| FFmpeg not installed | Installation instructions + exit code 1 |
| No audio in video | Error message + exit code 1 |
| Low disk space (<2 GB) | Warning + exit code 1 |
| Ctrl+C | Progress saved, hint to resume |
| ML model not installed | Instructions `pip install smkaraokemaker[ml]` |

---

## License

MIT
