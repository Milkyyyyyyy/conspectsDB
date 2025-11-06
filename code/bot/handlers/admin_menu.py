from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from code.bot.bot_instance import bot
from code.database.service import connect_db
from code.logging import logger
from code.bot.states import MainStates
from code.bot.services.user_service import get_user_info
from code.database.service import connect_db
from code.database.queries import get
from code.utils import getkey
from code.bot.handlers.main_menu import main_menu


@bot.callback_query_handler(func=lambda call: call.data == 'admin_menu')
async def call_admin_menu(call):
	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))

	await admin_menu(call.from_user.id, call.message.chat.id)

async def admin_menu(user_id, chat_id):
	if await bot.get_state(user_id, chat_id) != MainStates.admin_menu_state.name:
		await bot.set_state(user_id, chat_id, MainStates.admin_menu_state)

	# Проверяем, является ли юзер админом
	async with bot.retrieve_data(user_id, chat_id) as data:
		is_moderator = await getkey(data, 'is_moderator', None)
		if is_moderator is None:
			async with connect_db() as db:
				user_row = await get(database=db, table='USERS', filters={'telegram_id': user_id})
				is_moderator = user_row['role'] in ('moderator', 'admin')
				data['is_moderator'] = is_moderator
		is_moderator = bool(is_moderator)

	if not is_moderator:
		await main_menu(user_id, chat_id)
		return

	markup = InlineKeyboardMarkup()

	change_database_button = InlineKeyboardButton('Изменить датабазу', callback_data='change_database')
	markup.row(change_database_button)
	await bot.send_message(chat_id, 'Админ панель', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'change_database')
async def call_change_database_menu(call):
	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))
	await change_database_menu(call.from_user.id, call.message.chat.id)
async def change_database_menu(user_id, chat_id):
	# TODO добавить:
	# - Добавление факультетов, кафедр и направлений
	# - Добавление предмета с последующей привязкой к направлениям
	pass