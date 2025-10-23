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

# Обрабатывает кнопки, в случаях, если они ничего не должны делать
@bot.callback_query_handler(func=lambda call: 'empty' in call.data)
async def callback_start_register(call):
    data = call.data.split()
    if len(data) == 1:
        await bot.answer_callback_query(call.id)
    else:
        message = ' '.join(data[1:])
        await bot.answer_callback_query(call.id, text=message, show_alert=False)
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
    await choose_direction(userID=message.from_user.id, chatID=message.chat.id)
@bot.callback_query_handler(func=lambda call: 'page' in call.data)
async def process_change_page_call(call):
    await bot.answer_callback_query(call.id)
    async with bot.retrieve_data(call.message.chat.id) as data:
        n = call.message.message_id
        print(n)
        data['previous_message_id'] = n
        if 'next' in call.data:
            data['page'] += 1
        else:
            data['page'] -= 1
    await choose_direction(userID=call.from_user.id, chatID=call.message.chat.id)
async def choose_direction(userID=None, chatID=None, previousMessageID=None):
    # Получаем из даты информацию о текущей странице и таблице
    async with bot.retrieve_data(userID, chatID) as data:
        # Пробуем получить информации из data. Если её нет - записываем дефолтную
        try:
            previousMessageID=data['previous_message_id']
        except:
            previousMessageID=None
        try:
            page = data['page']
        except:
            data['page'] = 1
            page = 1
        try:
            table = data['table']
        except:
            data['table'] = 'FACULTS'
            table = 'FACULTS'
        try:
            filters = data['filters']
        except:
            data['filters'] = {}
            filters = {}

    # Получаем список из таблицы
    database = connectDB()
    all_list, cursor = getAll(database=database, table=table, filters=filters)
    database.close()

    MAX_ELEMENTS_PER_PAGE = 3
    ELEMENTS_PER_ROW = 2
    max_page = len(all_list) // MAX_ELEMENTS_PER_PAGE
    if page > max_page:
        page = max_page
    current_index = (page-1)*MAX_ELEMENTS_PER_PAGE
    max_index = min(len(all_list), current_index + MAX_ELEMENTS_PER_PAGE)
    new_row = []

    markup = InlineKeyboardMarkup()
    for ind in range(current_index, max_index):
        row = all_list[ind]
        ns = getRowNamespaces(row=row, cursor=cursor)
        button = InlineKeyboardButton(ns.name, callback_data="next step {ns.rowid}")
        new_row.append(button)
        if len(new_row) >= ELEMENTS_PER_ROW:
            markup.row(*new_row)
            new_row = []
    next_page_button = InlineKeyboardButton("--->", callback_data='empty' if page == max_page else 'next page')
    previous_page_button = InlineKeyboardButton("<---", callback_data='empty' if page == 1 else 'previous page')
    question_button = InlineKeyboardButton("Не могу найти", callback_data='message moderator')
    markup.row(previous_page_button, question_button, next_page_button)
    table_text = ''
    match table:
        case 'FACULTS':
            table_text = 'факультет'
        case 'CHAIRS':
            table_text = 'кафедру'
        case 'DIRECTIONS':
            table_text = 'направление'
    message_text = f"🔎 Выберите {table_text}\nСтр. {page} из {max_page}"
    if previousMessageID is None:
        await bot.send_message(chatID, message_text, reply_markup=markup)
    else:
        await bot.edit_message_text(message_text, chatID, previousMessageID)
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