# TODO
# ! Почистить говнокод в process_facult

from dotenv import load_dotenv
import os
from code.logging import logger
import asyncio
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
from telebot.asyncio_handler_backends import State, StatesGroup
from telebot.states.asyncio.middleware import StateMiddleware
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot import asyncio_filters

from code.database.classes.namespaced import getRowNamespaces
from code.database.repo.queries import connectDB, isExists, getAll

load_dotenv()
TOKEN = os.getenv("API_KEY")
bot = AsyncTeleBot(TOKEN, state_storage=StateMemoryStorage())

bot.add_custom_filter(asyncio_filters.StateFilter(bot))
bot.setup_middleware(StateMiddleware(bot))

class RegStates(StatesGroup):
    wait_for_name = State()
    wait_for_surname = State()
    wait_for_group = State()
    wait_for_facult = State()
    wait_for_chair = State()
    wait_for_direction = State()
    accept_registration = State()
class MenuStates(StatesGroup):
    main_menu = State()
@bot.message_handler(commands=['start'])
async def start(message):
    logger.debug('/start command')
    userID = str(message.from_user.id)
    database = connectDB()
    isUserExists, _ = isExists(database=database, table="USERS", filters={"telegram_id": userID})
    database.close()
    if not isUserExists:
        text = 'Похоже, что вы не зарегистрированы. Если хотите пройти регистрацию вызовите команду `register`'
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("Зарегистрироваться", callback_data="register"))
        await bot.reply_to(message, text, reply_markup=kb)

# Registration
@bot.callback_query_handler(func=lambda call: call.data == 'register')
async def callback_start_register(call):
    await bot.answer_callback_query(call.id)
    try:
        await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception:
        pass
    await cmd_register(userID=call.from_user.id, chatID = call.message.chat.id)

@bot.message_handler(commands=['register'])
async def cmd_register(message=None, userID=None, chatID=None):
    if userID is None:
        userID = message.from_user.id
    if chatID is None:
        chatID = message.chat.id

    await bot.set_state(userID, RegStates.wait_for_name, chatID)
    await bot.send_message(chatID, "Введите имя:")

@bot.message_handler(state=RegStates.wait_for_name)
async def process_name(message=None):
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['name'] = message.text
    await bot.set_state(message.from_user.id, RegStates.wait_for_surname, message.chat.id)
    await bot.send_message(message.chat.id, "Введите фамилию:")

@bot.message_handler(state=RegStates.wait_for_surname)
async def process_surname(message):
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['surname'] = message.text
    await bot.set_state(message.from_user.id, RegStates.wait_for_group, message.chat.id)
    await bot.send_message(message.chat.id, "Из какой вы группы?")

@bot.message_handler(state=RegStates.wait_for_group)
async def process_group(message):
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['group'] = message.text
    await bot.set_state(message.from_user.id, RegStates.wait_for_facult, message.chat.id)
    await process_facult(userID=message.from_user.id, chatID=message.chat.id)
@bot.callback_query_handler(func=lambda call: 'change page' in call.data)
async def change_facult_page(call):
    await bot.answer_callback_query(call.id)
    new_page = call.data.strip().split()[-1]
    new_page = int(new_page)
    if new_page <= 0:
        new_page = 1
    await process_facult(page=new_page, userID=call.from_user.id, chatID=call.message.chat.id, previousMessageID=call.message.message_id)

async def process_facult(page=None, userID=None, chatID=None, previousMessageID=None):
    MAX_ELEMENTS = 6
    database = connectDB()
    facults, cursor = getAll(database=database, table="FACULTS")
    facults_amount = len(facults)
    max_page = facults_amount // MAX_ELEMENTS
    database.close()
    if page is None:
        page = 1
    elif page > max_page:
        page = max_page
    markup = InlineKeyboardMarkup()
    newRow = []
    currentFacult = (page-1)*MAX_ELEMENTS
    for i in range(currentFacult, min(facults_amount, currentFacult+MAX_ELEMENTS)):
        f = getRowNamespaces(cursor=cursor, row=facults[i])
        facultButton = InlineKeyboardButton(text=f.name, callback_data=str(f.rowid))
        newRow.append(facultButton)
        if len(newRow) >= 2:
            markup.row(*newRow)
            newRow=[]
    nextPageButton = InlineKeyboardButton("-->", callback_data=f'change page {page+1}')
    previousPageButton = InlineKeyboardButton("<--", callback_data=f'change page {page-1}')
    markup.row(previousPageButton, nextPageButton)
    if previousMessageID is None:
        await bot.send_message(chatID, f"Выберите факультет {page}", reply_markup=markup)
    else:
        await bot.edit_message_reply_markup(chatID, previousMessageID, reply_markup=markup)
async def accept_registration(userID=None, chatID=None):
    async with bot.retrieve_data(userID, chatID) as data:
        name = data['name']
        surname = data['surname']
        group = data['group']
    buttons = InlineKeyboardMarkup()
    buttons.add(InlineKeyboardButton("Всё правильно", callback_data="registration_accepted"))
    buttons.add(InlineKeyboardButton("Повторить регистрацию", callback_data="register"))
    await bot.send_message(chatID, f"Проверьте правильность данных.\n\nИмя: {name}\nФамилия: {surname}\nГруппа: {group}", reply_markup=buttons)
@bot.callback_query_handler(func=lambda call: call.data == 'registration_accepted')
async def end_registration(call):
    await bot.answer_callback_query(call.id)
    try:
        await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    except Exception:
        pass
    await bot.set_state(call.from_user.id, MenuStates.main_menu, call.message.chat.id)


async def main():
    try:
        logger.info("Starting polling...")
        await bot.infinity_polling()
    finally:
        # гарантированно закрываем сессию aiohttp, чтобы не было "Unclosed client session"
        try:
            if hasattr(bot, "session") and bot.session:
                await bot.session.close()
                logger.debug("bot.session closed")
        except Exception as e:
            logger.exception("End session %s", e)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user (KeyboardInterrupt)")