from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from code.bot.bot_instance import bot
from code.bot.services.requests import request
from code.database.service import connect_db
from code.logging import logger
from code.bot.states import MainStates
from code.bot.services.user_service import get_user_info
from code.database.service import connect_db
from code.database.queries import get, is_exists, insert
from code.utils import getkey
from code.bot.handlers.main_menu import main_menu
from code.bot.utils import send_temporary_message


@bot.callback_query_handler(func=lambda call: call.data == 'admin_menu')
async def call_admin_menu(call):
	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))

	await admin_menu(call.from_user.id, call.message.chat.id)
@bot.message_handler(commands=['admin_menu'])
async def command_admin_menu(message):
	await admin_menu(message.from_user.id, message.chat.id)
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
	# - Добавление предмета с последующей привязкой к направлениям
	# - Добавление кафедр и направлений
	markup = InlineKeyboardMarkup()
	add_facult_button = InlineKeyboardButton('Добавить факультет', callback_data='add_facult')
	markup.row(add_facult_button)
	await bot.send_message(chat_id, 'Выберите действие', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'add_facult')
async def call_add_facult_menu(call):
	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))
	await add_facult(call.from_user.id, call.message.chat.id)
async def add_facult(user_id, chat_id):
	new_facult_name = await request(user_id, chat_id, request_message='Введите название факультета')
	async with connect_db() as db:
		is_already_exists = await is_exists(database=db, table='FACULTS', filters={'name': new_facult_name})
		if is_already_exists:
			await send_temporary_message(bot, chat_id, 'Факультет уже существует.', delay_seconds=10)
		else:
			await insert(database=db, table='FACULTS', values=[new_facult_name], columns=['name'])
			logger.info('Pinging database row with name=%s', new_facult_name)
			if await is_exists(database=db, table='facults', filters={'name': new_facult_name}):
				await send_temporary_message(bot, chat_id, f'Успешно добавлен факультет <b>"{new_facult_name}"</b>')
			else:
				await send_temporary_message(bot, chat_id, 'Не удалось добавить факультет...')
	return


