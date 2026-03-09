"""
HelpWriter Bot - Version 2.1
Writing assistant for blogs, websites, articles, and reviews.

Version: 2.1.0
Author: Created with assistance from Claude
"""

from dotenv import load_dotenv
load_dotenv()

import os
import logging
import asyncio
import time
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, PreCheckoutQueryHandler, filters, ContextTypes
from openai import OpenAI
import assemblyai as aai
from pydub import AudioSegment
from database import (check_user_access, assign_code_to_user, log_usage, get_admin_stats,
                      add_access_code, get_all_access_codes, get_user_style, set_user_style,
                      get_active_subscription, create_subscription, get_expiring_subscriptions,
                      deactivate_expired_subscriptions, get_subscription_stats)
from style_prompts import get_style_prompt, get_style_name, get_style_description, get_all_styles, STYLE_NAMES, STYLE_PROMPTS

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
# AUTHENTICATION MIDDLEWARE
# =============================================================================

SUBSCRIPTION_PRICE_STARS = 150  # 1 month
SUBSCRIPTION_DAYS = 30


async def require_auth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if user has access.
    Priority: admin → manual code → active subscription → paywall.
    """
    user_id = update.effective_user.id

    if user_id == ADMIN_ID:
        return True

    # Manual access code (legacy, non-auto codes)
    access_code = check_user_access(user_id)
    if access_code and not access_code.startswith("auto_"):
        return True

    # Paid subscription
    deactivate_expired_subscriptions()
    if get_active_subscription(user_id):
        return True

    # No access — show paywall
    await update.message.reply_text(
        "⭐ *Для использования бота нужна подписка*\n\n"
        "Стоимость: *150 звёзд / месяц* (~200 ₽)\n\n"
        "Что входит:\n"
        "• Транскрибация голоса\n"
        "• Структурирование текста\n"
        "• Развитие идей\n\n"
        "Нажмите кнопку ниже, чтобы оплатить:",
        parse_mode="Markdown"
    )
    await context.bot.send_invoice(
        chat_id=user_id,
        title="Подписка HelpWriter — 1 месяц",
        description="30 дней доступа ко всем режимам обработки текста",
        payload=f"subscription_30d_{user_id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice("1 месяц", SUBSCRIPTION_PRICE_STARS)],
    )
    return False


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
# TEXT PROCESSING FUNCTION (DeepSeek)
# =============================================================================

async def refine_text(raw_text: str, style: str = "transcription") -> str:
    """Process text using DeepSeek model with specified mode."""
    try:
        logger.info(f"Processing text with DeepSeek... Mode: {style}")

        # Get mode-specific prompt
        style_prompt = get_style_prompt(style)

        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": style_prompt},
                {"role": "user", "content": f"Обработай этот текст:\n\n{raw_text}"}
            ],
            temperature=0.7
        )

        logger.info(f"✅ DeepSeek response received successfully")
        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"❌ Error processing text: {e}")
        raise Exception(f"Ошибка обработки: {str(e)}")


# =============================================================================
# KEYBOARD HELPERS
# =============================================================================

def get_mode_keyboard():
    """Get processing mode selection keyboard."""
    keyboard = [
        [KeyboardButton("✏️ Аккуратная транскрибация")],
        [KeyboardButton("📋 Структура и план")],
        [KeyboardButton("💡 Идеи")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_main_keyboard(is_admin=False):
    """Get main menu keyboard based on user role."""
    if is_admin:
        keyboard = [
            [KeyboardButton("📊 Статистика"), KeyboardButton("📋 Коды")],
            [KeyboardButton("➕ Добавить коды")],
            [KeyboardButton("❓ Справка")],
        ]
    else:
        keyboard = []

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True) if keyboard else None


# Map button text to mode keys
MODE_BUTTON_MAP = {
    "✏️ Аккуратная транскрибация": "transcription",
    "📋 Структура и план": "structure",
    "💡 Идеи": "ideas",
}


# =============================================================================
# TELEGRAM HANDLERS
# =============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - show mode selection keyboard."""
    reply_markup = get_mode_keyboard()

    welcome_message = """👋 Привет! Я — HelpWriter, помощник для написания текстов.

**Как это работает:**
1. Выберите режим обработки
2. Отправьте голосовое или текст
3. Получите готовый результат

**Режимы:**
✏️ Аккуратная транскрибация — диктуйте, я аккуратно отредактирую
📋 Структура и план — диктуйте мысли, я верну план материала
💡 Идеи — набросайте идею, я предложу углы для раскрытия

🎯 **Выберите режим:**"""

    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="Markdown")


async def enter_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /enter_code command."""
    user_id = update.effective_user.id

    # Check if already authenticated
    existing_code = check_user_access(user_id)
    if existing_code:
        current_mode = get_user_style(user_id)
        await update.message.reply_text(
            f"✅ У вас уже есть доступ!\n\n"
            f"Ваш код: {existing_code}\n\n"
            f"Текущий режим: {get_style_name(current_mode)}\n\n"
            f"Бот готов к работе.",
            reply_markup=get_mode_keyboard()
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

    if success:
        await update.message.reply_text(
            message + "\n\nВыберите режим обработки текста:",
            reply_markup=get_mode_keyboard()
        )
    else:
        await update.message.reply_text(message)


async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin_stats command - only for admin."""
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав для этой команды.")
        return

    sub_stats = get_subscription_stats()
    stars_rub = round(sub_stats["stars_last_30d"] * 0.02 * 90 * 0.7)  # after Telegram 30% cut

    message = (
        "📊 **Статистика использования бота**\n\n"
        f"⭐ *Подписки:* {sub_stats['active_subscriptions']} активных\n"
        f"💰 *Выручка за 30 дней:* {sub_stats['stars_last_30d']} звёзд (~{stars_rub} ₽ после комиссии)\n\n"
        "— — —\n\n"
    )

    stats = get_admin_stats()

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

    # Only admin can use admin menu buttons
    if user_id != ADMIN_ID:
        return False

    if text == "📊 Статистика":
        await admin_stats_command(update, context)
        return True
    elif text == "📋 Коды":
        await list_codes_command(update, context)
        return True
    elif text == "➕ Добавить коды":
        await update.message.reply_text(
            "➕ *Добавление кодов*\n\n"
            "Отправьте коды для добавления в формате:\n"
            "`/seed_codes код1 код2 код3`",
            parse_mode="Markdown"
        )
        return True
    elif text == "❓ Справка":
        help_text = """❓ *Админ-справка*

*Доступные команды:*

📊 /admin\\_stats - Полная статистика по всем кодам

📋 /seed\\_codes - Управление кодами доступа
   • Без аргументов: показать существующие коды
   • С аргументами: `/seed_codes код1 код2 код3`

*Через CLI на сервере:*
```bash
python manage_codes.py add код1 код2
python manage_codes.py list
python manage_codes.py stats
python manage_codes.py remove код
```"""
        await update.message.reply_text(help_text, parse_mode="Markdown")
        return True

    return False


async def list_codes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of all access codes."""
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав для этой команды.")
        return

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
        message += f"   Режим: {get_style_name(preferred_style)}\n"
        if assigned_at:
            message += f"   📅 {assigned_at}\n"
        message += "\n"

    await update.message.reply_text(message, parse_mode="Markdown")


async def handle_mode_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handle processing mode selection from keyboard."""
    text = update.message.text
    user_id = update.effective_user.id

    if text not in MODE_BUTTON_MAP:
        return False

    selected_mode = MODE_BUTTON_MAP[text]

    # Store in context.user_data (session-based)
    context.user_data['selected_scenario'] = selected_mode
    context.user_data['scenario_name'] = text

    logger.info(f"User {user_id} selected mode: {text} ({selected_mode})")

    if selected_mode == "transcription":
        confirmation = f"""✅ Режим: {text}

Отправьте голосовое или текст — я аккуратно отредактирую, сохранив ваш стиль.

🎤 Голосовое — транскрибирую и отредактирую
📝 Текст — сразу отредактирую"""
    elif selected_mode == "structure":
        confirmation = f"""✅ Режим: {text}

Надиктуйте или напишите ваши мысли — я верну структурированный план материала.

🎤 Голосовое — транскрибирую и создам план
📝 Текст — сразу создам план"""
    else:
        confirmation = f"""✅ Режим: {text}

Набросайте идею — факт, новость, наблюдение, мысль. Я предложу 4-6 углов под которыми это можно раскрыть.

🎤 Голосовое — транскрибирую и разберу углы
📝 Текст — сразу разберу углы"""

    await update.message.reply_text(confirmation, parse_mode="Markdown")
    return True


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming voice messages."""
    if not await require_auth(update, context):
        return

    user_id = update.effective_user.id
    start_time = time.time()

    # Get selected mode from context (fallback to database preference)
    user_style = context.user_data.get('selected_scenario', get_user_style(user_id))

    # If no mode selected, prompt user to select one
    if user_style not in STYLE_PROMPTS:
        await update.message.reply_text(
            "❗ Сначала выберите режим обработки:",
            reply_markup=get_mode_keyboard()
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

        audio_duration = len(audio) / 1000.0  # Convert to seconds

        logger.info(f"✅ Conversion successful! Duration: {audio_duration:.1f}s")
    except Exception as e:
        logger.error(f"❌ Error converting audio: {e}")
        await update.message.reply_text(f"❌ Ошибка конвертации аудио: {str(e)}")
        if os.path.exists(temp_ogg):
            os.remove(temp_ogg)
        return

    await update.message.reply_text(f"🎤 Обрабатываю... ({get_style_name(user_style)})")

    try:
        raw_text = await transcribe_audio(temp_wav)
        refined_text = await refine_text(raw_text, style=user_style)

        processing_time = time.time() - start_time

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
        if os.path.exists(temp_ogg):
            os.remove(temp_ogg)
        if os.path.exists(temp_wav):
            os.remove(temp_wav)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages."""
    user_id = update.effective_user.id
    text = update.message.text

    # Check if admin button (before auth check — admin always has access)
    admin_buttons = ["📊 Статистика", "📋 Коды", "➕ Добавить коды", "❓ Справка"]
    if user_id == ADMIN_ID and text in admin_buttons:
        await handle_menu_buttons(update, context)
        return

    # Check if mode selection (before auth — let user pick mode, auth checked when processing)
    mode_selected = await handle_mode_selection(update, context)
    if mode_selected:
        return

    # Auth check before actual processing
    if not await require_auth(update, context):
        return

    # If no mode selected, prompt user
    if 'selected_scenario' not in context.user_data:
        await update.message.reply_text(
            "❗ Сначала выберите режим обработки:",
            reply_markup=get_mode_keyboard()
        )
        return

    raw_text = text
    start_time = time.time()

    user_style = context.user_data.get('selected_scenario', get_user_style(user_id))

    await update.message.reply_text(f"✍️ Обрабатываю... ({get_style_name(user_style)})")

    try:
        refined_text = await refine_text(raw_text, style=user_style)

        processing_time = time.time() - start_time

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
# PAYMENT HANDLERS
# =============================================================================

async def handle_precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm pre-checkout — required by Telegram before charging."""
    await update.pre_checkout_query.answer(ok=True)


async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful Stars payment — create subscription."""
    user_id = update.effective_user.id
    payment = update.message.successful_payment

    create_subscription(
        telegram_user_id=user_id,
        payment_id=payment.telegram_payment_charge_id,
        stars_amount=payment.total_amount,
        period_days=SUBSCRIPTION_DAYS,
    )

    await update.message.reply_text(
        "✅ *Оплата прошла успешно!*\n\n"
        f"Подписка активна на {SUBSCRIPTION_DAYS} дней.\n\n"
        "Выберите режим и отправляйте голосовые или текст:",
        parse_mode="Markdown",
        reply_markup=get_mode_keyboard()
    )


async def subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /subscription command — show subscription status."""
    user_id = update.effective_user.id

    if user_id == ADMIN_ID:
        await update.message.reply_text("👑 Вы администратор — доступ без подписки.")
        return

    code = check_user_access(user_id)
    if code and not code.startswith("auto_"):
        await update.message.reply_text(f"🔑 У вас ручной код доступа: `{code}`", parse_mode="Markdown")
        return

    sub = get_active_subscription(user_id)
    if sub:
        expires = sub["expires_at"][:10]  # YYYY-MM-DD
        await update.message.reply_text(
            f"✅ *Подписка активна*\n\n"
            f"Истекает: *{expires}*\n\n"
            "Чтобы продлить заранее, нажмите кнопку:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Продлить — 150 ⭐", callback_data="renew_subscription")
            ]])
        )
    else:
        await update.message.reply_text("❌ Подписка не активна.")
        await context.bot.send_invoice(
            chat_id=user_id,
            title="Подписка HelpWriter — 1 месяц",
            description="30 дней доступа ко всем режимам обработки текста",
            payload=f"subscription_30d_{user_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice("1 месяц", SUBSCRIPTION_PRICE_STARS)],
        )


async def send_expiry_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Daily job: remind users whose subscription expires in 3 days."""
    deactivate_expired_subscriptions()
    expiring = get_expiring_subscriptions(days_before=3)
    for entry in expiring:
        user_id = entry["user_id"]
        expires = entry["expires_at"][:10]
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"⏳ *Подписка истекает {expires}*\n\n"
                    "Продлите, чтобы не потерять доступ:"
                ),
                parse_mode="Markdown"
            )
            await context.bot.send_invoice(
                chat_id=user_id,
                title="Продление HelpWriter — 1 месяц",
                description="30 дней доступа ко всем режимам обработки текста",
                payload=f"subscription_30d_{user_id}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice("1 месяц", SUBSCRIPTION_PRICE_STARS)],
            )
        except Exception as e:
            logger.warning(f"Could not send reminder to {user_id}: {e}")


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

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("enter_code", enter_code_command))
    application.add_handler(CommandHandler("admin_stats", admin_stats_command))
    application.add_handler(CommandHandler("seed_codes", seed_codes_command))
    application.add_handler(CommandHandler("subscription", subscription_command))

    # Payment handlers
    application.add_handler(PreCheckoutQueryHandler(handle_precheckout))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))

    # Add message handlers
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Daily reminder job (requires python-telegram-bot[job-queue])
    if application.job_queue:
        import datetime
        application.job_queue.run_daily(
            send_expiry_reminders,
            time=datetime.time(hour=10, minute=0),
        )
        logger.info("✅ Expiry reminder job scheduled at 10:00 daily")
    else:
        logger.warning("⚠️ job_queue not available — expiry reminders disabled. Install python-telegram-bot[job-queue]")

    # Start bot
    logger.info("🚀 Starting HelpWriter bot v2.2...")
    logger.info("✅ Bot is running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=["message", "pre_checkout_query"])


if __name__ == "__main__":
    main()
