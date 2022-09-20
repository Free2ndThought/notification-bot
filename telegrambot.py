import logging
import random

import grafana_api.grafana_api
import string
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, ChatMember
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    Application
)
from os.path import exists as file_exists
from cryptography.fernet import Fernet


def id_generator(size=12, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

MENU, PHOTO, LOCATION, BIO, REGISTER, FEEDBACK = range(6)

from grafana_api.grafana_face import GrafanaFace

global encrypter


def auth_grafana(host='api.energy.uni-passau.de:8080') -> GrafanaFace:
    with open('graf.auth') as auth_file:
        username = auth_file.readline()
        password = auth_file.readline()
        return GrafanaFace(
            auth=(username, password),
            host=host
        )


async def start(update: Update) -> int:
    """Starts the conversation and asks the user about their gender."""
    reply_keyboard_register = [["Yes", "No"]]
    reply_keyboard_menu = [["Stats today", "Devices", "Help"]]
    user = update.message.from_user

    await  update.message.reply_text(f"Hello {user.first_name}, welcome to the RPMT notification beta application "
                                     "Send /cancel to stop talking to me.")

    if not file_exists(f'user/{update.message.from_user.id}'):
        await update.message.reply_text(
            "Apparently you have not yet used our service.\n\n"
            "Do you want to register an account?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard_register,
                                             one_time_keyboard=True,
                                             input_field_placeholder="Choose an item"
                                             ),
        )
        return REGISTER
    else:
        await  update.message.reply_text(f"How can I help you today",
                                         reply_markup=ReplyKeyboardMarkup(reply_keyboard_menu,
                                                                          one_time_keyboard=True,
                                                                          input_field_placeholder="Choose an item"
                                                                          )
                                         )
        return MENU


async def register(update: Update) -> int:
    """Creates a new user using the grafana api, and saves user credentials in an id folder"""
    grafana = auth_grafana()
    user_login_id = id_generator()
    user_login_pw = id_generator()
    with open(f'users/{update.message.from_user.id}', 'wb') as cred_file:
        cred_file.write(encrypter.encrypt(user_login_id))
        cred_file.write(encrypter.encrypt(user_login_pw))
        cred_file.close()

    new_user = {
        "name": f"{update.message.from_user.full_name}",
        "email": "user@graf.com",
        "login": f'{user_login_id}',
        "password": f'{user_login_pw}',
        "OrgId": 1
    }
    grafana.admin.create_user(new_user)

    return MENU


async def menu(update: Update) -> int:
    """Stores the selected gender and asks for a photo."""
    user = update.message.from_user
    logger.info("User %s entered to %s", user.first_name, update.message.text)
    await update.message.reply_text(
        "I see! Please send me a photo of yourself, "
        "so I know what you look like, or send /skip if you don't want to.",
        reply_markup=ReplyKeyboardRemove(),
    )

    return FEEDBACK


async def feedback(update: Update) -> int:
    """Stores the location and asks for some info about the user."""
    user = update.message.from_user
    user_feedback = await update.message.text
    logger.info(
        f"{user.first_name} gave the following feedback: {user_feedback}"
    )
    await update.message.reply_text(
        "Thank you for your feedback"
    )

    return MENU

async def skip_feedback(update: Update) -> int:
    """Stores the location and asks for some info about the user."""
    user = update.message.from_user
    logger.info(
        "%s has chosen to provide no feedback ", user.first_name
    )
    await update.message.reply_text(
        "This concludes the review of your energy consumption. Thank you for your participation"
    )

    return MENU


async def cancel(update: Update) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        "Thank you for your participation. Goodbye!", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def main() -> None:
    """Run the bot."""
    #global encrypter
    #if not file_exists('.k.ey'):
    #    key = Fernet.generate_key()
    #    with open(".k.ey", "wb") as key_file:
    #        key_file.write(key)
    #        encrypter = Fernet(key)
    #else:
    #    with open(".k.ey", "rb") as key_file:
    #        key = key_file.read()
    #        encrypter = Fernet(key)
#
    #if not file_exists('graf.auth'):
    #    with open("graf.auth", 'wb') as auth_file:
    #        username_graf = password_graf = b'admin'
    #        encr_username = encrypter.encrypt(username_graf)
    #        encr_password = encrypter.encrypt(password_graf)
    #        auth_file.write(encr_username)
    #        auth_file.write(encr_password)
    #else:
    #    with open('graf.auth', 'rb') as auth_file:
    #        username_graf = encrypter.decrypt(auth_file.readline())
    #        password_graf = encrypter.decrypt(auth_file.readline())


    # Create the Application and pass it your bot's token.
    with open("token") as file:
        token = file.read()
        application = Application.builder().token(token=token).build()

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [MessageHandler(filters.Regex("^(Register|LogIn|Other)$"), menu)],
            FEEDBACK: [MessageHandler(filters.TEXT, menu), CommandHandler("skip", skip_feedback)],
            REGISTER: [MessageHandler(filters.Regex("Yes"), register),
                       MessageHandler(filters.Regex("No"), cancel)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
