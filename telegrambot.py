import logging
import random

import grafana_api.grafana_api
import string
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    CallbackContext,
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

MENU, PHOTO, LOCATION, BIO, REGISTER = range(5)

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


async def start(update: Update, callback: CallbackContext.DEFAULT_TYPE) -> int:
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


async def register(update: Update, callback: CallbackContext.DEFAULT_TYPE) -> int:
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


async def menu(update: Update, callback: CallbackContext.DEFAULT_TYPE) -> int:
    """Stores the selected gender and asks for a photo."""
    user = update.message.from_user
    logger.info("User %s entered to %s", user.first_name, update.message.text)
    await update.message.reply_text(
        "I see! Please send me a photo of yourself, "
        "so I know what you look like, or send /skip if you don't want to.",
        reply_markup=ReplyKeyboardRemove(),
    )

    return PHOTO


async def photo(update: Update, callback: CallbackContext.DEFAULT_TYPE) -> int:
    """Stores the photo and asks for a location."""
    user = update.message.from_user
    photo_file = await update.message.photo[-1].get_file()
    await photo_file.download("user_photo.jpg")
    logger.info("Photo of %s: %s", user.first_name, "user_photo.jpg")
    await update.message.reply_text(
        "Gorgeous! Now, send me your location please, or send /skip if you don't want to."
    )

    return LOCATION


async def skip_photo(update: Update, callback: CallbackContext.DEFAULT_TYPE) -> int:
    """Skips the photo and asks for a location."""
    user = update.message.from_user
    logger.info("User %s did not send a photo.", user.first_name)
    await update.message.reply_text(
        "I bet you look great! Now, send me your location please, or send /skip."
    )

    return LOCATION


async def location(update: Update, callback: CallbackContext.DEFAULT_TYPE) -> int:
    """Stores the location and asks for some info about the user."""
    user = update.message.from_user
    user_location = update.message.location
    logger.info(
        "Location of %s: %f / %f", user.first_name, user_location.latitude, user_location.longitude
    )
    await update.message.reply_text(
        "Maybe I can visit you sometime! At last, tell me something about yourself."
    )

    return BIO


async def skip_location(update: Update, callback: CallbackContext.DEFAULT_TYPE) -> int:
    """Skips the location and asks for info about the user."""
    user = update.message.from_user
    logger.info("User %s did not send a location.", user.first_name)
    await update.message.reply_text(
        "You seem a bit paranoid! At last, tell me something about yourself."
    )

    return BIO


async def bio(update: Update, callback: CallbackContext.DEFAULT_TYPE) -> int:
    """Stores the info about the user and ends the conversation."""
    user = update.message.from_user
    logger.info("Bio of %s: %s", user.first_name, update.message.text)
    await update.message.reply_text("Thank you! I hope we can talk again some day.")

    return ConversationHandler.END


async def cancel(update: Update, callback: CallbackContext.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        "Bye! I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def main() -> None:
    """Run the bot."""
    global encrypter
    if not file_exists('k.ey'):
        key = Fernet.generate_key()
        with open("k.ey", "wb") as key_file:
            key_file.write(key)
            encrypter = Fernet(key)
    else:
        with open("k.ey", "rb") as key_file:
            key = key_file.read()
            encrypter = Fernet(key)

    if not file_exists('graf.auth'):
        with open("graf.auth", 'wb') as auth_file:
            username_graf = password_graf = b'admin'
            encr_username = encrypter.encrypt(username_graf)
            encr_password = encrypter.encrypt(password_graf)
            auth_file.write(encr_username)
            auth_file.write(encr_password)
    else:
        with open('graf.auth', 'rb') as auth_file:
            username_graf = encrypter.decrypt(auth_file.readline())
            password_graf = encrypter.decrypt(auth_file.readline())

    # Create the Application and pass it your bot's token.
    with open("token") as file:
        token = file.read()
        application = Application.builder().token(token).build()

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [MessageHandler(filters.Regex("^(Register|LogIn|Other)$"), menu)],

            PHOTO: [MessageHandler(filters.PHOTO, photo), CommandHandler("skip", skip_photo)],
            LOCATION: [
                MessageHandler(filters.LOCATION, location),
                CommandHandler("skip", skip_location),
            ],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, bio)],
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
