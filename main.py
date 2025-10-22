
from code.logging import logger
from code.database.Repo.queries import getAll, get, connectDB, insert
from code.database.classes.namespaced import getRowNamespaces
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
from telebot.asyncio_handler_backends import State, StatesGroup
from telebot.states.asyncio.middleware import StateMiddleware



TOKEN = "8041847694:AAHusDqbEiIbJwvJ_cJi0bUplRuZxSjKgZ0"
bot = AsyncTeleBot(TOKEN, state_storage=StateMemoryStorage())
# обязательно подключить middleware для состояний
bot.setup_middleware(StateMiddleware(bot))

class RegStates(StatesGroup):
    name = State()
    surname = State()
    age = State()

@bot.message_handler(commands=['sign_up'])
async def cmd_register(message):
    # ставим состояние — бот ожидает имя
    await bot.set_state(message.from_user.id, RegStates.name, message.chat.id)
    await bot.send_message(message.chat.id, "Как Вас зовут? (имя)")

@bot.message_handler(state=RegStates.name, content_types=['text'])
async def process_name(message):
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['name'] = message.text
    await bot.set_state(message.from_user.id, RegStates.surname, message.chat.id)
    await bot.send_message(message.chat.id, "А фамилия?")

@bot.message_handler(state=RegStates.surname, content_types=['text'])
async def process_surname(message):
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['surname'] = message.text
    await bot.set_state(message.from_user.id, RegStates.age, message.chat.id)
    await bot.send_message(message.chat.id, "Из какой вы группы?")

@bot.message_handler(state=RegStates.age, content_types=['text'])
async def process_age(message):
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['age'] = message.text
        await bot.send_message(
            message.chat.id,
            f"Регистрация завершена: {data['name']} {data['surname']}, {data['age']}"
        )
    # очищаем состояние
    await bot.delete_state(message.from_user.id, message.chat.id)
bot.polling(none_stop=True)