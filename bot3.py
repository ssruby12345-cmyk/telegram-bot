import os
import logging
from urllib.parse import urlparse

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

# =========================
# CONFIG
# =========================

BOT_TOKEN = "8782676728:AAH92BT7x_YTVq8TFmN6H4n5p5YXt2ywLwE"

# Your Telegram channel username
# Example: @mychannel
CHANNEL_ID = "-1003978393307"

# Optional admin Telegram user IDs
ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

# Conversation states
BUTTON_TEXT, BUTTON_URL, PHOTO = range(3)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================
# URL CHECK
# =========================

def valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.netloc)
        )
    except Exception:
        return False


# =========================
# HOME KEYBOARD
# =========================

def home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ Generate Button",
                    callback_data="generate",
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Cancel",
                    callback_data="cancel",
                )
            ],
        ]
    )


# =========================
# START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    context.user_data.clear()

    await update.message.reply_text(
        "Button Generator\n\n"
        "Press the button below to create a channel post.",
        reply_markup=home_keyboard(),
    )


# =========================
# GENERATE START
# =========================

async def generate_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query
    await query.answer()

    context.user_data.clear()

    await query.edit_message_text(
        "Send me the button text.\n\n"
        "Example:\n"
        "🎬 Watch Video"
    )

    return BUTTON_TEXT


# =========================
# RECEIVE BUTTON TEXT
# =========================

async def receive_button_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    text = update.message.text.strip()

    if not text:
        await update.message.reply_text(
            "Please send a button name."
        )
        return BUTTON_TEXT

    if len(text) > 64:
        await update.message.reply_text(
            "Button text is too long.\n"
            "Keep it under 64 characters."
        )
        return BUTTON_TEXT

    context.user_data["button_text"] = text

    await update.message.reply_text(
        "Now send the URL.\n\n"
        "Example:\n"
        "https://example.com"
    )

    return BUTTON_URL


# =========================
# RECEIVE BUTTON URL
# =========================

async def receive_button_url(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    url = update.message.text.strip()

    if not valid_url(url):
        await update.message.reply_text(
            "❌ Invalid URL.\n\n"
            "Use a full http:// or https:// URL."
        )
        return BUTTON_URL

    button_text = context.user_data.get(
        "button_text"
    )

    if not button_text:
        await update.message.reply_text(
            "Something went wrong.\n"
            "Use /start and try again."
        )

        return ConversationHandler.END

    context.user_data["button_url"] = url

    await update.message.reply_text(
        "✅ Button saved.\n\n"
        "Now send the PHOTO you want to post "
        "to your channel."
    )

    return PHOTO


# =========================
# RECEIVE PHOTO
# =========================

async def receive_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message.photo:
        await update.message.reply_text(
            "❌ Please send a photo."
        )
        return PHOTO

    button_text = context.user_data.get(
        "button_text"
    )

    button_url = context.user_data.get(
        "button_url"
    )

    if not button_text or not button_url:
        await update.message.reply_text(
            "Something went wrong.\n"
            "Use /start and try again."
        )

        return ConversationHandler.END

    # Create button
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    button_text,
                    url=button_url,
                )
            ]
        ]
    )

    # Get highest quality photo
    photo = update.message.photo[-1].file_id

    try:

        await context.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=photo,
            reply_markup=keyboard,
        )

        await update.message.reply_text(
            "✅ Done!\n\n"
            "The photo + button has been sent "
            "to your channel."
        )

    except Exception as e:

        logger.exception(
            "Failed to send photo to channel"
        )

        await update.message.reply_text(
            "❌ I couldn't send the post "
            "to the channel.\n\n"
            "Check that:\n"
            "• The channel username is correct\n"
            "• The bot is an admin in the channel\n"
            "• The bot has permission to post messages"
        )

    context.user_data.clear()

    return ConversationHandler.END


# =========================
# CANCEL
# =========================

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    context.user_data.clear()

    if update.callback_query:

        query = update.callback_query

        await query.answer()

        await query.edit_message_text(
            "Cancelled.",
            reply_markup=home_keyboard(),
        )

    else:

        await update.message.reply_text(
            "Cancelled.",
            reply_markup=home_keyboard(),
        )

    return ConversationHandler.END


# =========================
# HELP
# =========================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "How to use:\n\n"
        "1. Press Generate Button\n"
        "2. Send the button text\n"
        "3. Send the URL\n"
        "4. Send the photo\n"
        "5. Bot sends the photo + button "
        "to your channel.\n\n"
        "/start - Main menu\n"
        "/cancel - Cancel current operation"
    )


# =========================
# ERROR HANDLER
# =========================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.exception(
        "Unhandled exception:",
        exc_info=context.error,
    )


# =========================
# MAIN
# =========================

def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is empty. "
            "Put your Telegram bot token in BOT_TOKEN."
        )

    if CHANNEL_ID == "@YOUR_CHANNEL_USERNAME":
        raise RuntimeError(
            "Set CHANNEL_ID to your Telegram channel username."
        )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    conversation = ConversationHandler(

        entry_points=[
            CallbackQueryHandler(
                generate_start,
                pattern=r"^generate$",
            )
        ],

        states={

            BUTTON_TEXT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_button_text,
                )
            ],

            BUTTON_URL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_button_url,
                )
            ],

            PHOTO: [
                MessageHandler(
                    filters.PHOTO,
                    receive_photo,
                )
            ],
        },

        fallbacks=[
            CommandHandler(
                "cancel",
                cancel,
            ),

            CallbackQueryHandler(
                cancel,
                pattern=r"^cancel$",
            ),
        ],

        allow_reentry=True,
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("help", help_command)
    )

    application.add_handler(
        CommandHandler("cancel", cancel)
    )

    application.add_handler(conversation)

    application.add_handler(
        CallbackQueryHandler(
            cancel,
            pattern=r"^cancel$",
        )
    )

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Button Generator Bot started."
    )

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()


