"""
В этом файле происходит обработка главного меню (пока что это только само главное меню и вывод информации о пользователе)
"""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from code.bot.bot_instance import bot
from code.bot.callbacks import call_factory
from code.bot.services.requests import request, request_list
from code.bot.services.user_service import get_user_info
from code.bot.services.validation import validators
from code.bot.utils import get_greeting, send_temporary_message, safe_edit_message, delete_message_after_delay
from code.database.queries import update, get, get_all, insert
from code.database.service import connect_db
from code.logging import logger
from code.utils import getkey


@bot.callback_query_handler(func=call_factory.filter(area='main_menu').check)
async def callback_handler(call):
	logger.debug('Handle callback in main_menu...')
	user_id = call.from_user.id
	chat_id = call.message.chat.id
	message_id = call.message.id
	username = call.from_user.username

	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))

	action = call_factory.parse(callback_data=call.data)['action']
	match action:
		case 'main_menu':
			await main_menu(user_id, chat_id, message_id)
		case 'show_info':
			await print_user_info(
				user_id=user_id,
				chat_id=chat_id,
				previous_message_id=message_id,
				username=username
			)
		case 'change_name':
			await change_name(user_id, chat_id, username, message_id)
		case 'change_surname':
			await change_surname(user_id, chat_id, username, message_id)
		case 'change_facult':
			await change_facult(user_id, chat_id, username, message_id)


async def main_menu(user_id, chat_id, previous_message_id=None):
	logger.info(f'User({user_id}) is requesting main menu.')

	async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
		is_user_moderator = await getkey(data, 'is_user_moderator', None)
		if is_user_moderator is None:
			async with connect_db() as db:
				user_row = await get(
					database=db,
					table='USERS',
					filters={'telegram_id': user_id}
				)
				is_user_moderator = (user_row['role'] in ('moderator', 'admin'))
				data['is_user_moderator'] = is_user_moderator
		is_user_moderator = bool(is_user_moderator)

	# Собираем reply_markup
	markup = InlineKeyboardMarkup()
	show_info_button = InlineKeyboardButton(
		'О пользователе 👤',
		callback_data=call_factory.new(
			area='main_menu',
			action='show_info'
		)
	)
	upload_conspect_button = InlineKeyboardButton(
		'Загрузить конспект',
		callback_data=call_factory.new(
			area='conspects_menu',
			action='upload_conspect'
		)
	)
	markup.row(upload_conspect_button)
	markup.row(show_info_button)

	# Если юзер модератор, добавляем кнопку с доступом к панели админа
	if is_user_moderator:
		moderator_menu = InlineKeyboardButton(
			'Админ панель',
			callback_data=call_factory.new(
				area='admin_menu',
				action='admin_menu'
			)
		)
		markup.row(moderator_menu)

	greeting = await get_greeting()
	await safe_edit_message(
		previous_message_id,
		chat_id,
		user_id,
		text=greeting,
		reply_markup=markup
	)


async def print_user_info(user_id=None, chat_id=None, previous_message_id=None, username=None):
	logger.info("Showing user info: user_id=%s chat_id=%s message_id=%s", user_id, chat_id, previous_message_id)
	try:
		user_info = await get_user_info(chat_id=chat_id, user_id=user_id)
	except Exception as e:
		logger.exception(f"Failed to get user_info for user=%s chat=%s", user_id, chat_id)
		await send_temporary_message(chat_id, 'Произошла ошибка')
		return

	text_message = ("<blockquote><b>Информация о пользователе</b>\n\n"
	                f"<b>Имя</b>: {user_info['name']}\n"
	                f"<b>Фамилия</b>: {user_info['surname']}\n"
	                f"<b>Юзернейм</b>: @{username}\n\n"
	                f"<b>Учебная группа</b>: {user_info['study_group']}\n"
	                f"<b>Факультет</b>: {user_info['facult_name']}\n"
	                f"<b>Кафедра</b>: {user_info['chair_name']}\n"
	                f"<b>Направление</b>: {user_info['direction_name']}\n\n"
	                f"<b>Кол-во загруженных конспектов</b>: В РАЗРАБОТКЕ</blockquote>")
	markup = InlineKeyboardMarkup()
	back_button = InlineKeyboardButton(
		'Назад',
		callback_data=call_factory.new(
			area='main_menu',
			action='main_menu'
		)
	)
	change_name_button = InlineKeyboardButton(
		'Изменить имя',
		callback_data=call_factory.new(
			area='main_menu',
			action='change_name'
		)
	)
	change_surname_button = InlineKeyboardButton(
		'Изменить фамилию',
		callback_data=call_factory.new(
			area='main_menu',
			action='change_surname'
		)
	)
	change_surname_button = InlineKeyboardButton(
		'Изменить факультет',
		callback_data=call_factory.new(
			area='main_menu',
			action='change_facult'
		)
	)
	markup.row(change_name_button, change_surname_button)
	markup.row(back_button)
	try:
		if previous_message_id is None or not isinstance(previous_message_id, int):
			# Если id сообщения невалидный, отправляем новое сообщение вместо редактирования
			sent = await bot.send_message(chat_id=chat_id, text=text_message, reply_markup=markup, parse_mode='HTML')
			logger.info("Sent user info as new message to chat=%s message_id=%s", chat_id,
			            getattr(sent, "message_id", getattr(sent, "id", None)))
		else:
			await bot.edit_message_text(
				text=text_message,
				chat_id=chat_id,
				message_id=previous_message_id,
				parse_mode='HTML'
			)
			await bot.edit_message_reply_markup(chat_id=chat_id, message_id=previous_message_id, reply_markup=markup)
			logger.info("Updated message %s with user info for user=%s", previous_message_id, user_id)
	except Exception:
		logger.exception("Failed to display user info for user=%s chat=%s", user_id, chat_id)
		try:
			await send_temporary_message(chat_id, text='Не удалось отобразить информацию. Попробуйте ещё раз.',
			                             delay_seconds=3)
		except Exception:
			logger.exception("Also failed to send fallback error message to chat=%s", chat_id)

async def change_facult(user_id, chat_id, username, previous_message_id):
	logger.info("Initiating change_facult for user=%s chat=%s", user_id, chat_id)
	try:
		async with connect_db() as db:
			facults = await get_all(
				database=db,
				table='FACULTS'
			)
			facult_choice = await request_list(
				user_id=user_id,
				chat_id=chat_id,
				items_list=facults,
				input_field='name',
				output_field='rowid'
			)
			if facult_choice is None:
				raise Exception('Interrupt by user')
			await change_chair(user_id, chat_id, username, previous_message_id, facult_rowid=facult_choice, connection=db)
	except Exception:
		logger.exception("Failed to change facult for user=%s chat=%s", user_id, chat_id)
		await print_user_info(user_id=user_id, chat_id=chat_id, previous_message_id=previous_message_id,
		                      username=username)
		return
async def change_chair(user_id, chat_id, username, previous_message_id, facult_rowid=None, connection=None):
	logger.info("Initiating change_chair for user=%s chat=%s", user_id, chat_id)
	try:
		async with connect_db(connection) as db:
			user_info = None
			if facult_rowid is None:
				user_info = await get_user_info(chat_id, user_id)
				facult_rowid = user_info['facult_id']

			chairs = await get_all(
				database=db,
				table='CHAIRS',
				filters={'facult_id': facult_rowid}
			)
			chair_choice = await request_list(
				user_id=user_id,
				chat_id=chat_id,
				items_list=chairs,
				input_field='name',
				output_field='rowid'
			)
			if chair_choice is None:
				raise Exception('Interrupt by user')
			await change_direction(user_id, chat_id, username, previous_message_id, chair_rowid=chair_choice, user_info=user_info, connection=db)
	except Exception:
		logger.exception("Failed to change chair for user=%s chat=%s", user_id, chat_id)
		await print_user_info(user_id=user_id, chat_id=chat_id, previous_message_id=previous_message_id,
		                      username=username)
		return
async def change_direction(user_id, chat_id, username, previous_message_id, chair_rowid=None, user_info=None, connection=None):
	logger.info("Initiating change_chair for user=%s chat=%s", user_id, chat_id)
	try:
		async with connect_db(connection) as db:
			if chair_rowid is None:
				if user_info is None:
					user_info = await get_user_info(chat_id, user_id)
				chair_rowid = user_info['chair_id']
			directions = await get_all(
				database=db,
				table='DIRECTIONS',
				filters={'chair_id': chair_rowid}
			)
			direction_choice = await request_list(
				user_id=user_id,
				chat_id=chat_id,
				items_list=directions,
				input_field='name',
				output_field='rowid'
			)
			if direction_choice is None:
				raise Exception('Interrupt by user')
			await update(
				database=db,
				table='USERS',
				filters={'user_id': user_id},
				values=[direction_choice, ],
				columns=['direction_id']
			)
	except Exception:
		logger.exception("Failed to change direction for user=%s chat=%s", user_id, chat_id)
		await print_user_info(user_id=user_id, chat_id=chat_id, previous_message_id=previous_message_id,
		                      username=username)
		return

async def change_name(user_id, chat_id, username, previous_message_id):
	logger.info("Initiating change_name for user=%s chat=%s", user_id, chat_id)

	name = None
	try:
		name = await request(
			user_id=user_id,
			chat_id=chat_id,
			timeout=30,
			validator=validators.name,
			request_message='Введите новое имя:'
		)
		if not isinstance(name, str):
			logger.info('User %s provided invalid name input: %r', user_id, name)
			await send_temporary_message(chat_id, text='Имя не было изменено.', delay_seconds=10)
			raise Exception('Invalid input')
	except Exception as e:
		logger.exception("Request for new name failed for user=%s chat=%s", user_id, chat_id)
		await print_user_info(user_id=user_id, chat_id=chat_id, previous_message_id=previous_message_id,
		                      username=username)
		return


	updated = None
	try:
		async with connect_db() as db:
			updated = await update(
				database=db,
				values=[name, ],
				table='USERS',
				columns=['name'],
				filters={'telegram_id': user_id}
			)
			logger.info("Database update result for user=%s: %r", user_id, updated)
	except Exception as e:
		logger.exception(f'Database update failed for user=%s\n{e}', user_id)
		await send_temporary_message(chat_id, text='Произошла ошибка!', delay_seconds=5)
		await print_user_info(user_id=user_id, chat_id=chat_id, previous_message_id=previous_message_id,
		                      username=username)
		return
	finally:
		text = 'Обновлено' if updated else 'Не удалось обновить'
		await send_temporary_message(chat_id, text=text, delay_seconds=3)
		await print_user_info(user_id=user_id, chat_id=chat_id, previous_message_id=previous_message_id,
		                      username=username)


async def change_surname(user_id, chat_id, username, previous_message_id):
	logger.info("Initiating change_name for user=%s chat=%s", user_id, chat_id)

	surname = None
	try:
		surname = await request(
			user_id=user_id,
			chat_id=chat_id,
			timeout=30,
			validator=validators.surname,
			request_message='Введите новую фамилию:'
		)
		if not isinstance(surname, str):
			logger.info('User %s provided invalid name input: %r', user_id, surname)
			await send_temporary_message(chat_id, text='Фамилия не была изменена.', delay_seconds=10)
			raise Exception('Invalid input')
	except Exception as e:
		logger.exception("Request for new name failed for user=%s chat=%s", user_id, chat_id)
		await print_user_info(user_id=user_id, chat_id=chat_id, previous_message_id=previous_message_id,
		                      username=username)
		return


	updated = None
	try:
		async with connect_db() as db:
			updated = await update(
				database=db,
				values=[surname, ],
				table='USERS',
				columns=['surname'],
				filters={'telegram_id': user_id}
			)
			logger.info("Database update result for user=%s: %r", user_id, updated)
	except Exception as e:
		logger.exception(f'Database update failed for user=%s\n{e}', user_id)
		await send_temporary_message(chat_id, text='Произошла ошибка!', delay_seconds=5)
		await print_user_info(user_id=user_id, chat_id=chat_id, previous_message_id=previous_message_id,
		                      username=username)
		return
	finally:
		text = 'Обновлено' if updated else 'Не удалось обновить'
		await send_temporary_message(chat_id, text=text, delay_seconds=3)
		await print_user_info(user_id=user_id, chat_id=chat_id, previous_message_id=previous_message_id,
		                      username=username)
