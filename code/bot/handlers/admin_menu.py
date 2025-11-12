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
from code.bot.utils import send_temporary_message, safe_edit_message
from collections import defaultdict
import asyncio
from enum import Enum

# ===================================
async def select_from_database(user_id=None, chat_id=None, table=None, filters: dict = {}, header='Выберите'):
	if None in (user_id, chat_id, table):
		logger.error("Incorrect data")
		return None
	async with connect_db() as db:
		rows = await get_all(database=db, table=table, filters=filters)
	return await request_list(
		user_id=user_id,
		chat_id=chat_id,
		header=header,
		items_list=rows,
		input_field='name',
		output_field='rowid'
	)

@bot.callback_query_handler(func=lambda call: call.data == 'show_database')
async def call_print_subdivisions(call):
	try:
		await bot.answer_callback_query(call.id)
	except:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))
	await print_subdivisions(call.message.chat.id)
	return
async def print_subdivisions(chat_id):
	facults, chairs, directions, chairs_by_facults, directions_by_chairs = await group_subdivision()
	message = ''
	for facult in facults.values():
		message += '\n' + facult['name'] + '\n'
		facult_rowid = int(facult['rowid'])
		for chair_id in chairs_by_facults[facult_rowid]:
			chair = chairs[chair_id]
			message += '| ' + chair['name'] + '\n'
			chair_rowid = int(chair['rowid'])
			for direction_id in directions_by_chairs[chair_rowid]:
				direction = directions[direction_id]
				message += '| | ' + direction['name'] + '\n'

	back_button = InlineKeyboardButton('<-- Назад', callback_data='delete')
	markup = InlineKeyboardMarkup()
	markup.add(back_button)
	await bot.send_message(chat_id, message, reply_markup=markup)
	return

async def group_subdivision_by_rowid():
	async with connect_db() as db:
		facults, chairs, directions = await asyncio.gather(
			get_all(database=db, table='FACULTS'),
			get_all(database=db, table='CHAIRS'),
			get_all(database=db, table='DIRECTIONS')
		)
	facults_by_rowid = {}
	for facult in facults:
		rowid = int(facult['rowid'])
		facults_by_rowid[rowid] = facult
	facults_by_rowid = dict(sorted(facults_by_rowid.items()))

	chairs_by_rowid = {}
	for chair in chairs:
		rowid = int(chair['rowid'])
		chairs_by_rowid[rowid] = chair
	chairs_by_rowid = dict(sorted(chairs_by_rowid.items()))

	directions_by_rowid = {}
	for direction in directions:
		rowid = int(direction['rowid'])
		directions_by_rowid[rowid] = direction
	directions_by_rowid = dict(sorted(directions_by_rowid.items()))
	return facults_by_rowid, chairs_by_rowid, directions_by_rowid
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
		chairs_by_facults[facult_id].append(int(chair['rowid']))

	directions_by_chairs = defaultdict(list)
	for direction in directions:
		chair_id = direction['chair_id']
		directions_by_chairs[chair_id].append(int(direction['rowid']))

	facults_by_rowid, chairs_by_rowid, directions_by_rowid = await group_subdivision_by_rowid()
	return facults_by_rowid, chairs_by_rowid, directions_by_rowid, chairs_by_facults, directions_by_chairs
# ================================

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_menu')
async def call_back_to_menu(call):
	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))
	await main_menu(
		call.from_user.id,
		call.message.chat.id,
		call.message.id
	)
@bot.callback_query_handler(func=lambda call: call.data == 'admin_menu')
async def call_admin_menu(call):
	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))

	await admin_menu(call.message.id, call.from_user.id, call.message.chat.id)

@bot.message_handler(commands=['admin_menu'])
async def command_admin_menu(message):
	await admin_menu(user_id=message.from_user.id, chat_id=message.chat.id)
async def admin_menu(previous_message_id=None, user_id=None, chat_id=None):
	if None in (user_id, chat_id):
		logger.error("user_id and chat_id was not provided")
		return
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
	show_database_button = InlineKeyboardButton('Показать факультеты/кафедры/направления', callback_data='show_database')
	back_to_menu_button = InlineKeyboardButton('Назад в меню', callback_data='back_to_menu')
	markup.row(change_database_button, show_database_button)
	markup.row(back_to_menu_button)

	await safe_edit_message(previous_message_id, chat_id, user_id, 'Админ панель', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'change_database')
async def call_change_database_menu(call):
	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))
	await change_database_menu(
		previous_message_id = call.message.id,
		user_id=call.from_user.id,
		chat_id=call.message.chat.id
	)
async def change_database_menu(previous_message_id, user_id, chat_id):
	# TODO добавить:
	# - Добавление предмета с последующей привязкой к направлениям
	# - Добавление кафедр и направлений
	markup = InlineKeyboardMarkup()
	back_button = InlineKeyboardButton('Назад', callback_data='admin_menu')
	add_facult_button = InlineKeyboardButton('Добавить факультет', callback_data='add_facult')
	add_chair_button = InlineKeyboardButton('Добавить кафедру', callback_data='add_chair')
	markup.row(add_facult_button, add_chair_button)
	markup.row(back_button)
	await safe_edit_message(previous_message_id, chat_id, user_id, 'Выберите действие', reply_markup=markup)


class AddingRowResult(Enum):
	INCORRECT_INPUT_DATA = 0
	ROW_ALREADY_EXISTS = 1
	ABORTED_BY_USER = 2
	SUCCESS = 3
async def add_row(user_id, chat_id, accept_message='Подтвердите добавление',
                  table=None,
                  values: list =None,
                  columns: list=None
                  ):
	if None in (table, values, columns):
		logger.error('Incorrect input data: table=%s, values=%s, columns=%s', type(table), type(values), type(columns))
		return AddingRowResult.INCORRECT_INPUT_DATA
	if len(values) != len(columns):
		logger.error('Incorrect input data: the lengths of values and columns are not equal (%s and %s)', len(values), len(columns))
		return AddingRowResult.INCORRECT_INPUT_DATA

	filters = {}
	for i in range(0, len(columns)):
		filters[columns[i]] = i

	async with connect_db() as db:
		is_already_exists = await is_exists(database=db, table=table, filters=filters)
		if is_already_exists:
			return AddingRowResult.ROW_ALREADY_EXISTS

		insert_new_row_accept = await request_confirmation(user_id, chat_id, accept_message)
		if insert_new_row_accept:
			await insert(database=db, table=table, values = values, columns = columns)
		else:
			return AddingRowResult.ABORTED_BY_USER
	return AddingRowResult.SUCCESS


@bot.callback_query_handler(func=lambda call: call.data == 'add_facult')
async def call_add_facult(call):
	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))
	await add_facult(call.from_user.id, call.message.chat.id)
async def add_facult(user_id, chat_id):
	new_facult_name = await request(user_id, chat_id, request_message='Введите название факультета')
	result = await add_row(
		user_id,
		chat_id,
		f'Подтвердите добавление факультета "{new_facult_name}"',
		table='FACULTS',
		values=[new_facult_name],
		columns=['name',]
	)
	match result:
		case AddingRowResult.INCORRECT_INPUT_DATA:
			await send_temporary_message(chat_id, 'Неправильные вводные данные (см. логи)')
		case AddingRowResult.ROW_ALREADY_EXISTS:
			await send_temporary_message(chat_id, 'Такой факультет уже существует')
		case AddingRowResult.ABORTED_BY_USER:
			await send_temporary_message(chat_id, 'Отменяю...')
		case AddingRowResult.SUCCESS:
			await send_temporary_message(chat_id, f'Успешно добавлен факультет {new_facult_name}')
	return

@bot.callback_query_handler(func=lambda call: call.data == 'add_chair')
async def call_add_chair(call):
	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))
	await add_chair(call.from_user.id, call.message.chat.id)
async def add_chair(user_id, chat_id):
	facult_id = await select_from_database(
		user_id,
		chat_id,
		'FACULTS',
		header='Выберите факультет'
	)
	# Админ отменил добавление
	if facult_id is None:
		return
	new_chair_name = await request(user_id, chat_id, request_message='Введите название кафедры')

	result = await add_row(
		user_id,
		chat_id,
		f'Подтвердите добавление факультета "{new_chair_name}"',
		table='CHAIRS',
		values=[new_chair_name, facult_id],
		columns=['name', 'facult_id']
	)

	match result:
		case AddingRowResult.INCORRECT_INPUT_DATA:
			await send_temporary_message(chat_id, 'Неправильные вводные данные (см. логи)')
		case AddingRowResult.ROW_ALREADY_EXISTS:
			await send_temporary_message(chat_id, 'Такая кафедра уже существует')
		case AddingRowResult.ABORTED_BY_USER:
			await send_temporary_message(chat_id, 'Отменяю...')
		case AddingRowResult.SUCCESS:
			await send_temporary_message(chat_id, f'Успешно добавлена кафедра {new_chair_name}')
	return


