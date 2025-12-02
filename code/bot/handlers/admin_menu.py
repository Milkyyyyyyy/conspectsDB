import asyncio
from collections import defaultdict
from enum import Enum
from typing import Union, List

from select import select
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from code.bot.bot_instance import bot
from code.bot.callbacks import call_factory
from code.bot.handlers.main_menu import main_menu
from code.bot.services.requests import request, request_list, request_confirmation, wait_for_callback_on_message
from code.bot.states import MainStates
from code.bot.utils import send_temporary_message, safe_edit_message, delete_message_after_delay
from code.database.queries import get, is_exists, insert, get_all, remove, remove_all, update
from code.database.service import connect_db
from code.database.utils import safe_row_to_dict
from code.logging import logger
from code.utils import getkey
from code.bot.services.conspects import send_conspect_message


@bot.callback_query_handler(func=call_factory.filter(area='admin_menu').check)
async def callback_handler(call):
	"""
	Handler для callback'ов в области admin_menu
	"""
	logger.debug('Handle callback in admin menu...')
	user_id = call.from_user.id
	chat_id = call.message.chat.id
	message_id = call.message.id

	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))

	action = call_factory.parse(callback_data=call.data)['action']
	logger.debug('Callback in admin menu action: %s', action)
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
		case 'add_subject':
			await add_subject(
				user_id=user_id,
				chat_id=chat_id,
				previous_message_id=message_id
			)
		case 'delete_subject':
			await delete_subject(
				user_id=user_id,
				chat_id=chat_id,
				previous_message_id=message_id
			)
		case 'edit_subject_connection':
			await edit_subject_connections(
				user_id=user_id,
				chat_id=chat_id,
				previous_message_id=message_id
			)
		case 'show_database':
			await print_subdivisions(chat_id, previous_message_id=message_id)
		case 'check_conspects':
			await check_conspects(user_id, chat_id)


# ===================================
async def select_from_database(
		user_id=None,
		chat_id=None,
		table=None,
		filters: dict = {},
		header='Выберите',
		input_field: Union[str, List[str]] = 'name',
		output_field: Union[str, List[str]] = 'rowid',
):
	"""
	Небольшая утилита для выбора записей из датабазы

	:param user_id: ID юзера.
	:param chat_id: ID чата.
	:param table: Название таблицы в датабазе.
	:param filters: Фильтры записей датабазы, которые будут даны на выбор.
	:param header: Заголовок, который будет отображаться над списком.
	:param input_field: Поле, которое будет выводиться пользователю.
	:param output_field: Поле (или поля), которые будут возвращены функцией.
	:return: Список значений заданных полей, или просто одно значение
	"""
	if None in (user_id, chat_id, table):
		logger.error("Incorrect data")
		return None

	async with connect_db() as db:
		rows = await get_all(database=db, table=table, filters=filters)

	choice = await request_list(
		user_id=user_id,
		chat_id=chat_id,
		header=header,
		items_list=rows,
		input_field=input_field,
		output_field=output_field,
	)
	return choice


async def print_subdivisions(chat_id, previous_message_id=None):
	"""
	Выводит всю датабазу факультетов, кафедр и направлений в виде схемы

	:param chat_id: ID чата
	"""
	facults, chairs, directions, chairs_by_facults, directions_by_chairs = await _group_subdivision()
	logger.info(f'Printing subdivisions for {chat_id}, facults=%s, chairs=%s, directions=%s', len(facults), len(chairs), len(directions))

	# Выводим схему факультетов, кафедр и направлений
	schema = ''
	for facult in facults.values():
		schema += '\n' + facult['name'] + '\n'
		facult_rowid = int(facult['rowid'])
		for chair_id in chairs_by_facults[facult_rowid]:
			chair = chairs[chair_id]
			schema += '| ' + chair['name'] + '\n'
			chair_rowid = int(chair['rowid'])
			for direction_id in directions_by_chairs[chair_rowid]:
				direction = directions[direction_id]
				schema += '| | ' + direction['name'] + '\n'
	# Собираем markup
	back_button = InlineKeyboardButton(
		'<-- Назад',
		callback_data=call_factory.new(
			area='admin_menu',
			action='admin_menu'
		)
	)
	markup = InlineKeyboardMarkup()
	markup.add(back_button)
	if schema == '':
		schema = 'Не обнаружено факультетов.'
	await safe_edit_message(
		previous_message_id=previous_message_id,
		chat_id=chat_id,
		text=schema,
		reply_markup=markup
	)
	return


async def _group_subdivision_by_rowid():
	"""
	Группирует факультеты, кафедры и направления по rowid

	:return: Кортеж словарей, где ключ - rowid
	"""
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


async def _group_subdivision():
	"""
	Группирует кафедры по факультетам, а направления по кафедрам

	:return: Кортеж словарей из _group_subdivision_by_rowid и словарь группировки кафедр по факультету и направлений по кафедрам
	"""
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

	facults_by_rowid, chairs_by_rowid, directions_by_rowid = await _group_subdivision_by_rowid()
	return facults_by_rowid, chairs_by_rowid, directions_by_rowid, chairs_by_facults, directions_by_chairs


# ================================



@bot.message_handler(commands=['admin_menu'])
async def command_admin_menu(message):
	logger.info('User %s invoked command /admin_menu', message.from_user.id)
	await admin_menu(user_id=message.from_user.id, chat_id=message.chat.id)

async def admin_menu(previous_message_id=None, user_id=None, chat_id=None):
	"""
	Выводит пользователю меню админа

	:param previous_message_id: ID прошлого сообщения.
	:param user_id: ID юзера.
	:param chat_id: ID чата.
	"""
	logger.info('Printing admin menu for %s', user_id)
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
		logger.info("User %s is not moderator or admin, exiting", user_id)
		await main_menu(user_id, chat_id)
		return

	markup = InlineKeyboardMarkup()

	check_conspects_button = InlineKeyboardButton(
		'Проверить новые конспекты',
		callback_data=call_factory.new(
			area='admin_menu',
			action='check_conspects'
		)
	)

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

	markup.row(check_conspects_button)
	markup.row(change_database_button, show_database_button)
	markup.row(back_to_menu_button)

	await safe_edit_message(previous_message_id, chat_id, user_id, 'Админ панель', reply_markup=markup)


async def change_database_menu(previous_message_id, user_id, chat_id):
	"""
	Меню изменения датабазы в админ панели

	:param previous_message_id: ID прошлого сообщения.
	:param user_id: ID юзера.
	:param chat_id: ID чата
	"""
	logger.info('Printing change_database menu for user %s', user_id)
	# Собираем весь markup
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
			action='add_facult'
		)
	)
	add_chair_button = InlineKeyboardButton(
		'Добавить кафедру',
		callback_data=call_factory.new(
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

	add_subject_button = InlineKeyboardButton(
		'Добавить предмет',
		callback_data=call_factory.new(
			area='admin_menu',
			action='add_subject'
		)
	)
	delete_subject_button = InlineKeyboardButton(
		'Удалить предмет',
		callback_data=call_factory.new(
			area='admin_menu',
			action='delete_subject'
		)
	)
	edit_subject_connection_button = InlineKeyboardButton(
		'Добавить направление к предмету',
		callback_data=call_factory.new(
			area='admin_menu',
			action='edit_subject_connection'
		)
	)
	markup.row(add_facult_button, add_chair_button)
	markup.row(add_direction_button)

	markup.row(delete_facult_button, delete_chair_button)
	markup.row(delete_direction_button)

	markup.row(add_subject_button, delete_subject_button)
	markup.row(edit_subject_connection_button)

	markup.row(back_button)
	await safe_edit_message(previous_message_id, chat_id, user_id, 'Выберите действие', reply_markup=markup)


class AddingRowResult(Enum):
	"""
	Enum для утилиты add_row
	"""
	INCORRECT_INPUT_DATA = 0
	ROW_ALREADY_EXISTS = 1
	ABORTED_BY_USER = 2
	SUCCESS = 3


async def add_row(
		user_id, chat_id, accept_message='Подтвердите добавление',
		table=None,
		filters: dict = None,
		previous_message_id=None,
		delete_message_after: bool = False,
):
	"""
	Утилита для добавления записи в датабазу

	:param user_id: ID юзера.
	:param chat_id: ID чата.
	:param accept_message: Сообщение, которое будет выведено пользователю.
	:param table: Название таблицы из датабазы
	:param previous_message_id: ID прошлого сообщения
	:return: AddingRowResult Enum с результатом добавления
	"""
	logger.info('Adding row with filters=%s', filters)
	if None in (table, filters, ):
		logger.error('Incorrect input data: table=%s, filters=', type(table), filters)
		return AddingRowResult.INCORRECT_INPUT_DATA
	async with connect_db() as db:
		is_already_exists = await is_exists(database=db, table=table, filters=filters)
		if is_already_exists:
			return AddingRowResult.ROW_ALREADY_EXISTS

		insert_new_row_accept = await request_confirmation(user_id, chat_id, accept_message,
														   previous_message_id=previous_message_id,
		                                                   delete_message_after=delete_message_after)
		if insert_new_row_accept:
			await insert(database=db, table=table, filters=filters)
		else:
			return AddingRowResult.ABORTED_BY_USER
	return AddingRowResult.SUCCESS


async def add_facult(user_id, chat_id, previous_message_id):
	"""
	Добавление факультета пользователем

	:param user_id: ID юзера.
	:param chat_id: ID
	:param previous_message_id: ID прошлого сообщения
	:return:
	"""
	new_facult_name, message_id = await request(
		user_id,
		chat_id,
		request_message='Введите название факультета',
		previous_message_id=previous_message_id
	)
	previous_message_id = message_id
	result = await add_row(
		user_id,
		chat_id,
		f'Подтвердите добавление факультета "{new_facult_name}"',
		table='FACULTS',
		filters={'name': new_facult_name},
		delete_message_after=True
	)

	match result:
		case AddingRowResult.INCORRECT_INPUT_DATA:
			await send_temporary_message(chat_id, 'Неправильные вводные данные (см. логи)', delay_seconds=2)
		case AddingRowResult.ROW_ALREADY_EXISTS:
			await send_temporary_message(chat_id, 'Такой факультет уже существует', delay_seconds=2)
		case AddingRowResult.ABORTED_BY_USER:
			await send_temporary_message(chat_id, 'Отменяю...', delay_seconds=1)
		case AddingRowResult.SUCCESS:
			await send_temporary_message(chat_id, f'Успешно добавлен факультет <b>"{new_facult_name}"</b>', delay_seconds=10)
	await asyncio.sleep(0.5)
	await admin_menu(user_id=user_id, chat_id=chat_id, previous_message_id=None)


async def add_chair(user_id, chat_id, previous_message_id):
	"""
	Добавление кафедры пользователем

	:param user_id: ID юзера.
	:param chat_id: ID
	:param previous_message_id: ID прошлого сообщения
	:return:
	"""
	facult_id = await select_from_database(
		user_id,
		chat_id,
		'FACULTS',
		header='Выберите факультет',
	)
	# Админ отменил добавление
	if facult_id is None:
		await admin_menu(user_id=user_id, chat_id=chat_id)
		return
	new_chair_name, message_id = await request(
		user_id,
		chat_id,
		request_message='Введите название кафедры',
		delete_request_message=True
	)
	previous_message_id = message_id
	result = await add_row(
		user_id,
		chat_id,
		f'Подтвердите добавление кафедры "{new_chair_name}"',
		table='CHAIRS',
		filters={'name': new_chair_name, 'facult_id':facult_id},
		delete_message_after=True
	)

	match result:
		case AddingRowResult.INCORRECT_INPUT_DATA:
			await send_temporary_message(chat_id, 'Неправильные вводные данные (см. логи)', delay_seconds=2)
		case AddingRowResult.ROW_ALREADY_EXISTS:
			await send_temporary_message(chat_id, 'Такая кафедра уже существует', delay_seconds=2)
		case AddingRowResult.ABORTED_BY_USER:
			await send_temporary_message(chat_id, 'Отменяю...', delay_seconds=5)
		case AddingRowResult.SUCCESS:
			await send_temporary_message(chat_id, f'Успешно добавлена кафедра <b>"{new_chair_name}"</b>', delay_seconds=1)
	await asyncio.sleep(0.5)
	await admin_menu(user_id=user_id, chat_id=chat_id, previous_message_id=None)


async def add_direction(user_id, chat_id, previous_message_id):
	"""
	Добавление направления пользователем

	:param user_id: ID юзера
	:param chat_id: ID чата
	:param previous_message_id: ID прошлого сообщения
	:return:
	"""

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
		await admin_menu(user_id=user_id, chat_id=chat_id)
		return

	new_direction_name, message_id = await request(
		user_id,
		chat_id,
		request_message='Введите название направления',
		delete_request_message=True
	)
	previous_message_id = message_id
	result = await add_row(
		user_id,
		chat_id,
		f'Подтвердите добавление направления "{new_direction_name}"',
		table='DIRECTIONS',
		filters={'name': new_direction_name, 'chair_id':chair_id},
		delete_message_after=True
	)
	match result:
		case AddingRowResult.INCORRECT_INPUT_DATA:
			await send_temporary_message(chat_id, 'Неправильные вводные данные (см. логи)', delay_seconds=2)
		case AddingRowResult.ROW_ALREADY_EXISTS:
			await send_temporary_message(chat_id, 'Такое направление уже существует', delay_seconds=2)
		case AddingRowResult.ABORTED_BY_USER:
			await send_temporary_message(chat_id, 'Отменяю...', delay_seconds=1)
		case AddingRowResult.SUCCESS:
			await send_temporary_message(chat_id, f'Успешно добавлено направление <b>"{new_direction_name}"</b>',
			                             delay_seconds=5)
	await asyncio.sleep(0.5)
	await admin_menu(user_id=user_id, chat_id=chat_id)


async def delete_facult(user_id, chat_id, previous_message_id):
	"""
	Удаление факультета пользователем
	"""
	selected_facult = await select_from_database(
		user_id,
		chat_id,
		'FACULTS',
		header='Выберите факультет',
		output_field=['rowid', 'name']
	)
	if selected_facult is None:
		await admin_menu(
			user_id=user_id,
			chat_id=chat_id,
			previous_message_id=previous_message_id
		)
		return
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
	confirm_sub_deletion = False if len(chairs) == 0 \
		else await request_confirmation(
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
		last_message_id = last_message.id
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
			await asyncio.sleep(0.5)
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
		chat_id=chat_id
	)
	return


async def delete_chair(user_id, chat_id, previous_message_id):
	"""
	Удаление кафедры пользователем
	"""
	selected_facult = await select_from_database(
		user_id,
		chat_id,
		'FACULTS',
		header='Выберите факультет',
		output_field='rowid'
	)
	if selected_facult is None:
		await admin_menu(
			user_id=user_id,
			chat_id=chat_id,
			previous_message_id=previous_message_id
		)
		return
	selected_chair = await select_from_database(
		user_id,
		chat_id,
		'CHAIRS',
		{'facult_id': selected_facult},
		header='Выберите кафедру',
		output_field=['rowid', 'name']
	)
	if selected_chair is None:
		await admin_menu(
			user_id=user_id,
			chat_id=chat_id,
			previous_message_id=previous_message_id
		)
		return
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
	confirm_sub_deletion = False if len(directions) == 0 \
		else await request_confirmation(
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
		await asyncio.sleep(0.5)
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


async def delete_direction(user_id, chat_id, previous_message_id):
	"""
	Удаление направления пользователем
	"""
	selected_facult = await select_from_database(
		user_id,
		chat_id,
		'FACULTS',
		header='Выберите факультет',
		output_field='rowid'
	)
	if selected_facult is None:
		await admin_menu(
			user_id=user_id,
			chat_id=chat_id,
			previous_message_id=previous_message_id
		)
		return
	selected_chair = await select_from_database(
		user_id,
		chat_id,
		'CHAIRS',
		{'facult_id': selected_facult},
		header='Выберите кафедру',
		output_field='rowid'
	)
	if selected_chair is None:
		await admin_menu(
			user_id=user_id,
			chat_id=chat_id,
			previous_message_id=previous_message_id
		)
		return
	selected_direction = await select_from_database(
		user_id,
		chat_id,
		'DIRECTIONS',
		{'chair_id': selected_chair},
		header='Выберите направление',
		output_field=['rowid', 'name']
	)
	if selected_direction is None:
		await admin_menu(
			user_id=user_id,
			chat_id=chat_id,
			previous_message_id=previous_message_id
		)
		return
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


async def add_subject(user_id, chat_id, previous_message_id):
	"""
	Добавление предмета пользователем
	"""
	subject_name, message_id = await request(
		user_id,
		chat_id,
		request_message='Введите название предмета'
	)
	previous_message_id=message_id
	result = await add_row(
		user_id,
		chat_id,
		f'Подтвердите добавление предмета "{subject_name}"',
		table='SUBJECTS',
		filters={'name': subject_name},
		delete_message_after=True
	)
	match result:
		case AddingRowResult.INCORRECT_INPUT_DATA:
			await send_temporary_message(chat_id, 'Неправильные вводные данные (см. логи)', delay_seconds=7)
		case AddingRowResult.ROW_ALREADY_EXISTS:
			await send_temporary_message(chat_id, 'Такой предмет уже существует', delay_seconds=7)
		case AddingRowResult.ABORTED_BY_USER:
			await send_temporary_message(chat_id, 'Отменяю...', delay_seconds=5)
		case AddingRowResult.SUCCESS:
			await send_temporary_message(chat_id, f'Успешно добавлен предмет <b>"{subject_name}"</b>', delay_seconds=5)
	await asyncio.sleep(0.5)
	await admin_menu(user_id=user_id, chat_id=chat_id)


async def delete_subject(user_id, chat_id, previous_message_id):
	"""
	Удаление предмета пользователем
	"""
	selected_subject = await select_from_database(
		user_id,
		chat_id,
		'SUBJECTS',
		header='Выберите направление',
		output_field=['rowid', 'name']
	)
	if not selected_subject is None:
		async with connect_db() as db:
			await remove(
				database=db,
				table='SUBJECTS',
				filters={'rowid': selected_subject[0]}
			)
			await remove_all(
				database=db,
				table='SUBJECT_DIRECTIONS',
				filters={'subject_id': selected_subject[0]}
			)


async def edit_subject_connections(user_id, chat_id, previous_message_id):
	"""
	Добавление связи предмета с направлениями пользователем
	"""
	selected_subject = await select_from_database(
		user_id,
		chat_id,
		'SUBJECTS',
		header='Выберите предмет'
	)
	if selected_subject is None:
		await admin_menu(
			user_id=user_id,
			chat_id=chat_id,
			previous_message_id=previous_message_id
		)
		return
	while True:
		async with connect_db() as db:
			directions = await get_all(
				database=db,
				table='DIRECTIONS'
			)
			directions = list(dict(row) for row in directions)
			already_existing_connections = await get_all(
				database=db,
				table='SUBJECT_DIRECTIONS'
			)
			existing_ids = []
			for con in already_existing_connections:
				existing_ids.append((con['subject_id'], con['direction_id']))
			for direction in directions:
				if (direction['rowid'], selected_subject) in existing_ids:
					direction['name'] += ' ➖'
					direction['exist'] = True
				else:
					direction['name'] += ' ➕'
					direction['exist'] = False

		selected_connection = await request_list(
			user_id,
			chat_id,
			header='Выберите связь',
			items_list=directions,
			input_field='name',
			output_field=['rowid', 'name', 'exist']
		)

		if selected_connection is None:
			break

		if bool(selected_connection[2]):
			async with connect_db() as db:
				await remove(
					database=db,
					table='SUBJECT_DIRECTIONS',
					filters={'rowid': selected_connection[0]}
				)
		else:
			async with connect_db() as db:
				await insert(
					database=db,
					table='SUBJECT_DIRECTIONS',
					filters={
					'subject_id': selected_subject,
					'direction_id': selected_connection[0]
					}
				)
	await admin_menu(user_id=user_id, chat_id=chat_id, previous_message_id=None)

async def check_conspects(user_id, chat_id):
	# Сначала находим все конспекты, которые требуют проверки
	async with connect_db() as db:
		conspects_row = await get_all(
			database=db,
			table='CONSPECTS',
			filters={'status': 'pending'}
		)
	if len(conspects_row) == 0:
		await bot.send_message(chat_id, 'Нет непроверенных конспектов.')
		await asyncio.sleep(0.25)
		asyncio.create_task(admin_menu(user_id=user_id, chat_id=chat_id))
		return
	get_next_conspect = True
	response = 'back'
	next_button = InlineKeyboardButton('Дальше', callback_data='next_conspect')
	accept_button = InlineKeyboardButton('✅ Принять', callback_data='accept_conspect')
	decline_button = InlineKeyboardButton('❌ Отклонить', callback_data='decline_conspect')
	quit_button = InlineKeyboardButton('Назад в меню', callback_data='quit_checking')
	markup = InlineKeyboardMarkup()
	markup.row(accept_button, decline_button)
	markup.row(next_button)
	markup.row(quit_button)

	message = None
	while response != 'quit_checking':
		if len(conspects_row) == 0:
			await admin_menu(user_id=user_id, chat_id=chat_id)
			return
		next_conspect = conspects_row.pop()
		message = await send_conspect_message(
			user_id=user_id,
			chat_id=chat_id,
			conspect_row=next_conspect,
			reply_markup = markup,
			markup_text = 'Подтвердите или отклоните этот конспект'
		)
		response = await wait_for_callback_on_message(
			user_id,
			chat_id,
			message_id = message.id,
			delete_callback_after=False,
			timeout = 60*5
		)

		async with connect_db() as db:
			match response:
				case 'quit_checking':
					await admin_menu(user_id=user_id, chat_id=chat_id)
					return
				case 'accept_conspect':
					await update(
						database=db,
						table='CONSPECTS',
						filters = {'rowid': next_conspect['rowid']},
						values = ['accepted', ],
						columns = ['status', ]
					)
				case 'decline_conspect':
					await update(
						database=db,
						table='CONSPECTS',
						filters={'rowid': next_conspect['rowid']},
						values=['declined', ],
						columns=['status', ]
					)
				case 'next_conspect':
					continue
