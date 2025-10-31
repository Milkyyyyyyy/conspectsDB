"""
Здесь хранить все State юзера
"""
from enum import StrEnum

from telebot.asyncio_handler_backends import State, StatesGroup
from code.logging import logger
from code.bot.bot_instance import bot

class MainStates(StatesGroup):
	default_state = State()
	request_state = State()
# State регистрации
class RegStates(StatesGroup):
	wait_for_name = State()
	wait_for_surname = State()
	wait_for_group = State()
	wait_for_facult = State()
	wait_for_chair = State()
	wait_for_direction = State()
	accept_registration = State()


# State главного меню
class MenuStates(StatesGroup):
	main_menu = State()

async def set_default_state(user_id, chat_id):
	logger.debug('Restoring default state for user=%s chat=%s', user_id, chat_id)
	await bot.set_state(user_id=user_id, chat_id=chat_id, state=MainStates.default_state)
