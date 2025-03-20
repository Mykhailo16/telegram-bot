import logging
import os
import random
import re
import sqlite3

import psycopg2

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CallbackQueryHandler, CommandHandler, Updater

#################################################################################################################
# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
#################################################################################################################

database_config = None

#################################################################################################################

async def send_message(update, context, text):
    text = text.encode('utf16', errors='surrogatepass').decode('utf16')
    return await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode="markdown")

async def send_buttons(update, context, text, buttons):
    text = text.encode('utf16', errors='surrogatepass').decode('utf16')
    keyboard = []
    for key, value in buttons.items():
        if key.startswith("https://t.me/"):
            button = InlineKeyboardButton(str(value), url=str(key))
        else:
            button = InlineKeyboardButton(str(value), callback_data=str(key))
        keyboard.append([button])
    reply_markup = InlineKeyboardMarkup(keyboard)
    return await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="markdown")

#################################################################################################################

def get_user(user_id):
    users_list = []
    try:
        with psycopg2.connect(database_config) as conn:
            with conn.cursor() as cur:
                query = 'SELECT user_id, stage, wallet_id FROM Users WHERE user_id = %s'
                cur.execute(query, (user_id,))
                rows = cur.fetchall()

                for user in rows:
                    user_dict = {
                        'user_id': user[0],
                        'stage': user[1],
                        'wallet_id': user[2]
                    }
                    users_list.append(user_dict)

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
    finally:
        if len(users_list) > 0:
            return users_list[0]
        else:
            return None

def create_user(user_id):
    try:
        with psycopg2.connect(database_config) as conn:
            with conn.cursor() as cur:
                query = "INSERT INTO Users (user_id, stage) VALUES (%s, %s)"
                cur.execute(query, (user_id, "register"))
                conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)

def update_user_stage(user_id, stage):
    try:
        with psycopg2.connect(database_config) as conn:
            with conn.cursor() as cur:
                query = "UPDATE Users SET stage = %s WHERE user_id = %s"
                cur.execute(query, (stage, user_id))
                conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)

def update_user_wallet(user_id, wallet_id):
    try:
        with psycopg2.connect(database_config) as conn:
            with conn.cursor() as cur:
                query = "UPDATE Users SET wallet_id = %s WHERE user_id = %s"
                cur.execute(query, (wallet_id, user_id))
                conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)

def update_user_promo_code(user_id, promo_code):
    try:
        with psycopg2.connect(database_config) as conn:
            with conn.cursor() as cur:
                query = "UPDATE Users SET promo_code = %s WHERE user_id = %s"
                cur.execute(query, (promo_code, user_id))
                conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)

def get_available_promo_code():
    available_promo_codes = []

    try:
        with psycopg2.connect(database_config) as conn:
            with conn.cursor() as cur:
                query = 'SELECT promo_code FROM PromoCodes'
                cur.execute(query)
                rows = cur.fetchall()

                for promo_code in rows:
                    available_promo_codes.append(promo_code[0])

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
    finally:
        return available_promo_codes

def get_user_promo_code(user_id):
    user_promo_code = None

    try:
        with psycopg2.connect(database_config) as conn:
            with conn.cursor() as cur:
                query = 'SELECT promo_code FROM Users WHERE user_id = %s'
                cur.execute(query, (user_id,))
                rows = cur.fetchall()
                for row in rows:
                    user_promo_code = row[0]
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
    finally:
        return user_promo_code

def save_user_input(user_id, user_input):
    try:
        with psycopg2.connect(database_config) as conn:
            with conn.cursor() as cur:
                query = "INSERT INTO UserInputs (user_id, user_input) VALUES (%s, %s)"
                cur.execute(query, (user_id, user_input))
                conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)

#################################################################################################################

async def start(update, context):
    message = "Estamos muito felizes por ter você com a gente! Bora ganhar dinheiro fácil!"
    await send_buttons(update, context, message, {
        "register": "Resgatar código promocional",
        "report": "Enviar o relatório",
        "https://t.me/RoDrIgO_MATEO": "Suporte"
    })

async def register(update, context):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if user is None:
        create_user(user_id)
        await send_message(update, context, "Primeiro, por favor, envie sua carteira cripto para receber seus pagamentos futuros! (TRC20)")
    else:
        await send_user_promo_code(update, context)

async def report(update, context):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if user is not None:
        update_user_stage(user_id, 'report')
        await send_message(update, context, "Quando seu amigo se registrou?")
    else:
        await send_message(update, context, "Primeiro, cê tem que pegar o código promocional e mandar sua carteira cripto!")

async def support(update, context):
    await send_message(update, context, "[https://t.me/RoDrIgO_MATEO](https://t.me/RoDrIgO_MATEO)")

async def input_text(update, context):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if user is not None:
        text = update.message.text
        if user['stage'] == "register":
            if (re.fullmatch("T[A-Za-z1-9]{33}", text)):
                update_user_wallet(user_id, text)
                available_promo_codes = get_available_promo_code()
                user_promo_code = random.choice(available_promo_codes)
                update_user_promo_code(user_id, user_promo_code)

                await send_user_promo_code(update, context)
                await send_message(update, context, "Aqui está seu código promocional! E não se esqueça de entrar no nosso grupo no Telegram: [https://t.me/amigo_bonuses](https://t.me/amigo_bonuses) , para não perder bônus e informações exclusivas!")

                update_user_stage(user_id, 'home')
            else:
                await send_message(update, context, "Isso aí não parece uma carteira cripto!")

        elif user['stage'] == "report":
            if (re.fullmatch("([0-9]|[01][0-9]|2[0-3]):([0-5][0-9])", text)):
                save_user_input(user_id, text)
                await send_message(update, context, "Obrigado! Quanto mais amigos, mais grana!")

                update_user_stage(user_id, 'home')
            else:
                await send_message(update, context, "Isso não parece uma hora!")



    else:
        await send_message(update, context, "Primeiro, cê tem que pegar o código promocional e mandar sua carteira cripto!")



async def send_user_promo_code(update, context):
    user_id = update.effective_user.id
    user_promo_code = get_user_promo_code(user_id)
    if user_promo_code is not None:
        await send_message(update, context, "Valeu! Agora você está oficialmente com a gente. Aqui está seu código promocional:")
        await send_message(update, context, "" + user_promo_code)
    update_user_stage(user_id, 'home')

async def buttons_handler(update, context):
    query = update.callback_query.data
    await update.callback_query.answer()
    if query == "register":
        await register(update, context)
    elif query == "report":
        await report(update, context)


def main():
    load_dotenv()
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]

    global database_config
    database_config = os.environ["DATABASE_URL"]

    app = ApplicationBuilder().token(bot_token).build()
    app.add_handler(CallbackQueryHandler(buttons_handler))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("support", support))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, input_text))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

    logger.info("Initialized bot.")

if __name__ == "__main__":
    main()
