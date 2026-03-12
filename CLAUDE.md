# Voice Assistant Bot (HelpWriter) — Контекст для Claude

**Версия:** 2.5
**Обновлено:** 12 марта 2026

---

## Что это за проект

Telegram-бот для обработки надиктованного текста + веб-редактор для работы с результатами.
Пользователь надиктовывает → бот обрабатывает → текст автоматически появляется в веб-редакторе.

Название репозитория на GitHub: `yuriysklv-hue/helpwriter`

---

## Архитектура

```
Telegram (голос/текст)
    → bot_v2.py (основная логика)
    → AssemblyAI (транскрибация .ogg → текст)
    → DeepSeek (обработка текста по промпту)
    → database.py (сохранение документа)
    → Пользователь получает результат + кнопку "Открыть в редакторе"

Веб-редактор (браузер)
    → api/main.py (FastAPI, порт 8000)
    → database.py (тот же SQLite файл, WAL mode)
    → web/ (React + TipTap, статика через Nginx)
```

---

## Режимы обработки (3 штуки)

| Ключ | Название | Описание |
|---|---|---|
| `transcription` | ✏️ Аккуратная транскрибация | Минимальные правки, сохраняет авторский стиль |
| `structure` | 📋 Структура и план | Извлекает структуру и план из сырых мыслей |
| `ideas` | 💡 Идеи | Развивает сырую идею в 4-6 углов для материала |

Промпты хранятся в `style_prompts.py`.

---

## Структура файлов

```
helpwriter/
├── bot_v2.py              # Основной код бота
├── database.py            # Работа с БД (SQLite)
├── style_prompts.py       # Промпты для режимов обработки
├── manage_codes.py        # CLI для управления кодами доступа
├── bot_database.db        # База данных (WAL mode)
├── requirements.txt       # Зависимости
├── .env                   # Переменные окружения (не коммитить!)
├── api/                   # FastAPI бэкенд
│   ├── main.py            # FastAPI app, CORS, роуты
│   ├── models.py          # Pydantic модели
│   ├── deps.py            # JWT middleware
│   └── routes/
│       ├── auth.py        # POST /api/auth/telegram, GET /verify, POST /logout
│       ├── documents.py   # GET/PUT/DELETE /api/documents
│       ├── users.py       # GET /api/users/me, /me/stats
│       └── internal.py    # POST /internal/bot/save
├── migrations/
│   └── 001_add_users_documents.sql
└── web/                   # React + TipTap фронтенд (Этап 4, TODO)
```

---

## База данных (SQLite, WAL mode)

| Таблица | Описание |
|---|---|
| `users` | Пользователи веб-редактора (telegram_id, имя, username) |
| `documents` | Документы (user_id FK, content, mode, source, soft-delete) |
| `subscriptions` | Платные подписки через Telegram Stars |
| `access_codes` | Legacy коды доступа |
| `usage_logs` | Логи использования для аналитики |

---

## Переменные окружения (.env)

```bash
TELEGRAM_BOT_TOKEN="..."
DEEPSEEK_API_KEY="..."
ASSEMBLYAI_API_KEY="..."
ADMIN_ID="..."            # Telegram user ID администратора
WEB_URL="https://your-domain.com"  # URL веб-редактора (опционально)
JWT_SECRET_KEY="..."      # Секрет для подписи JWT (сгенерировать случайный)
INTERNAL_API_TOKEN="..."  # Токен для /internal/bot/save (опционально)
```

---

## API

### Запуск API локально
```bash
cd ~/voice_bot/voice_assistant_bot
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Эндпоинты

| Метод | Путь | Описание |
|---|---|---|
| POST | `/api/auth/telegram` | Авторизация через Telegram Login Widget |
| GET | `/api/auth/verify` | Проверка токена |
| POST | `/api/auth/logout` | Выход |
| GET | `/api/documents` | Список документов (пагинация, фильтр по mode) |
| GET | `/api/documents/{id}` | Получить документ |
| PUT | `/api/documents/{id}` | Обновить документ |
| DELETE | `/api/documents/{id}` | Удалить документ (soft delete) |
| GET | `/api/users/me` | Профиль текущего пользователя |
| GET | `/api/users/me/stats` | Статистика по документам |
| POST | `/internal/bot/save` | Сохранить документ из бота (X-Internal-Token) |
| GET | `/api/health` | Health check |

Документация API: `/api/docs` (Swagger UI)

---

## Команды бота

| Команда | Описание |
|---|---|
| `/start` | Меню режимов |
| `/subscription` | Статус подписки, продление |
| `/web` | Ссылка на веб-редактор |
| `/admin_stats` | Статистика (только для ADMIN_ID) |

---

## Сервер

| Параметр | Значение |
|---|---|
| IP | `80.249.148.167` |
| User | `root` |
| Путь к боту | `~/voice_bot/voice_assistant_bot` |
| Tmux сессия бота | `bot` |
| API порт | `8000` |

```bash
# Подключение
ssh root@80.249.148.167

# Войти в сессию бота
tmux attach -t bot

# Перезапустить бота
tmux send-keys -t bot C-c Enter
sleep 2
tmux send-keys -t bot 'source venv/bin/activate && python bot_v2.py' Enter

# Запустить API (в отдельной tmux-сессии или systemd)
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## ⚠️ Правило деплоя

**Каждый коммит и пуш в GitHub = обязательный деплой на сервер.**

```bash
ssh root@80.249.148.167
cd ~/voice_bot/voice_assistant_bot
git fetch origin
git show origin/claude/review-documentation-gIM7w:bot_v2.py > bot_v2.py
git show origin/claude/review-documentation-gIM7w:database.py > database.py
git show origin/claude/review-documentation-gIM7w:style_prompts.py > style_prompts.py
# Для api/ — скопировать папку целиком
tmux send-keys -t bot C-c Enter
sleep 2
tmux send-keys -t bot 'source venv/bin/activate && python bot_v2.py' Enter
```

---

## Troubleshooting

**Бот не отвечает:**
```bash
ssh root@80.249.148.167 "ps aux | grep bot"
tmux attach -t bot
```

**Ошибка 409 Conflict** (несколько инстансов):
```bash
pkill -f bot_v2.py
tmux send-keys -t bot 'python bot_v2.py' Enter
```

**API не запускается:**
```bash
pip install fastapi uvicorn python-jose[cryptography]
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Следующие этапы (TODO)

- **Этап 4:** Frontend (React + Vite + TipTap) в папке `web/`
- **Этап 5:** Деплой — Nginx, SSL (Let's Encrypt), systemd для API
- **Этап 6:** Тестирование end-to-end, полировка

---

## Латентность и стоимость

| Этап | Время |
|---|---|
| Транскрибация (AssemblyAI) | 1–5 сек |
| Обработка (DeepSeek) | 1–3 сек |
| Итого | 4–12 сек |

Стоимость за одно голосовое: ~$0.0001–0.0005
