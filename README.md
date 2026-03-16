# SMKaraokeMaker

**Генератор караоке-видео из музыкальных клипов**

CLI-приложение для macOS, которое принимает на вход музыкальное видео и автоматически превращает его в караоке: отделяет вокал от инструментала, распознаёт текст песни с точными таймингами по словам, накладывает синхронизированные субтитры с подсветкой текущего слова и выдаёт готовый MP4-файл.

```
$ smkaraokemaker input.mp4 -o karaoke_output.mp4

Входной файл: input.mp4 (1920x1080, 222 сек, 30 fps)

 [1/5] Извлечение аудио              ██████████ 100%  0:00:02
 [2/5] Разделение вокала и музыки     ██████████ 100%  0:03:12
 [3/5] Распознавание текста и таймингов██████████ 100%  0:01:45
 [4/5] Генерация караоке-субтитров    ██████████ 100%  0:00:01
 [5/5] Рендер финального видео        ██████████ 100%  0:01:08

✓ Готово: karaoke_output.mp4 (134 МБ, 3:42)
```

---

## Возможности

- **Автоматическая сепарация вокала** — Demucs (htdemucs_ft) от Meta, лучшее качество разделения на рынке
- **Распознавание текста с пословными таймингами** — faster-whisper (large-v3), поддержка 90+ языков
- **Караоке-субтитры** — ASS-формат с тегами `\kf` для плавной заливки слов слева направо
- **Кэширование** — при повторном запуске с тем же файлом выполненные шаги пропускаются
- **Apple Silicon** — нативная поддержка MPS-ускорения (PyTorch) на M1/M2/M3/M4
- **Гибкая настройка** — цвета, шрифт, позиция субтитров, профили качества
- **Автоопределение языка** — или явное указание через `--lang`

---

## Требования

| Компонент | Версия | Назначение |
|-----------|--------|------------|
| macOS | 12+ | Apple Silicon рекомендуется |
| Python | 3.11+ | Среда выполнения |
| FFmpeg | 6.0+ | Работа с аудио/видео, **с поддержкой libass** |

### Установка FFmpeg с libass

Стандартный `brew install ffmpeg` **не включает** поддержку ASS-субтитров. Нужна версия из tap:

```bash
brew tap homebrew-ffmpeg/ffmpeg
brew install homebrew-ffmpeg/ffmpeg/ffmpeg
```

Проверить поддержку:

```bash
ffmpeg -filters 2>/dev/null | grep ass
# Должно показать: .. ass  V->V  Render ASS subtitles...
```

---

## Установка

### Из исходников

```bash
git clone https://github.com/user/smkaraokemaker.git
cd smkaraokemaker

# Создать виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# Установить с ML-зависимостями
pip install -e ".[ml]"

# Или минимальная установка (без ML — для разработки/тестов)
pip install -e ".[dev]"
```

### Зависимости

**Основные** (устанавливаются автоматически):
- `typer` — CLI-интерфейс
- `rich` — прогресс-бары и форматированный вывод
- `pydantic` — валидация данных
- `ffmpeg-python` — обёртка FFmpeg
- `Pillow` — работа с изображениями
- `numpy` — массивы данных

**ML** (группа `[ml]`):
- `torch` — ML-бэкенд (MPS на Apple Silicon)
- `demucs` — сепарация вокала (Meta)
- `faster-whisper` — распознавание речи (CTranslate2)

---

## Использование

### Базовый вызов

```bash
smkaraokemaker video.mp4
# Результат: video_karaoke.mp4
```

### С указанием выхода и языка

```bash
smkaraokemaker video.mp4 -o karaoke.mp4 --lang ru
```

### Быстрый черновик (для превью)

```bash
smkaraokemaker video.mp4 --quality draft
```

### Кастомные цвета

```bash
smkaraokemaker video.mp4 \
  --color-active "#FF4444" \
  --color-inactive "#CCCCCC" \
  --color-done "#666666"
```

### Свой шрифт и размер

```bash
smkaraokemaker video.mp4 --font /path/to/MyFont.ttf --font-size 64
```

### Подробный вывод (отладка)

```bash
smkaraokemaker video.mp4 -v --keep-temp
```

---

## Флаги и опции

| Флаг | Тип | По умолчанию | Описание |
|------|-----|-------------|----------|
| `INPUT_VIDEO` | path | — | Путь к исходному видеофайлу (обязательный) |
| `-o, --output` | path | `<input>_karaoke.mp4` | Путь к выходному файлу |
| `--lang` | str | `auto` | Язык распознавания ([ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)) |
| `--model` | str | `large-v3` | Модель Whisper: `tiny`, `base`, `small`, `medium`, `large-v3` |
| `--font` | path | NotoSans-Bold | Путь к .ttf-шрифту |
| `--font-size` | int | `48` | Размер шрифта (px) |
| `--color-active` | str | `#FFD700` | Цвет текущего слова (золотой) |
| `--color-inactive` | str | `#FFFFFF` | Цвет ещё не спетых слов (белый) |
| `--color-done` | str | `#AAAAAA` | Цвет уже спетых слов (серый) |
| `--position` | str | `bottom` | Позиция: `top`, `center`, `bottom` |
| `--separator` | str | `demucs` | Движок сепарации: `demucs` |
| `--lyrics` | path | — | Готовый текст песни (.txt / .lrc) для forced alignment |
| `--keep-temp` | flag | `false` | Сохранить промежуточные файлы |
| `--quality` | str | `high` | Профиль: `draft`, `high`, `ultra` |
| `-v, --verbose` | flag | `false` | Подробный лог |
| `--version` | flag | — | Показать версию |

---

## Профили качества

| Профиль | Пресет FFmpeg | CRF | Аудио | Скорость | Применение |
|---------|-------------|-----|-------|----------|------------|
| `draft` | ultrafast | 28 | 128k AAC | Быстро | Превью, проверка таймингов |
| `high` | medium | 18 | 192k AAC | Средне | Основной режим |
| `ultra` | slow | 14 | 320k AAC | Медленно | Максимальное качество |

---

## Как это работает

### Архитектура

Линейный пайплайн из 5 модулей — каждый получает результат предыдущего:

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
[3. Speech Recognizer]   faster-whisper → слова + тайминги (word-level)
    │
    ▼
[4. Subtitle Renderer]   Генерация ASS с тегами \kf (караоке-заливка)
    │
    ▼
[5. Video Composer]      FFmpeg: видео + инструментал + субтитры → MP4
    │
    ▼
karaoke_output.mp4
```

### Караоке-эффект

Субтитры используют формат ASS (Advanced SubStation Alpha) с тегами `\kf` — плавная заливка каждого слова слева направо синхронно с пением:

```ass
Dialogue: 0,0:01:05.00,0:01:10.00,Karaoke,,0,0,0,,{\kf50}Я {\kf30}помню {\kf40}чудное {\kf60}мгновенье
```

Цвета:
- **Золотой** (`#FFD700`) — слово поётся прямо сейчас (заливка)
- **Белый** (`#FFFFFF`) — слова впереди
- **Серый** (`#AAAAAA`) — уже спетые слова

### Кэширование

При повторном запуске с тем же файлом SMKaraokeMaker автоматически пропускает уже выполненные шаги:

```
$ smkaraokemaker video.mp4 -o karaoke.mp4

 [1/5] Извлечение аудио (кэш)         ██████████ 100%
 [2/5] Разделение вокала и музыки (кэш)██████████ 100%
 [3/5] Распознавание текста (кэш)      ██████████ 100%
 [4/5] Генерация субтитров (кэш)       ██████████ 100%
 [5/5] Рендер финального видео         ██████████ 100%  0:01:08
```

Кэш хранится в `/tmp/smkaraokemaker_<hash>/` и привязан к SHA256-хэшу входного файла. Для принудительного перезапуска удалите temp-директорию или измените входной файл.

---

## Оценка производительности

Ориентировочное время обработки для видео **4 минуты**:

| Этап | Apple Silicon (M2) | CPU (Intel) |
|------|-------------------|-------------|
| Извлечение аудио | 2 сек | 2 сек |
| Сепарация (Demucs) | ~3 мин | ~8 мин |
| Распознавание (Whisper large-v3) | ~2 мин | ~6 мин |
| Генерация субтитров (ASS) | <1 сек | <1 сек |
| Сборка видео | ~1 мин | ~2 мин |
| **Итого** | **~6 мин** | **~16 мин** |

Для быстрого превью: `--quality draft --model small` сократит время в 3-4 раза.

---

## Структура проекта

```
smkaraokemaker/
├── pyproject.toml                 # Зависимости, entry point
├── smkaraokemaker/
│   ├── __init__.py                # Версия пакета
│   ├── __main__.py                # python -m smkaraokemaker
│   ├── cli.py                     # Typer CLI с 14 флагами
│   ├── pipeline.py                # Оркестратор: прогресс, кэш, ошибки
│   ├── config.py                  # KaraokeConfig, PipelineContext
│   ├── models.py                  # Word, Segment, SubtitleStyle
│   ├── modules/
│   │   ├── audio_extractor.py     # FFmpeg → WAV
│   │   ├── vocal_separator.py     # Demucs сепарация
│   │   ├── speech_recognizer.py   # faster-whisper + группировка
│   │   ├── subtitle_renderer.py   # ASS-генератор с \kf
│   │   └── video_composer.py      # Финальная сборка
│   ├── utils/
│   │   ├── ffmpeg_utils.py        # Обёртки FFmpeg/ffprobe
│   │   ├── temp_manager.py        # Кэш, temp-файлы
│   │   ├── validators.py          # Валидация входных данных
│   │   └── fonts.py               # Встроенный шрифт
│   └── assets/fonts/
│       └── NotoSans-Bold.ttf      # Шрифт по умолчанию
└── tests/                         # 41 тест
    ├── test_models.py
    ├── test_audio_extractor.py
    ├── test_speech_recognizer.py
    ├── test_subtitle_renderer.py
    ├── test_video_composer.py
    ├── test_temp_manager.py
    └── test_validators.py
```

---

## Разработка

```bash
# Установка dev-зависимостей
pip install -e ".[dev,ml]"

# Запуск тестов
pytest tests/ -v

# Запуск без ML (быстрые тесты)
pytest tests/ -v -m "not slow"
```

### Модели Whisper

| Модель | Размер | VRAM | Качество | Скорость |
|--------|--------|------|----------|----------|
| `tiny` | 39 МБ | ~1 ГБ | Низкое | Очень быстро |
| `base` | 74 МБ | ~1 ГБ | Среднее | Быстро |
| `small` | 244 МБ | ~2 ГБ | Хорошее | Средне |
| `medium` | 769 МБ | ~5 ГБ | Отличное | Медленно |
| `large-v3` | 1550 МБ | ~10 ГБ | Лучшее | Очень медленно |

Для тестирования рекомендуется `--model small` или `--model base`.

---

## Поддерживаемые форматы

**Входные видео:** `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.m4v`

**Выход:** `.mp4` (H.264 + AAC)

---

## Обработка ошибок

| Ситуация | Поведение |
|----------|----------|
| Файл не найден | Сообщение + код выхода 1 |
| Неподдерживаемый формат | Список поддерживаемых + код 1 |
| FFmpeg не установлен | Инструкция `brew install` + код 1 |
| Нет аудио в видео | Сообщение + код 1 |
| Мало места на диске (<2 ГБ) | Предупреждение + код 1 |
| Ctrl+C | Сохранение прогресса, подсказка для продолжения |
| ML-модель не установлена | Инструкция `pip install smkaraokemaker[ml]` |

---

## Лицензия

MIT
