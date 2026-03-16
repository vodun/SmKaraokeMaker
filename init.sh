#!/usr/bin/env bash
set -euo pipefail

echo "=== SMKaraokeMaker — инициализация окружения ==="
echo ""

# Функция для запроса подтверждения
confirm() {
    local prompt="$1"
    read -r -p "$prompt [y/n]: " answer
    [[ "$answer" =~ ^[Yy]$ ]]
}

# ---------- Проверка macOS ----------
if [[ "$(uname)" != "Darwin" ]]; then
    echo "⚠  Скрипт предназначен для macOS. На других ОС установка может отличаться."
fi

# ---------- Homebrew ----------
if ! command -v brew &>/dev/null; then
    echo "✗ Homebrew не найден."
    if confirm "  Установить Homebrew?"; then
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        # Добавить brew в PATH для текущей сессии (Apple Silicon)
        if [[ -f /opt/homebrew/bin/brew ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    else
        echo "  Без Homebrew невозможно продолжить. Выход."
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
    echo "✗ Python 3.11+ не найден (текущий: $(python3 --version 2>/dev/null || echo 'отсутствует'))."
    if confirm "  Установить Python 3.12 через Homebrew?"; then
        brew install python@3.12
        # Обновить PATH
        export PATH="$(brew --prefix python@3.12)/libexec/bin:$PATH"
        if PYTHON=$(find_python); then
            echo "✓ Python установлен: $($PYTHON --version)"
        else
            echo "✗ Не удалось найти Python 3.11+ после установки. Попробуйте перезапустить терминал."
            exit 1
        fi
    else
        echo "  Без Python 3.11+ невозможно продолжить. Выход."
        exit 1
    fi
fi

# ---------- FFmpeg с libass ----------
install_ffmpeg=false

if ! command -v ffmpeg &>/dev/null; then
    echo "✗ FFmpeg не найден."
    if confirm "  Установить FFmpeg с libass?"; then
        install_ffmpeg=true
    else
        echo "  ⚠  Без FFmpeg приложение не сможет работать."
    fi
else
    if ffmpeg -filters 2>/dev/null | grep -q "ass"; then
        echo "✓ FFmpeg: $(ffmpeg -version 2>/dev/null | head -1 | awk '{print $3}') (libass есть)"
    else
        echo "⚠  FFmpeg установлен, но без поддержки libass (нужна для субтитров)."
        if confirm "  Переустановить FFmpeg с libass?"; then
            brew uninstall ffmpeg 2>/dev/null || true
            install_ffmpeg=true
        else
            echo "  ⚠  Без libass караоке-субтитры не будут работать."
        fi
    fi
fi

if $install_ffmpeg; then
    echo "  Подключаю tap homebrew-ffmpeg/ffmpeg..."
    brew tap homebrew-ffmpeg/ffmpeg 2>/dev/null || true
    echo "  Устанавливаю FFmpeg с libass (это может занять несколько минут)..."
    brew install homebrew-ffmpeg/ffmpeg/ffmpeg
    echo "✓ FFmpeg установлен"
fi

# ---------- Виртуальное окружение ----------
VENV_DIR=".venv"
echo ""

if [[ ! -d "$VENV_DIR" ]]; then
    echo "Создаю виртуальное окружение ($VENV_DIR)..."
    $PYTHON -m venv "$VENV_DIR"
    echo "✓ Виртуальное окружение создано"
else
    echo "✓ Виртуальное окружение уже существует ($VENV_DIR)"
fi

# Активация
source "$VENV_DIR/bin/activate"
echo "✓ Окружение активировано: $(python --version)"

# ---------- Обновление pip ----------
echo ""
echo "Обновляю pip..."
pip install --upgrade pip --quiet

# ---------- Установка проекта ----------
echo "Устанавливаю SMKaraokeMaker со всеми зависимостями..."
echo "  (core + ml + dev — это может занять несколько минут)"
pip install -e ".[ml,dev]" --quiet

echo ""
echo "✓ Установлено:"
pip list 2>/dev/null | grep -iE "torch|demucs|faster-whisper|typer|rich|pytest" | sed 's/^/  /'

# ---------- Проверка ----------
echo ""
echo "=== Проверка зависимостей ==="
smkaraokemaker check

echo ""
echo "=== Готово! ==="
echo ""
echo "Для активации окружения в новом терминале:"
echo "  source .venv/bin/activate"
echo ""
echo "Запуск:"
echo "  smkaraokemaker run video.mp4"
echo ""
echo "Тесты:"
echo "  pytest"
