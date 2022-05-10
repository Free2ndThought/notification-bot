import requests
import json
import telegram
from telegram.ext import Application,
from grafana_api.grafana_face import GrafanaFace

GET_UPDATE_SUFFIX = "getUpdates"
SEND_MESSAGE_SUFFIX = "sendMessage"

def auth_grafana():
    grafana_api = GrafanaFace(
        auth=("username", "password"),
        host='api.energy.uni-passau.de:8080'
    )

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    with open("token") as file:
        token = file.read()
    application = Application.builder().token(token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()


    bot = telegram.Bot(token=token)

    bot.