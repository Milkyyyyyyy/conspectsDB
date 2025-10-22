import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
from telebot.asyncio_handler_backends import State, StatesGroup
from telebot.states.asyncio.middleware import StateMiddleware
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot import asyncio_filters

from code.database.repo.queries import connectDB, isExists



TOKEN = "7428239168:AAHTx5DadgqK4Q7oKmhlBJkwAW9iRYHcaso"
bot = AsyncTeleBot(TOKEN, state_storage=StateMemoryStorage())

bot.add_custom_filter(asyncio_filters.StateFilter(bot))
# обязательно подключить middleware для состояний
bot.setup_middleware(StateMiddleware(bot))

class RegStates(StatesGroup):
    wait_for_name = State()
    wait_for_surname = State()
    wait_for_age = State()

@bot.message_handler(commands=['start'])
async def start(message):
    userID = str(message.from_user.id)
    database = connectDB()
    isUserExists, _ = isExists(database=database, table="USERS", filters={"telegram_id": userID})
    database.close()
    if not isUserExists:
        text = 'Похоже, что вы не зарегистрированы. Если хотите пройти регистрацию вызовите команду `register`'
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("Зарегистрироваться", callback_data="register"))
        await bot.reply_to(message, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == 'register')
async def callback_start_register(call):
    print('button pressed')
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
    await bot.send_message(chatID, "Как Вас зовут? (имя)")

@bot.message_handler(state=RegStates.wait_for_name)
async def process_name(message=None):
    print(message.text)
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['wait_for_name'] = message.text
    print('setting next state')
    await bot.set_state(message.from_user.id, RegStates.wait_for_surname, message.chat.id)
    await bot.send_message(message.chat.id, "А фамилия?")

@bot.message_handler(state=RegStates.wait_for_surname)
async def process_surname(message):
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['wait_for_surname'] = message.text
    await bot.set_state(message.from_user.id, RegStates.wait_for_age, message.chat.id)
    await bot.send_message(message.chat.id, "Из какой вы группы?")

@bot.message_handler(state=RegStates.wait_for_age)
async def process_age(message):
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['wait_for_age'] = message.text
        await bot.send_message(
            message.chat.id,
            f"Регистрация завершена: {data['wait_for_name']} {data['wait_for_surname']}, {data['wait_for_age']}"
        )
    # очищаем состояние
    await bot.delete_state(message.from_user.id, message.chat.id)
asyncio.run(bot.infinity_polling())