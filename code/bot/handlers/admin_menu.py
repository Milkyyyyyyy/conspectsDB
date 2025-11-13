from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from code.bot.bot_instance import bot
from code.bot.services.requests import request, request_list, request_confirmation
from code.database.service import connect_db
from code.logging import logger
from code.bot.states import MainStates
from code.bot.services.user_service import get_user_info
from code.database.service import connect_db
from code.database.queries import get, is_exists, insert, get_all, remove, remove_all
from code.utils import getkey
from code.bot.handlers.main_menu import main_menu
from code.bot.utils import send_temporary_message, safe_edit_message, delete_message_after_delay
from collections import defaultdict
import asyncio
from enum import Enum
from code.bot.callbacks import call_factory
from typing import Union, List

# ===================================
async def select_from_database(
		user_id=None,
		chat_id=None,
		table=None,
		filters: dict = {},
		header='Выберите',
		input_field: Union[str, List[str]] = 'name',
		output_field: Union[str, List[str]] ='rowid',
):
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
		input_field=input_field,
		output_field=output_field,
	)

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

	back_button = InlineKeyboardButton(
		'<-- Назад',
		callback_data=call_factory.new(
			area='',
			action='delete'
		)
	)
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

@bot.callback_query_handler(func=call_factory.filter(area='admin_menu').check)
async def callback_handler(call):
	logger.debug('Handle callback in admin menu...')
	user_id = call.from_user.id
	chat_id = call.message.chat.id
	message_id = call.message.id
	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))
	action = call_factory.parse(callback_data=call.data)['action']
	match action:
		case 'back_to_menu':
			await main_menu(
				user_id=user_id,
				chat_id=chat_id,
				previous_message_id=message_id
			)
			return
		case 'admin_menu':
			await admin_menu(message_id, user_id, chat_id)
		case 'change_database':
			await change_database_menu(
				previous_message_id=message_id,
				user_id=user_id,
				chat_id=chat_id
			)
		case 'add_facult':
			await add_facult(
				user_id=user_id,
				chat_id=chat_id,
				previous_message_id=message_id,
			)
		case 'add_chair':
			await add_chair(
				user_id=user_id,
				chat_id=chat_id,
				previous_message_id=message_id
			)
		case 'add_direction':
			await add_direction(
				user_id=user_id,
				chat_id=chat_id,
				previous_message_id=message_id
			)
		case 'delete_facult':
			await delete_facult(
				user_id=user_id,
				chat_id=chat_id,
				previous_message_id=message_id
			)
		case 'delete_chair':
			await delete_chair(
				user_id=user_id,
				chat_id=chat_id,
				previous_message_id=message_id
			)
		case 'delete_direction':
			await delete_direction(
				user_id=user_id,
				chat_id=chat_id,
				previous_message_id=message_id
			)
		case 'show_database':
			await print_subdivisions(chat_id)




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

	change_database_button = InlineKeyboardButton(
		'Изменить датабазу',
		callback_data=call_factory.new(
			area='admin_menu',
			action='change_database'
		)
	)
	show_database_button = InlineKeyboardButton(
		'Показать факультеты/кафедры/направления',
		callback_data=call_factory.new(
			area='admin_menu',
			action='show_database'
		)
	)
	back_to_menu_button = InlineKeyboardButton(
		'Назад в меню',
		callback_data=call_factory.new(
			area='admin_menu',
			action='back_to_menu'
		)
	)

	markup.row(change_database_button, show_database_button)
	markup.row(back_to_menu_button)

	await safe_edit_message(previous_message_id, chat_id, user_id, 'Админ панель', reply_markup=markup)

async def change_database_menu(previous_message_id, user_id, chat_id):
	markup = InlineKeyboardMarkup()
	back_button = InlineKeyboardButton(
		'Назад',
		callback_data=call_factory.new(
			area='admin_menu',
			action='admin_menu'
		)
	)
	add_facult_button = InlineKeyboardButton(
		'Добавить факультет',
		callback_data=call_factory.new(
			area='admin_menu',
			action = 'add_facult'
		)
	)
	add_chair_button = InlineKeyboardButton(
		'Добавить кафедру',
		callback_data = call_factory.new(
			area='admin_menu',
			action='add_chair'
		)
	)
	add_direction_button = InlineKeyboardButton(
		'Добавить направление',
		callback_data=call_factory.new(
			area='admin_menu',
			action='add_direction'
		)
	)

	delete_facult_button = InlineKeyboardButton(
		'Удалить факультет',
		callback_data=call_factory.new(
			area='admin_menu',
			action='delete_facult'
		)
	)
	delete_chair_button = InlineKeyboardButton(
		'Удалить кафедру',
		callback_data=call_factory.new(
			area='admin_menu',
			action='delete_chair'
		)
	)
	delete_direction_button = InlineKeyboardButton(
		'Удалить направление',
		callback_data=call_factory.new(
			area='admin_menu',
			action='delete_direction'
		)
	)
	markup.row(add_facult_button, add_chair_button)
	markup.row(add_direction_button)
	markup.row(delete_facult_button, delete_chair_button)
	markup.row(delete_direction_button)
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
                  columns: list=None,
                  previous_message_id=None,
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

		insert_new_row_accept = await request_confirmation(user_id, chat_id, accept_message, previous_message_id=previous_message_id)
		if insert_new_row_accept:
			await insert(database=db, table=table, values = values, columns = columns)
		else:
			return AddingRowResult.ABORTED_BY_USER
	return AddingRowResult.SUCCESS


async def add_facult(user_id, chat_id, previous_message_id):
	new_facult_name = await request(
		user_id,
		chat_id,
		request_message='Введите название факультета',
	)
	result = await add_row(
		user_id,
		chat_id,
		f'Подтвердите добавление факультета "{new_facult_name}"',
		table='FACULTS',
		values=[new_facult_name],
		columns=['name',],
		previous_message_id=previous_message_id
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
	await admin_menu(user_id=user_id, chat_id=chat_id, previous_message_id=previous_message_id)

async def add_chair(user_id, chat_id, previous_message_id):
	facult_id = await select_from_database(
		user_id,
		chat_id,
		'FACULTS',
		header='Выберите факультет',
	)
	# Админ отменил добавление
	if facult_id is None:
		await admin_menu(user_id=user_id, chat_id=chat_id, previous_message_id=previous_message_id)
		return
	new_chair_name = await request(
		user_id,
		chat_id,
		request_message='Введите название кафедры',
		delete_request_message=True
	)

	result = await add_row(
		user_id,
		chat_id,
		f'Подтвердите добавление кафедры "{new_chair_name}"',
		table='CHAIRS',
		values=[new_chair_name, facult_id],
		columns=['name', 'facult_id'],
		previous_message_id=previous_message_id
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
	await admin_menu(user_id=user_id, chat_id=chat_id, previous_message_id=previous_message_id)

async def add_direction(user_id, chat_id, previous_message_id):
	facult_id = await select_from_database(
		user_id,
		chat_id,
		'FACULTS',
		header='Выберите факультет',
	)
	# Админ отменил добавление
	if facult_id is None:
		await admin_menu(user_id=user_id, chat_id=chat_id, previous_message_id=previous_message_id)
		return

	chair_id = await select_from_database(
		user_id,
		chat_id,
		'CHAIRS',
		header='Выберите факультет',
		filters={'facult_id': facult_id}
	)
	# Админ отменил добавление
	if chair_id is None:
		await admin_menu(user_id=user_id, chat_id=chat_id, previous_message_id=previous_message_id)
		return

	new_direction_name = await request(
		user_id,
		chat_id,
		request_message='Введите название направления',
		delete_request_message=True
	)
	result = await add_row(
		user_id,
		chat_id,
		f'Подтвердите добавление направления "{new_direction_name}"',
		table='DIRECTIONS',
		values=[new_direction_name, chair_id],
		columns=['name', 'chair_id'],
		previous_message_id=previous_message_id
	)
	match result:
		case AddingRowResult.INCORRECT_INPUT_DATA:
			await send_temporary_message(chat_id, 'Неправильные вводные данные (см. логи)')
		case AddingRowResult.ROW_ALREADY_EXISTS:
			await send_temporary_message(chat_id, 'Такое направление уже существует')
		case AddingRowResult.ABORTED_BY_USER:
			await send_temporary_message(chat_id, 'Отменяю...')
		case AddingRowResult.SUCCESS:
			await send_temporary_message(chat_id, f'Успешно добавлено направление {new_direction_name}')
	await admin_menu(user_id=user_id, chat_id=chat_id, previous_message_id=previous_message_id)

# TODO
# async def add_subject
# async def connect_subject_to_direction (мб другое название)
# После этого в принципе можно делать мердж в develop, а затем и в мэйн

async def delete_facult(user_id, chat_id, previous_message_id):
	selected_facult = await select_from_database(
		user_id,
		chat_id,
		'FACULTS',
		header='Выберите факультет',
		output_field=['rowid', 'name']
	)
	confirm = await request_confirmation(
		user_id,
		chat_id,
		text=f'Подтвердите удаление факультета "{selected_facult[1]}"',
		previous_message_id=previous_message_id
	)
	if confirm:
		try:
			async with connect_db() as db:
				await remove(
					database=db,
					table='FACULTS',
					filters={'rowid': selected_facult[0]}
				)
				# Получаем все кафедры этого факультета
				chairs = await get_all(
					database=db,
					table='CHAIRS',
					filters={'facult_id': selected_facult[0]}
				)
		except Exception as e:
			logger.exception(f"Can't delete facult: {e}")
			await admin_menu(user_id=user_id, chat_id=chat_id, previous_message_id=previous_message_id)
			return
		confirm_sub_deletion = await request_confirmation(
			user_id,
			chat_id,
			text=f'Удалить все кафедры/направления, связанные с этим факультетом?\n'
				 f'Крайне рекомендуется\n'
				 f'Найдено <b>{len(chairs)}</b> кафедр',
			previous_message_id=previous_message_id
		)
		if confirm_sub_deletion:
			last_message = await bot.send_message(
				chat_id=chat_id,
				text='Удаляю...'
			)
			last_message_id=last_message.id
			# Для каждой кафедры удаляем все направления
			async with connect_db() as db:
				for chair in chairs:
					chair_id = chair.row_id
					await remove_all(
						database=db,
						table='DIRECTIONS',
						filters={'char_id': chair_id}
					)
				# Удаляем все кафедры
				await remove_all(
					database=db,
					table='DIRECTIONS',
					filters={'facult_id': selected_facult[0]}
				)
				last_message_id = await safe_edit_message(
					chat_id=chat_id,
					user_id=user_id,
					previous_message_id=last_message_id,
					text='Готово!'
				)
				await delete_message_after_delay(
					chat_id,
					last_message_id,
					delay_seconds=1
				)
	await admin_menu(
		user_id=user_id,
		chat_id=chat_id,
		previous_message_id=previous_message_id
	)
	return

async def delete_chair(user_id, chat_id, previous_message_id):
	selected_facult = await select_from_database(
		user_id,
		chat_id,
		'FACULTS',
		header='Выберите факультет',
		output_field='rowid'
	)
	selected_chair = await select_from_database(
		user_id,
		chat_id,
		'CHAIRS',
		{'facult_id': selected_facult},
		header='Выберите кафедру',
		output_field=['rowid', 'name']
	)
	confirm = await request_confirmation(
		user_id,
		chat_id,
		text=f'Подтвердите удаление кафедры "{selected_chair[1]}"',
		previous_message_id=previous_message_id
	)
	if confirm:
		try:
			async with connect_db() as db:
				await remove(
					database=db,
					table='CHAIRS',
					filters={'rowid': selected_chair[0]}
				)
				# Получаем все кафедры этого факультета
				directions = await get_all(
					database=db,
					table='DIRECTIONS',
					filters={'chair_id': selected_chair[0]}
				)
		except Exception as e:
			logger.exception(f"Can't delete chair: {e}")
			await admin_menu(user_id=user_id, chat_id=chat_id, previous_message_id=previous_message_id)
			return
		confirm_sub_deletion = await request_confirmation(
			user_id,
			chat_id,
			text=f'Удалить все направления, связанные с этой кафедрой?\n'
				 f'Крайне рекомендуется\n'
				 f'Найдено <b>{len(directions)}</b> направлений',
			previous_message_id=previous_message_id
		)
		if confirm_sub_deletion:
			last_message = await bot.send_message(
				chat_id=chat_id,
				text='Удаляю...'
			)
			last_message_id = last_message.id
			# Для каждой кафедры удаляем все направления
			async with connect_db() as db:
				# Удаляем все направления
				await remove_all(
					database=db,
					table='DIRECTIONS',
					filters={'chair_id': selected_chair[0]}
				)
			last_message_id = await safe_edit_message(
				chat_id=chat_id,
				user_id=user_id,
				previous_message_id=last_message_id,
				text='Готово!'
			)
			await delete_message_after_delay(
				chat_id,
				last_message_id,
				delay_seconds=1
			)
	await admin_menu(
		user_id=user_id,
		chat_id=chat_id,
		previous_message_id=previous_message_id
	)
	return

async def delete_direction(user_id, chat_id, previous_message_id):
	selected_facult = await select_from_database(
		user_id,
		chat_id,
		'FACULTS',
		header='Выберите факультет',
		output_field='rowid'
	)
	selected_chair = await select_from_database(
		user_id,
		chat_id,
		'CHAIRS',
		{'facult_id': selected_facult},
		header='Выберите кафедру',
		output_field='rowid'
	)
	selected_direction = await select_from_database(
		user_id,
		chat_id,
		'DIRECTIONS',
		{'chair_id': selected_chair},
		header='Выберите направление',
		output_field=['rowid', 'name']
	)
	confirm = await request_confirmation(
		user_id,
		chat_id,
		text=f'Подтвердите удаление направления "{selected_direction[1]}"',
		previous_message_id=previous_message_id
	)
	if confirm:
		try:
			async with connect_db() as db:
				await remove(
					database=db,
					table='DIRECTIONS',
					filters={'rowid': selected_direction[0]}
				)
		except Exception as e:
			logger.exception(f"Can't delete direction: {e}")
			await admin_menu(user_id=user_id, chat_id=chat_id, previous_message_id=previous_message_id)
			return
	await admin_menu(
		user_id=user_id,
		chat_id=chat_id,
		previous_message_id=previous_message_id
	)
	return