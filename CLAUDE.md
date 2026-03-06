# Voice Assistant Bot (HelpWriter) — Контекст для Claude

**Версия:** 2.3
**Обновлено:** 6 марта 2026

---

## Что это за проект

Telegram-бот для обработки надиктованного текста. Пользователь отправляет голосовое сообщение или текст, бот обрабатывает его в одном из трёх режимов через DeepSeek.

Название репозитория на GitHub: `yuriysklv-hue/helpwriter`

---

## Архитектура

```
Telegram (голос/текст)
    → bot_v2.py (основная логика)
    → AssemblyAI (транскрибация .ogg → текст)
    → DeepSeek (обработка текста по промпту)
    → Пользователь получает результат
```

**Конвертация аудио:** .ogg → .wav через pydub/ffmpeg перед отправкой в AssemblyAI.

---

## Режимы обработки (3 штуки)

До марта 2026 было 5 стилей (email, чат, документация, официальное письмо, базовое). Затем сократили до 2, потом добавили третий:

| Ключ | Название | Описание |
|---|---|---|
| `transcription` | ✏️ Аккуратная транскрибация | Минимальные правки, сохраняет авторский стиль, убирает слова-паразиты |
| `structure` | 📋 Структура и план | Извлекает структуру и план из сырых надиктованных мыслей |
| `ideas` | 💡 Идеи | Развивает сырую идею в 4-6 конкретных углов для будущего материала |

Промпты хранятся в `style_prompts.py` в словаре `STYLE_PROMPTS`.

---

## Структура файлов

```
voice_assistant_bot/
├── bot_v2.py          # Основной код бота
├── database.py        # Работа с БД (SQLite)
├── style_prompts.py   # Промпты для режимов обработки
├── manage_codes.py    # CLI для управления кодами доступа
├── bot_database.db    # База данных
├── .env               # Переменные окружения (не коммитить!)
├── requirements.txt   # Зависимости
└── venv/              # Виртуальное окружение
```

---

## Сервер

| Параметр | Значение |
|---|---|
| IP | `80.249.148.167` |
| User | `root` |
| Путь к боту | `~/voice_bot/voice_assistant_bot` |
| Tmux сессия | `bot` |

```bash
# Подключение
ssh root@80.249.148.167

# Проверить статус
tmux ls

# Войти в сессию бота
tmux attach -t bot

# Выйти из tmux (бот продолжает работать)
Ctrl+B, затем D

# Перезапустить бота
tmux send-keys -t bot C-c
tmux send-keys -t bot 'python bot_v2.py' Enter
```

---

## Переменные окружения (.env)

```bash
TELEGRAM_BOT_TOKEN="..."
DEEPSEEK_API_KEY="..."
ASSEMBLYAI_API_KEY="..."
ADMIN_ID="..."  # Telegram user ID администратора (опционально)
```

---

## API и зависимости

| API | Назначение |
|---|---|
| Telegram Bot API | Long Polling, взаимодействие с пользователем |
| AssemblyAI | Транскрибация голоса, `language_code="ru"` |
| DeepSeek | Обработка текста, модель `deepseek-chat`, `temperature=0.7` |

```bash
python-telegram-bot>=20.0
openai>=1.0.0        # DeepSeek совместим с OpenAI SDK
assemblyai
pydub
python-dotenv
# системная зависимость: ffmpeg
```

---

## База данных (SQLite)

**Таблица `access_codes`:** code, telegram_user_id, assigned_at, is_active, preferred_style

**Таблица `usage_logs`:** access_code_id, telegram_user_id, message_type, audio_duration, text_characters, processing_time

Новые пользователи получают автокод `auto_{user_id}_{timestamp}` при первом использовании (open access режим).

---

## Команды бота

| Команда | Описание |
|---|---|
| `/start` | Показать меню выбора режима |
| `/enter_code <код>` | Активировать код доступа |
| `/admin_stats` | Статистика (только для ADMIN_ID) |
| `/seed_codes код1 код2` | Добавить коды доступа |

---

## Деплой обновлений на сервер

Деплой через GitHub (ветка `claude/bot-monetization-features-SPLUX`):

```bash
# Подключиться к серверу
ssh root@80.249.148.167

# Перейти в папку бота и обновить файлы
cd ~/voice_bot/voice_assistant_bot
git fetch origin
git show origin/claude/bot-monetization-features-SPLUX:bot_v2.py > bot_v2.py
git show origin/claude/bot-monetization-features-SPLUX:style_prompts.py > style_prompts.py
git show origin/claude/bot-monetization-features-SPLUX:CLAUDE.md > CLAUDE.md

# Перезапустить бота
tmux send-keys -t bot C-c Enter
sleep 2
tmux send-keys -t bot 'source venv/bin/activate && python bot_v2.py' Enter
```

Если `origin` ещё не указывает на GitHub (один раз):
```bash
git remote set-url origin https://github.com/yuriysklv-hue/helpwriter.git
```

---

## Troubleshooting

**Бот не отвечает:**
```bash
ssh root@80.249.148.167 "ps aux | grep bot"
tmux attach -t bot  # посмотреть логи
```

**Ошибка 409 Conflict** (несколько инстансов):
```bash
pkill -f bot_v2.py
tmux send-keys -t bot 'python bot_v2.py' Enter
```

---

## Латентность и стоимость

| Этап | Время |
|---|---|
| Транскрибация (AssemblyAI) | 1–5 сек |
| Обработка (DeepSeek) | 1–3 сек |
| Итого | 4–12 сек |

Стоимость за одно голосовое: ~$0.0001–0.0005
