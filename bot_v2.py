"""
Voice Assistant Bot - Version 2.0
With access code authentication and usage analytics

Version: 2.0.0
Author: Created with assistance from Claude
Date: 11 January 2026
"""

from dotenv import load_dotenv
load_dotenv()

import os
import logging
import asyncio
import time
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, PrefixHandler
from openai import OpenAI
import assemblyai as aai
from pydub import AudioSegment
from database import check_user_access, assign_code_to_user, log_usage, get_admin_stats, add_access_code, get_all_access_codes, get_user_style, set_user_style
from style_prompts import get_style_prompt, get_style_name, get_style_description, get_all_styles, STYLE_NAMES, STYLE_DESCRIPTIONS, STYLE_PROMPTS

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =============================================================================
# API CONFIGURATION
# =============================================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # Your Telegram user ID

if DEEPSEEK_API_KEY:
    logger.info(f"✅ DEEPSEEK_API_KEY loaded successfully")
if ASSEMBLYAI_API_KEY:
    logger.info(f"✅ ASSEMBLYAI_API_KEY loaded successfully")
if ADMIN_ID:
    logger.info(f"✅ ADMIN_ID: {ADMIN_ID}")
else:
    logger.warning("⚠️ ADMIN_ID not set!")

# =============================================================================
# CLIENT INITIALIZATION
# =============================================================================

try:
    deepseek_client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )
    logger.info("✅ DeepSeek client initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize DeepSeek client: {e}")

try:
    aai.settings.api_key = ASSEMBLYAI_API_KEY
    logger.info("✅ AssemblyAI client initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize AssemblyAI client: {e}")

# =============================================================================
# SYSTEM PROMPT (deprecated - using style_prompts.py instead)
# =============================================================================

SYSTEM_PROMPT = """You are a professional communication assistant. Your task is to refine voice transcriptions into well-structured, professional messages.

Style guidelines:
- Write in a professional yet casual business style (деловой casual)
- Clear, respectful, and concise
- Proper grammar and punctuation
- Logical structure with paragraphs
- Maintain the original meaning and tone
- Remove filler words (um, uh, like, etc.)
- Fix run-on sentences
- Add appropriate formatting when helpful

The input is a raw voice transcription that may contain:
- Filler words and repetitions
- Run-on sentences
- Informal phrasing
- Lack of punctuation

Transform it into a polished, professional message while keeping the authentic voice of the speaker."""

# =============================================================================
# AUTHENTICATION MIDDLEWARE
# =============================================================================

async def require_auth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if user is authenticated.
    Admin (ADMIN_ID) has automatic access.
    Regular users need an access code.
    Returns True if user has access, False otherwise.
    """
    user_id = update.effective_user.id

    # Admin has automatic access
    if user_id == ADMIN_ID:
        return True

    # Regular users need access code
    access_code = check_user_access(user_id)

    if access_code is None:
        await update.message.reply_text(
            "🔒 Бот требует код доступа.\n\n"
            "Используйте команду:\n"
            "/enter_code <ваш_код>\n\n"
            "Пример: /enter_code ritathebest"
        )
        return False

    return True


# =============================================================================
# TRANSCRIPTION FUNCTION (AssemblyAI)
# =============================================================================

async def transcribe_audio(audio_file_path: str) -> str:
    """Transcribe audio using AssemblyAI with Russian language support."""
    try:
        logger.info(f"Transcribing audio with AssemblyAI...")

        transcriber = aai.Transcriber()
        config = aai.TranscriptionConfig(language_code="ru")

        transcript = transcriber.transcribe(audio_file_path, config=config)

        while transcript.status == aai.TranscriptStatus.queued or \
              transcript.status == aai.TranscriptStatus.processing:
            await asyncio.sleep(1)
            transcript = transcriber.get_transcript(transcript.id)

        if transcript.status == aai.TranscriptStatus.completed:
            logger.info(f"✅ Transcription successful")
            logger.info(f"Text length: {len(transcript.text)}")
            return transcript.text
        elif transcript.status == aai.TranscriptStatus.error:
            raise Exception(f"Transcription failed: {transcript.error}")
        else:
            raise Exception(f"Unknown transcription status: {transcript.status}")

    except Exception as e:
        logger.error(f"❌ Error transcribing audio: {e}")
        raise Exception(f"Ошибка транскрибации: {str(e)}")


# =============================================================================
# TEXT EDITING FUNCTION (DeepSeek)
# =============================================================================

async def refine_text(raw_text: str, style: str = "business_casual") -> str:
    """Refine text using DeepSeek model with specified style."""
    try:
        logger.info(f"Refining text with DeepSeek... Style: {style}")

        # Get style-specific prompt
        style_prompt = get_style_prompt(style)

        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": style_prompt},
                {"role": "user", "content": f"Отредактируй это сообщение:\n\n{raw_text}"}
            ],
            temperature=0.7
        )

        logger.info(f"✅ DeepSeek response received successfully")
        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"❌ Error refining text: {e}")
        raise Exception(f"Ошибка редактирования: {str(e)}")


# =============================================================================
# TELEGRAM HANDLERS
# =============================================================================

def get_main_keyboard(is_admin=False):
    """Get main menu keyboard based on user role."""
    if is_admin:
        keyboard = [
            [KeyboardButton("📊 Статистика"), KeyboardButton("📋 Коды")],
            [KeyboardButton("➕ Добавить коды"), KeyboardButton("🎨 Стиль")],
            [KeyboardButton("❓ Справка")],
        ]
    else:
        keyboard = [
            [KeyboardButton("🎨 Стиль")],
        ]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - show scenario selection keyboard for ALL users."""
    user_id = update.effective_user.id

    # Show scenarios keyboard for EVERYONE (including admin)
    scenario_keyboard = [
        [KeyboardButton("📧 Email коллеге"), KeyboardButton("💬 Сообщение в чат")],
        [KeyboardButton("📝 Документация"), KeyboardButton("✉️ Официальное письмо")],
        [KeyboardButton("✏️ Аккуратно отредактировать")],
    ]

    reply_markup = ReplyKeyboardMarkup(scenario_keyboard, resize_keyboard=True)

    welcome_message = """👋 Привет! Я — HelpWriter.

**Как это работает:**
1. Выберите, что хотите создать
2. Отправьте голосовое или текст
3. Получите готовый результат

🎯 **Что хотите создать?**"""

    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="Markdown")


async def enter_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /enter_code command."""
    user_id = update.effective_user.id

    # Check if already authenticated
    existing_code = check_user_access(user_id)
    if existing_code:
        # Show menu for existing authenticated user
        current_style = get_user_style(user_id)
        reply_markup = get_main_keyboard(is_admin=False)
        await update.message.reply_text(
            f"✅ У вас уже есть доступ!\n\n"
            f"Ваш код: {existing_code}\n\n"
            f"🎨 Текущий стиль: {get_style_name(current_style)}\n\n"
            f"Бот готов к работе.",
            reply_markup=reply_markup
        )
        return

    # Get code from arguments
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ Укажите код доступа.\n\n"
            "Пример: /enter_code ritathebest"
        )
        return

    code = context.args[0].strip()

    # Assign code to user
    success, message = assign_code_to_user(code, user_id)

    # If code was successfully assigned, show menu
    if success:
        current_style = get_user_style(user_id)
        reply_markup = get_main_keyboard(is_admin=False)

        # Add style info to message
        style_info = f"\n\n🎨 Текущий стиль: {get_style_name(current_style)}\n\nИспользуй /style чтобы изменить стиль редактирования."
        full_message = message + style_info

        await update.message.reply_text(full_message, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message)


async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin_stats command - only for admin."""
    user_id = update.effective_user.id

    # Check if admin
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав для этой команды.")
        return

    # Get stats
    stats = get_admin_stats()

    # Format stats message
    message = "📊 **Статистика использования бота**\n\n"

    for stat in stats:
        message += f"🔑 Код: `{stat['code']}`\n"
        message += f"   👤 User ID: {stat['user_id'] if stat['user_id'] else 'Не активирован'}\n"
        message += f"   📨 Всего сообщений: {stat['total_messages']}\n"
        message += f"   🎤 Голосовых: {stat['voice_messages']}\n"
        message += f"   📝 Текстовых: {stat['text_messages']}\n"

        if stat['total_audio_duration']:
            minutes = stat['total_audio_duration'] / 60
            message += f"   ⏱️ Аудио: {minutes:.1f} мин\n"

        if stat['total_text_characters']:
            message += f"   📊 Текст: {stat['total_text_characters']:,} символов\n"

        if stat['first_usage']:
            message += f"   📅 Первое использование: {stat['first_usage']}\n"
        if stat['last_usage']:
            message += f"   📅 Последнее: {stat['last_usage']}\n"

        message += "\n"

    await update.message.reply_text(message, parse_mode="Markdown")


async def seed_codes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Seed initial access codes - only for admin."""
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав для этой команды.")
        return

    # Add codes from arguments
    if not context.args or len(context.args) == 0:
        existing_codes = get_all_access_codes()
        await update.message.reply_text(
            f"📋 Существующие коды:\n\n" + "\n".join(existing_codes) +
            "\n\nИспользование: /seed_codes код1 код2 код3"
        )
        return

    added = []
    already_exists = []

    for code in context.args:
        if add_access_code(code):
            added.append(code)
        else:
            already_exists.append(code)

    message = "📝 Результат:\n\n"
    if added:
        message += f"✅ Добавлены: {', '.join(added)}\n"
    if already_exists:
        message += f"⚠️ Уже существуют: {', '.join(already_exists)}\n"

    await update.message.reply_text(message)


async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin menu button presses."""
    user_id = update.effective_user.id
    text = update.message.text

    # Handle "Back" button - return to main menu
    if text == "◀️ Назад":
        is_admin = (user_id == ADMIN_ID)
        reply_markup = get_main_keyboard(is_admin=is_admin)
        await update.message.reply_text("🔙 Возврат в главное меню", reply_markup=reply_markup)
        return

    # Only admin can use admin menu buttons
    if user_id != ADMIN_ID and text in ["📊 Статистика", "📋 Коды", "➕ Добавить коды", "❓ Справка"]:
        await update.message.reply_text("❌ Это меню только для администратора.")
        return

    # Handle style button (available to all authenticated users)
    if text == "🎨 Стиль":
        await style_command(update, context)
        return

    # Handle admin button clicks
    if text == "📊 Статистика":
        await admin_stats_command(update, context)
    elif text == "📋 Коды":
        await list_codes_command(update, context)
    elif text == "➕ Добавить коды":
        await update.message.reply_text(
            "➕ *Добавление кодов*\n\n"
            "Отправьте коды для добавления в формате:\n"
            "`код1 код2 код3`\n\n"
            "Или используйте команду:\n"
            "`/seed_codes код1 код2 код3`",
            parse_mode="Markdown"
        )
    elif text == "❓ Справка":
        help_text = """❓ *Админ-справка*

*Доступные команды:*

📊 /admin_stats - Полная статистика по всем кодам

📋 /seed_codes - Управление кодами доступа
   • Без аргументов: показать существующие коды
   • С аргументами: `/seed_codes код1 код2 код3`

➕ Кнопка "Добавить коды" - быстрое добавление

*Через CLI на сервере:*
```bash
python manage_codes.py add код1 код2
python manage_codes.py list
python manage_codes.py stats
python manage_codes.py remove код
```"""

        await update.message.reply_text(help_text, parse_mode="Markdown")

    # Handle style selection buttons
    elif text in STYLE_NAMES.values():
        # User clicked a style button
        style_key = None
        for key, name in STYLE_NAMES.items():
            if name == text:
                style_key = key
                break

        if style_key:
            success = set_user_style(user_id, style_key)
            if success:
                # Return to main menu after style selection
                is_admin = (user_id == ADMIN_ID)
                reply_markup = get_main_keyboard(is_admin=is_admin)

                await update.message.reply_text(
                    f"✅ Стиль изменён на {get_style_name(style_key)}!\n\n"
                    f"_{get_style_description(style_key)}_\n\n"
                    f"📤 Теперь отправьте голосовое или текстовое сообщение для обработки.",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("❌ Ошибка при изменении стиля")


async def list_codes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of all access codes."""
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав для этой команды.")
        return

    codes = get_all_access_codes()
    from database import init_database
    import sqlite3
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT code, telegram_user_id, assigned_at, is_active, preferred_style
        FROM access_codes
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    message = "📋 *Список кодов доступа*\n\n"

    for row in rows:
        code, user_id_code, assigned_at, is_active, preferred_style = row
        status = "✅ Активен" if is_active else "❌ Неактивен"
        user_info = f"User ID: `{user_id_code}`" if user_id_code else "🔓 Не назначен"

        message += f"🔑 *{code}*\n"
        message += f"   {status}\n"
        message += f"   {user_info}\n"
        message += f"   🎨 Стиль: {get_style_name(preferred_style)}\n"
        if assigned_at:
            message += f"   📅 {assigned_at}\n"
        message += "\n"

    await update.message.reply_text(message, parse_mode="Markdown")


async def style_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /style command - show style selection menu."""
    user_id = update.effective_user.id

    # Check if user is authenticated
    access_code = check_user_access(user_id)
    if not access_code and user_id != ADMIN_ID:
        await update.message.reply_text(
            "🔒 Сначала активируйте код доступа с помощью /enter_code"
        )
        return

    # Get current style
    current_style = get_user_style(user_id)

    # Create style selection keyboard with Back button
    style_keyboard = []
    for style_key in get_all_styles():
        style_keyboard.append([KeyboardButton(get_style_name(style_key))])

    # Add "Back" button at the bottom
    style_keyboard.append([KeyboardButton("◀️ Назад")])

    reply_markup = ReplyKeyboardMarkup(style_keyboard, resize_keyboard=True)

    message = f"""🎨 *Выбор стиля редактирования*

Текущий стиль: {get_style_name(current_style)}

*Доступные стили:*

"""

    for style_key in get_all_styles():
        current_marker = "✅ " if style_key == current_style else ""
        message += f"{current_marker}{get_style_name(style_key)}\n"
        message += f"   _{get_style_description(style_key)}_\n\n"

    message += "💡 Выберите стиль из меню ниже или используйте:\n`/set_style <стиль>`"

    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")


async def set_style_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /set_style command - set specific style."""
    user_id = update.effective_user.id

    # Check authentication
    access_code = check_user_access(user_id)
    if not access_code and user_id != ADMIN_ID:
        await update.message.reply_text("🔒 Сначала активируйте код доступа")
        return

    # Get style from arguments
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ Укажите стиль.\n\n"
            "Доступные стили:\n"
            "• business_casual - 👔 Business Casual\n"
            "• formal - 🎩 Деловой строгий\n"
            "• basic - ✏️ Базовый\n"
            "• documentation - 📚 Документация\n"
            "• team_chat - 💬 Командный\n\n"
            "Пример: /set_style formal"
        )
        return

    style_arg = context.args[0].strip().lower()

    # Map style names/aliases to keys
    style_map = {
        "business_casual": "business_casual",
        "business": "business_casual",
        "casual": "business_casual",
        "формальный": "formal",
        "formal": "formal",
        "официальный": "formal",
        "базовый": "basic",
        "basic": "basic",
        "простой": "basic",
        "документация": "documentation",
        "documentation": "documentation",
        "docs": "documentation",
        "командный": "team_chat",
        "team_chat": "team_chat",
        "team": "team_chat",
        "чат": "team_chat"
    }

    style_key = style_map.get(style_arg)

    if not style_key:
        await update.message.reply_text(
            f"❌ Неизвестный стиль '{style_arg}'\n\n"
            "Используйте /style чтобы увидеть доступные стили"
        )
        return

    # Set user style
    success = set_user_style(user_id, style_key)

    if success:
        await update.message.reply_text(
            f"✅ Стиль изменён на {get_style_name(style_key)}!\n\n"
            f"_{get_style_description(style_key)}_"
        )
    else:
        await update.message.reply_text("❌ Ошибка при изменении стиля")


async def handle_scenario_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle scenario selection from keyboard."""
    user_id = update.effective_user.id
    text = update.message.text

    # Map scenario names to style keys
    scenario_to_style = {
        "📧 Email коллеге": "business_casual",
        "💬 Сообщение в чат": "team_chat",
        "📝 Документация": "documentation",
        "✉️ Официальное письмо": "formal",
        "✏️ Аккуратно отредактировать": "basic"
    }

    # Check if selected text is a scenario
    if text in scenario_to_style:
        selected_style = scenario_to_style[text]

        # Store in context.user_data (session-based, not database)
        context.user_data['selected_scenario'] = selected_style
        context.user_data['scenario_name'] = text

        logger.info(f"User {user_id} selected scenario: {text} ({selected_style})")

        # Show confirmation
        confirmation_message = f"""✅ **Выбрано:** {text}

Теперь отправьте голосовое или текст, который хотите отредактировать.

🎤 Голосовое — я транскрибирую и отредактирую
📝 Текст — я сразу отредактирую"""

        await update.message.reply_text(confirmation_message, parse_mode="Markdown")
        return True

    return False


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming voice messages."""
    user_id = update.effective_user.id
    start_time = time.time()

    # Get selected scenario from context (not database)
    user_style = context.user_data.get('selected_scenario', get_user_style(user_id))

    # If no scenario selected, prompt user to select one
    if user_style not in STYLE_PROMPTS:
        scenario_keyboard = [
            [KeyboardButton("📧 Email коллеге"), KeyboardButton("💬 Сообщение в чат")],
            [KeyboardButton("📝 Документация"), KeyboardButton("✉️ Официальное письмо")],
            [KeyboardButton("✏️ Аккуратно отредактировать")],
        ]
        reply_markup = ReplyKeyboardMarkup(scenario_keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "❗ Сначала выберите, что хотите создать:\n\n"
            "📧 Email коллеге\n"
            "💬 Сообщение в чат\n"
            "📝 Документация\n"
            "✉️ Официальное письмо\n"
            "✏️ Аккуратно отредактировать",
            reply_markup=reply_markup
        )
        return

    voice_file = await update.message.voice.get_file()

    # Download voice file
    temp_ogg = f"temp_voice_{update.message.message_id}.ogg"
    temp_wav = f"temp_voice_{update.message.message_id}.wav"
    await voice_file.download_to_drive(temp_ogg)

    # Convert .ogg to .wav for AssemblyAI
    try:
        logger.info(f"🔄 Converting {temp_ogg} to {temp_wav}")
        audio = AudioSegment.from_ogg(temp_ogg)
        audio.export(temp_wav, format="wav")

        # Calculate audio duration
        audio_duration = len(audio) / 1000.0  # Convert to seconds

        logger.info(f"✅ Conversion successful! Duration: {audio_duration:.1f}s")
    except Exception as e:
        logger.error(f"❌ Error converting audio: {e}")
        await update.message.reply_text(f"❌ Ошибка конвертации аудио: {str(e)}")
        if os.path.exists(temp_ogg):
            os.remove(temp_ogg)
        return

    await update.message.reply_text(f"🎤 Обрабатываю голосовое сообщение... (Стиль: {get_style_name(user_style)})")

    try:
        raw_text = await transcribe_audio(temp_wav)
        refined_text = await refine_text(raw_text, style=user_style)

        # Calculate processing time
        processing_time = time.time() - start_time

        # Log usage
        log_usage(
            telegram_user_id=user_id,
            message_type="voice",
            audio_duration=audio_duration,
            text_characters=len(raw_text),
            processing_time=processing_time
        )

        await update.message.reply_text(refined_text)
    except Exception as e:
        await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")
    finally:
        # Clean up temp files
        if os.path.exists(temp_ogg):
            os.remove(temp_ogg)
        if os.path.exists(temp_wav):
            os.remove(temp_wav)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages."""
    user_id = update.effective_user.id
    text = update.message.text

    # Check if admin button
    admin_buttons = ["📊 Статистика", "📋 Коды", "➕ Добавить коды", "❓ Справка"]
    if user_id == ADMIN_ID and text in admin_buttons:
        await handle_menu_buttons(update, context)
        return

    # Check if scenario selection
    scenario_selected = await handle_scenario_selection(update, context)
    if scenario_selected:
        return

    # If no scenario selected, prompt user
    if 'selected_scenario' not in context.user_data:
        scenario_keyboard = [
            [KeyboardButton("📧 Email коллеге"), KeyboardButton("💬 Сообщение в чат")],
            [KeyboardButton("📝 Документация"), KeyboardButton("✉️ Официальное письмо")],
            [KeyboardButton("✏️ Аккуратно отредактировать")],
        ]
        reply_markup = ReplyKeyboardMarkup(scenario_keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "❗ Сначала выберите, что хотите создать:\n\n"
            "📧 Email коллеге\n"
            "💬 Сообщение в чат\n"
            "📝 Документация\n"
            "✉️ Официальное письмо\n"
            "✏️ Аккуратно отредактировать",
            reply_markup=reply_markup
        )
        return

    raw_text = text
    start_time = time.time()

    # Get selected scenario from context (not database)
    user_style = context.user_data.get('selected_scenario', get_user_style(user_id))

    await update.message.reply_text(f"✍️ Редактирую текст... (Стиль: {get_style_name(user_style)})")

    try:
        refined_text = await refine_text(raw_text, style=user_style)

        # Calculate processing time
        processing_time = time.time() - start_time

        # Log usage
        log_usage(
            telegram_user_id=user_id,
            message_type="text",
            text_characters=len(raw_text),
            processing_time=processing_time
        )

        await update.message.reply_text(refined_text)
    except Exception as e:
        await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY environment variable not set")

    if not ASSEMBLYAI_API_KEY:
        raise ValueError("ASSEMBLYAI_API_KEY environment variable not set")

    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("enter_code", enter_code_command))
    application.add_handler(CommandHandler("admin_stats", admin_stats_command))
    application.add_handler(CommandHandler("seed_codes", seed_codes_command))
    application.add_handler(CommandHandler("style", style_command))
    application.add_handler(CommandHandler("set_style", set_style_command))

    # Add message handlers
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Start bot
    logger.info("🚀 Starting bot v2.0 with authentication...")
    logger.info("✅ Bot is running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
