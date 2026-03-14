# Voice Assistant Bot (HelpWriter) — Контекст для Claude

**Версия:** 3.0
**Обновлено:** 14 марта 2026

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
├── bot_database.db        # База данных (WAL mode)
├── requirements.txt       # Зависимости
├── nginx.conf             # Конфиг Nginx (статика + proxy к API)
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
└── web/                   # React + TipTap фронтенд
    ├── index.html
    ├── vite.config.js
    ├── package.json
    ├── .env.example
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── index.css
        ├── api/
        │   └── client.js          # axios + JWT interceptors
        ├── components/
        │   ├── Editor.jsx         # TipTap редактор + тулбар
        │   ├── Editor.css
        │   ├── Sidebar.jsx        # Список документов
        │   └── Sidebar.css
        └── pages/
            ├── Login.jsx          # Telegram Login Widget
            ├── Login.css
            ├── EditorPage.jsx     # Основная страница редактора
            └── EditorPage.css
```

---

## База данных (SQLite, WAL mode)

| Таблица | Описание |
|---|---|
| `users` | Пользователи веб-редактора (telegram_id, имя, username) |
| `documents` | Документы (user_id FK, content, mode, source, soft-delete) |
| `subscriptions` | Платные подписки через Telegram Stars |
| `usage_logs` | Логи использования для аналитики |

---

## Переменные окружения (.env)

```bash
TELEGRAM_BOT_TOKEN="..."
DEEPSEEK_API_KEY="..."
ASSEMBLYAI_API_KEY="..."
ADMIN_ID="..."                     # Telegram user ID администратора
WEB_URL="https://your-domain.com"  # URL веб-редактора
JWT_SECRET_KEY="..."               # Секрет для подписи JWT (сгенерировать случайный)
INTERNAL_API_TOKEN="..."           # Токен для /internal/bot/save
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

## Веб-редактор

### TipTap расширения
Установлены в `web/package.json` (TipTap v3):
- `@tiptap/starter-kit` — базовый набор (bold, italic, strike, code, headings, lists, blockquote, hr)
- `@tiptap/extension-underline` — подчёркивание
- `@tiptap/extension-text-align` — выравнивание (left / center / right / justify)
- `@tiptap/extension-highlight` — выделение цветом (жёлтый маркер)
- `@tiptap/extension-link` — ссылки (prompt для URL)
- `@tiptap/extension-superscript` — верхний индекс
- `@tiptap/extension-subscript` — нижний индекс

### Тулбар (слева направо)
Undo · Redo | Heading▾ (P/H1/H2/H3) · List▾ (bullet/numbered) · Outdent · Indent | **B** · *I* · ~~S~~ · `</>` · U̲ · Highlight · Link | x² · x₂ | Align L/C/R/J | Blockquote

### Типографика (Notion-style)
- `font-size: 16px`, `line-height: 1.6`
- Абзацы: `margin: 0 0 0.3em` (без лишнего воздуха)
- H1: 1.875rem / 700, H2: 1.375rem / 600, H3: 1.125rem / 600
- Списки: `li { margin: 0.1em 0 }`, вложенные плотные
- Inline code: моноширинный шрифт, красный цвет, серый фон
- Highlight: жёлтый фон `#fff3a3`
- Сохранение: Ctrl+S или кнопка

### Сборка фронтенда
```bash
cd web
npm install
npm run build   # → dist/ (статика для Nginx)
```

---

## Команды бота

| Команда | Описание |
|---|---|
| `/start` | Меню режимов |
| `/subscription` | Статус подписки, продление |
| `/web` | Ссылка на веб-редактор |
| `/admin_stats` | Статистика (только для ADMIN_ID) |

---

## Подписка (Telegram Stars)

Платёж через встроенный механизм Telegram Stars (invoice). Логика в `bot_v2.py`:
- `/subscription` — показывает статус и кнопку оплаты
- `pre_checkout_query` — подтверждение платежа
- `successful_payment` — активация подписки в БД (таблица `subscriptions`)
- Проверка активной подписки при каждой обработке голосового/текста

---

## Сервер

| Параметр | Значение |
|---|---|
| IP | `80.249.148.167` |
| User | `root` |
| Путь к боту | `~/voice_bot/voice_assistant_bot` |
| Tmux сессия бота | `bot` |
| API порт | `8000` |
| Фронтенд | `web/dist/` → Nginx |

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
git fetch origin main
git show origin/main:bot_v2.py > bot_v2.py
git show origin/main:database.py > database.py
git show origin/main:style_prompts.py > style_prompts.py
# api/ — скопировать папку целиком
# web/ — пересобрать
git show origin/main:web/src/components/Editor.jsx > web/src/components/Editor.jsx
git show origin/main:web/src/components/Editor.css > web/src/components/Editor.css
cd web && npm install && npm run build
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

**Фронтенд не собирается (конфликт версий TipTap):**
```bash
cd web && npm install --legacy-peer-deps
```

---

## Что реализовано (история этапов)

| Этап | Статус | Описание |
|---|---|---|
| 1 | ✅ | БД: таблицы users, documents, subscriptions, usage_logs |
| 2 | ✅ | FastAPI бэкенд: auth (JWT), documents CRUD, internal endpoint |
| 3 | ✅ | Интеграция бота с API (`/internal/bot/save`) |
| 4 | ✅ | React фронтенд: Telegram Login, Sidebar, TipTap редактор с тулбаром |
| 5 | 🔲 | Деплой: Nginx (SSL Let's Encrypt), systemd для API |
| 6 | 🔲 | Тестирование end-to-end, полировка |

---

## Латентность и стоимость

| Этап | Время |
|---|---|
| Транскрибация (AssemblyAI) | 1–5 сек |
| Обработка (DeepSeek) | 1–3 сек |
| Итого | 4–12 сек |

Стоимость за одно голосовое: ~$0.0001–0.0005
