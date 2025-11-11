from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from code.bot.bot_instance import bot
from code.bot.services.requests import request, request_list, request_confirmation
from code.database.service import connect_db
from code.logging import logger
from code.bot.states import MainStates
from code.bot.services.user_service import get_user_info
from code.database.service import connect_db
from code.database.queries import get, is_exists, insert, get_all
from code.utils import getkey
from code.bot.handlers.main_menu import main_menu
from code.bot.utils import send_temporary_message
from collections import defaultdict
import asyncio

# ===================================

async def select_facult(user_id, chat_id):
	async with connect_db() as db:
		facults = await get_all(database=db, table='FACULTS')

	facult_choice = await request_list(
		user_id=user_id,
		chat_id=chat_id,
		header='Выберите факультет',
		items_list=facults,
		input_field='name',
		output_field='rowid'
	)
	return facult_choice
async def select_chair(user_id, chat_id, facult_id):
	async with connect_db() as db:
		chairs = await get_all(database=db, table='CHAIRS', filters={'facult_id': facult_id})

	chair_choice = await request_list(
		user_id=user_id,
		chat_id=chat_id,
		header='Выберите кафедру',
		items_list=chairs,
		input_field='name',
		output_field='rowid'
	)
	return chair_choice
async def print_subdivisions(user_id, chat_id):
	facults, chairs, directions, chairs_by_facults, directions_by_chairs = group_subdivision()
	message = ''
	# TODO доделать

async def group_subdivision():
	async with connect_db() as db:
		facults, chairs, directions = await asyncio.gather(
			get_all(database=db, table='FACULTS'),
			get_all(database=db, table='CHAIRS'),
			get_all(database=db, table='DIRECTIONS')
		)

	chairs_by_facults = defaultdict(list)
	for chair in chairs:
		facult_id = chair['facult_id']
		chairs_by_facults[facult_id].append(chair['rowid'])

	directions_by_chairs = defaultdict(list)
	for direction in directions:
		chair_id = direction['chair_id']
		directions_by_chairs[chair_id].append(direction['rowid'])
	return facults, chairs, directions, chairs_by_facults, directions_by_chairs
# ================================

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
	add_chair_button = InlineKeyboardButton('Добавить кафедру', callback_data='add_chair')
	markup.row(add_facult_button, add_chair_button)
	await bot.send_message(chat_id, 'Выберите действие', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'add_facult')
async def call_add_facult(call):
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
			await send_temporary_message(bot, chat_id, 'Факультет с данным именем уже существует.', delay_seconds=10)
			return
		insert_new_row = await request_confirmation(user_id, chat_id, f'Добавить факультет "{new_facult_name}"?')
		if insert_new_row:
			await insert(database=db, table='FACULTS', values=[new_facult_name], columns=['name'])
		else:
			await send_temporary_message(bot, chat_id, 'Отменяю')
	return

@bot.callback_query_handler(func=lambda call: call.data == 'add_chair')
async def call_add_chair(call):
	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))
	await add_chair(call.from_user.id, call.message.chat.id)
async def add_chair(user_id, chat_id):
	facult_id = await select_facult(user_id, chat_id)
	# Админ отменил добавления
	if facult_id is None:
		return

	new_chair_name = await request(user_id, chat_id, request_message='Введите название кафедры')

	async with connect_db() as db:
		# Проверяем, есть ли эта кафедра в
		is_already_exists = await is_exists(database=db, table='CHAIRS', filters={'name': new_chair_name})
		if is_already_exists:
			await send_temporary_message(bot, chat_id, 'Кафедра с таким именем уже существует.')
			return
		# Запрашиваем ещё одно подтверждение у админа
		insert_new_row = await request_confirmation(user_id, chat_id, f'Добавить кафедру "{new_chair_name}"?')
		if insert_new_row:
			await insert(database=db, table='CHAIRS', values=[new_chair_name, facult_id], columns=['name', 'facult_id'])
		else:
			await send_temporary_message(bot, chat_id, 'Отменяю')
