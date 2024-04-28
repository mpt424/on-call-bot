import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from on_call_bot.configuration import TOKEN
from on_call_bot.consts import TIME_RANGE_REGEX
from on_call_bot.core import (
    button,
    done,
    global_init,
    identify_name,
    start,
    time_range_handler,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def start_bot():
    application = Application.builder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex(TIME_RANGE_REGEX), time_range_handler),
        ],
        states={
            0: [
                MessageHandler(filters.Regex(r"^(\w\W?)+$"), identify_name),
            ]
        },
        allow_reentry=True,
        fallbacks=[MessageHandler(filters.Regex("^Done$"), done)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button))
    global_init()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    try:
        start_bot()
    except Exception as e:
        logging.exception(str(e))
