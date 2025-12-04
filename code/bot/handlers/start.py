"""
Обработка команды start и menu
Проверка регистрации пользователя
"""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from code.bot.bot_instance import bot
from code.bot.callbacks import call_factory
from code.bot.handlers.main_menu import main_menu
from code.bot.services.user_service import is_user_exists, ensure_user_registered
from code.bot.states import MainStates
from code.bot.utils import delete_message_after_delay, send_message_after
from code.logging import logger
import random


# Обрабатываем команду /start
@bot.message_handler(commands=['start', 'menu'])
async def start(message):
	await delete_message_after_delay(message.chat.id, message.message_id, delay_seconds=5)
	user_id = message.from_user.id
	logger.info('The /start command has been invoked by user %s.', user_id)
	# Проверяем, существует ли пользователь
	logger.debug('Check if user %s exists', user_id)

	# Если не существует, предлагаем пройти регистрацию
	exists = await ensure_user_registered(user_id, chat_id=message.chat.id)

	if exists:
		logger.info(f'The user ({user_id}) exists')
		await bot.set_state(user_id=user_id, chat_id=message.chat.id, state=MainStates.default_state)
		await main_menu(user_id=message.from_user.id, chat_id=message.chat.id)

	back_to_menu_markup = ReplyKeyboardMarkup(
		resize_keyboard=True,
		one_time_keyboard=False
	)

	back_to_menu_button = KeyboardButton(
		'Вернуться в меню'
	)
	back_to_menu_markup.add(back_to_menu_button)

	if exists:
		delay_seconds = random.uniform(10, 20)
	else:
		delay_seconds = random.uniform(60, 60*3)
	await send_message_after(
		message.chat.id,
		text='Если кнопки не реагируют\nИспользуйте кнопку под клавиатурой',
		reply_markup=back_to_menu_markup,
		delay_seconds=delay_seconds
	)