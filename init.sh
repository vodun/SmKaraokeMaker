#!/usr/bin/env bash
set -euo pipefail

echo "=== SMKaraokeMaker — environment setup ==="
echo ""

# Confirmation prompt function
confirm() {
    local prompt="$1"
    read -r -p "$prompt [y/n]: " answer
    [[ "$answer" =~ ^[Yy]$ ]]
}

# ---------- macOS check ----------
if [[ "$(uname)" != "Darwin" ]]; then
    echo "⚠  This script is intended for macOS. Installation may differ on other OSes."
fi

# ---------- Homebrew ----------
if ! command -v brew &>/dev/null; then
    echo "✗ Homebrew not found."
    if confirm "  Install Homebrew?"; then
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        # Add brew to PATH for current session (Apple Silicon)
        if [[ -f /opt/homebrew/bin/brew ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    else
        echo "  Cannot continue without Homebrew. Exiting."
        exit 1
    fi
fi
echo "✓ Homebrew: $(brew --version | head -1)"

# ---------- Python 3.11+ ----------
find_python() {
    for cmd in python3.13 python3.12 python3.11 python3; do
        if command -v "$cmd" &>/dev/null; then
            local ver
            ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
            local minor
            minor=$(echo "$ver" | cut -d. -f2)
            if [[ "$minor" -ge 11 ]]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON=""
if PYTHON=$(find_python); then
    echo "✓ Python: $($PYTHON --version)"
else
    echo "✗ Python 3.11+ not found (current: $(python3 --version 2>/dev/null || echo 'not installed'))."
    if confirm "  Install Python 3.12 via Homebrew?"; then
        brew install python@3.12
        # Update PATH
        export PATH="$(brew --prefix python@3.12)/libexec/bin:$PATH"
        if PYTHON=$(find_python); then
            echo "✓ Python installed: $($PYTHON --version)"
        else
            echo "✗ Could not find Python 3.11+ after installation. Try restarting the terminal."
            exit 1
        fi
    else
        echo "  Cannot continue without Python 3.11+. Exiting."
        exit 1
    fi
fi

# ---------- FFmpeg with libass ----------
install_ffmpeg=false

if ! command -v ffmpeg &>/dev/null; then
    echo "✗ FFmpeg not found."
    if confirm "  Install FFmpeg with libass?"; then
        install_ffmpeg=true
    else
        echo "  ⚠  The application cannot work without FFmpeg."
    fi
else
    if ffmpeg -filters 2>/dev/null | grep -q "ass"; then
        echo "✓ FFmpeg: $(ffmpeg -version 2>/dev/null | head -1 | awk '{print $3}') (libass available)"
    else
        echo "⚠  FFmpeg is installed but without libass support (required for subtitles)."
        if confirm "  Reinstall FFmpeg with libass?"; then
            brew uninstall ffmpeg 2>/dev/null || true
            install_ffmpeg=true
        else
            echo "  ⚠  Karaoke subtitles will not work without libass."
        fi
    fi
fi

if $install_ffmpeg; then
    echo "  Adding tap homebrew-ffmpeg/ffmpeg..."
    brew tap homebrew-ffmpeg/ffmpeg 2>/dev/null || true
    echo "  Installing FFmpeg with libass (this may take a few minutes)..."
    brew install homebrew-ffmpeg/ffmpeg/ffmpeg
    echo "✓ FFmpeg installed"
fi

# ---------- Virtual environment ----------
VENV_DIR=".venv"
echo ""

if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment ($VENV_DIR)..."
    $PYTHON -m venv "$VENV_DIR"
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists ($VENV_DIR)"
fi

# Activation
source "$VENV_DIR/bin/activate"
echo "✓ Environment activated: $(python --version)"

# ---------- Upgrade pip ----------
echo ""
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# ---------- Install project ----------
echo "Installing SMKaraokeMaker with all dependencies..."
echo "  (core + ml + dev — this may take a few minutes)"
pip install -e ".[ml,dev]" --quiet

echo ""
echo "✓ Installed:"
pip list 2>/dev/null | grep -iE "torch|demucs|faster-whisper|typer|rich|pytest" | sed 's/^/  /'

# ---------- Verification ----------
echo ""
echo "=== Dependency check ==="
smkaraokemaker check

echo ""
echo "=== Done! ==="
echo ""
echo "To activate the environment in a new terminal:"
echo "  source .venv/bin/activate"
echo ""
echo "Run:"
echo "  smkaraokemaker run video.mp4"
echo ""
echo "Tests:"
echo "  pytest"
