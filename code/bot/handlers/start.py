"""
Обработка команды start и menu
Проверка регистрации пользователя
"""

import asyncio

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from code.bot.bot_instance import bot
from code.bot.handlers.main_menu import main_menu
from code.bot.services.user_service import is_user_exists
from code.bot.states import MenuStates, MainStates
from code.bot.utils import delete_message_after_delay
from code.logging import logger


# Обрабатываем команду /start
@bot.message_handler(commands=['start', 'menu'])
async def start(message):
	asyncio.create_task(delete_message_after_delay(bot, message.chat.id, message.message_id, delay_seconds=2))
	logger.info('The /start command has been invoked.')
	# Проверяем, существует ли пользователь
	logger.debug('Check if user exists')

	# Если не существует, предлагаем пройти регистрацию
	user_id = message.from_user.id
	if not await is_user_exists(user_id):
		logger.info(f'The user ({user_id}) does not exist')
		text = 'Похоже, что вы не зарегистрированы. Если хотите пройти регистрацию вызовите команду /register или нажмите на кнопку ниже'
		kb = InlineKeyboardMarkup()
		kb.add(InlineKeyboardButton("Зарегистрироваться", callback_data="register"))
		await bot.reply_to(message, text, reply_markup=kb)
	else:
		logger.info(f'The user ({user_id}) exists')
		await bot.set_state(user_id=user_id, chat_id=message.chat.id, state=MainStates.default_state)
		await main_menu(user_id=message.from_user.id, chat_id=message.chat.id)
