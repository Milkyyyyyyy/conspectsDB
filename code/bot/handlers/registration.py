from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from code.bot.bot_instance import bot
from code.bot.callbacks import call_factory
from code.bot.handlers.main_menu import main_menu
from code.bot.services.requests import request, request_list, request_confirmation
from code.bot.services.user_service import is_user_exists, save_user_in_database
from code.bot.services.validation import validators
from code.bot.utils import (delete_message_after_delay, send_temporary_message, send_reminder_contact_moderator,
                            send_message_after)
from code.database.queries import get_all
from code.database.service import connect_db
from code.logging import logger


@bot.callback_query_handler(func=call_factory.filter(area='registration').check)
async def callback_handler(call):
	logger.debug('Handle callback in registration...')
	user_id = call.from_user.id
	chat_id = call.message.chat.id
	message_id = call.message.id

	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))

	action = call_factory.parse(callback_data=call.data)['action']
	match action:
		case 'start_register':
			await start_registration(user_id=user_id, chat_id=chat_id)
			await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)


# Обработка команды /register
@bot.message_handler(commands=['register'])
async def start_registration(message=None, user_id=None, chat_id=None):
	# Если на вход не подано user_id и chat_id, получаем эту информацию из объекта message
	if user_id is None:
		user_id = message.from_user.id
	if chat_id is None:
		chat_id = message.chat.id

	logger.info("Register command invoked")
	logger.debug(f"cmd_register params: user_id={user_id}, chat_id={chat_id}")

	# Проверяем, существует ли пользователь
	try:
		exists = await is_user_exists(user_id)
		logger.debug("is_user_exists result")
	except Exception as e:
		logger.exception("Error while checking user existence", exc_info=e)
		await bot.send_message(chat_id, "Произошла ошибка проверки пользователя. Повторите позже.")
		return

	# Если пользователь найден, обрываем процесс регистрации
	if exists:
		logger.info("User already exists — stopping registration")
		await send_temporary_message(
			chat_id=chat_id,
			text='Вы уже зарегистрированы.',
			delay_seconds=2
		)
		return

	# Запрашиваем у пользователя всю нужную информацию
	name, surname, group = '', '', ''
	facult = chair = direction = (None, None)
	try:
		name, _ = await request(
			user_id=user_id,
			chat_id=chat_id,
			request_message='Введите <b>ваше</b> имя:',
			validator=validators.name
		)
		if name is None:
			logger.info("Name request returned None — stopping registration")
			await stop_registration(chat_id)
			return
		surname, _ = await request(
			user_id=user_id,
			chat_id=chat_id,
			request_message='Введите <b>вашу</b> фамилию:',
			validator=validators.surname
		)
		if surname is None:
			logger.info("Surname request returned None — stopping registration")
			await stop_registration(chat_id)
			return
		group, _ = await request(
			user_id=user_id,
			chat_id=chat_id,
			request_message='Введите учебную группу:',
			validator=validators.group
		)
		if group is None:
			logger.info("Group request returned None — stopping registration")
			await stop_registration(chat_id)
			return

		# Получаем справочники из БД и просим выбрать
		async with connect_db() as db:
			logger.debug("Fetching faculties from DB")
			facult_db = await get_all(database=db, table='FACULTS')
			await send_reminder_contact_moderator(
				chat_id,
				text='<b>Не можете что-то найти?</b>\n'
				     'Вы можете помочь расширить список и сделать бота удобнее',
				delay=0.5
			)
			facult = await request_list(
				user_id=user_id,
				chat_id=chat_id,
				header='Выберите ваш <b>факультет</b>\n',
				items_list=facult_db,
				input_field='name',
				output_field=['name', 'rowid']
			)
			if not facult:
				logger.info("Faculty selection cancelled or empty")
				await stop_registration(chat_id)
				return

			logger.debug("Fetching chairs for faculty from DB")
			chair_db = await get_all(database=db, table='CHAIRS', filters={'facult_id': facult[1]})
			chair = await request_list(
				user_id=user_id,
				chat_id=chat_id,
				header='Выберите вашу <b>кафедру</b>\n',
				items_list=chair_db,
				input_field='name',
				output_field=['name', 'rowid']
			)
			if not chair:
				logger.info("Chair selection cancelled or empty")
				await stop_registration(chat_id)
				return

			logger.debug("Fetching directions for chair from DB")
			direction_db = await get_all(database=db, table='DIRECTIONS', filters={'chair_id': chair[1]})
			direction = await request_list(
				user_id=user_id,
				chat_id=chat_id,
				header='Выберите ваше <b>направление</b>\n',
				items_list=direction_db,
				input_field='name',
				output_field=['name', 'rowid']
			)
			if not direction:
				logger.info("Direction selection cancelled or empty")
				await stop_registration(chat_id)
				return
	except Exception as e:
		# Логируем исключение и завершаем регистрацию аккуратно
		logger.exception("Unexpected error during registration flow", exc_info=e)
		await send_temporary_message(chat_id, 'Произошла ошибка при вводе данных. Попробуйте ещё раз.', delay_seconds=5)
		return
	# Вызываем подтверждение регистрации
	await accept_registration(
		user_id=user_id,
		chat_id=chat_id,
		name=name,
		surname=surname,
		group=group,
		facult=facult,
		chair=chair,
		direction=direction
	)


async def stop_registration(chat_id):
	logger.info("stop_registration called — user cancelled the flow")
	await send_temporary_message(chat_id, 'Завершаю регистрацию...', delay_seconds=10)
	raise Exception('Interrupt registration')


# Проверяем у пользователя правильность информации. Если нет - начинаем регистрацию заново
async def accept_registration(
		user_id=None, chat_id=None, name=None, surname=None, group=None, facult=None, chair=None,
		direction=None):
	logger.debug("Presenting registration confirmation to user")

	# Собираем кнопки
	buttons = InlineKeyboardMarkup()
	buttons.add(InlineKeyboardButton("Всё правильно", callback_data="registration_accepted"))
	buttons.add(InlineKeyboardButton("Повторить регистрацию", callback_data="register"))
	text = (f"Проверьте правильность данных\n\n"
	        f"<blockquote><b>Имя</b>: {name}\n"
	        f"<b>Фамилия</b>: {surname}\n"
	        f"<b>Учебная группа</b>: {group}\n\n"
	        f"<b>Факультет</b>: {facult[0]}\n"
	        f"<b>Кафедра</b>: {chair[0]}\n"
	        f"<b>Направление</b>: {direction[0]}</blockquote>\n")
	try:
		response = await request_confirmation(
			user_id=user_id,
			chat_id=chat_id,
			text=text,
			accept_text='Всё правильно',
			decline_text='Повторить регистрацию',
		)
	except Exception as e:
		logger.exception("Error while asking for registration confirmation", exc_info=e)
		await send_temporary_message(chat_id, text='Произошла ошибка. Повторите позже.', delay_seconds=5)
		return

	# Пользователь вызвал команду /cancel
	if response is None:
		logger.info("User cancelled at confirmation step")
		await send_temporary_message(chat_id, text='Отменяю регситрацию...', delay_seconds=5)
		return

	# Сохраняем пользователя в датабазу и выводим сообщение
	if response:
		logger.info("User accepted registration — proceeding to save")
		await end_registration(
			user_id=user_id,
			chat_id=chat_id,
			name=name,
			surname=surname,
			group=group,
			direction_id=direction[1],
			role='user'
		)
	else:
		logger.info("User requested to repeat registration")
		await start_registration(user_id=user_id, chat_id=chat_id)
		return


# Завершает регистрацию
async def end_registration(
		user_id=None, chat_id=None, name=None, surname=None, group=None, direction_id=None,
		role=None):
	logger.debug("Starting end_registration")
	previous_message = await bot.send_message(chat_id, 'Завершаю регистрацию...')
	previous_message_id = previous_message.id
	logger.debug("Sent intermediate 'finishing' message")

	saved = False
	try:
		saved = await save_user_in_database(
			user_id=user_id,
			name=name,
			surname=surname,
			group=group,
			direction_id=direction_id,
			role=role
		)
		logger.debug("save_user_in_database returned")
	except Exception as e:
		logger.exception("Error while saving user in database", exc_info=e)
		try:
			await bot.edit_message_text(text='Произошла ошибка. Повторите попытку позже', chat_id=chat_id,
			                            message_id=previous_message_id)
			logger.debug("Updated previous message to show error")
		except Exception as e2:
			logger.warning("Failed to edit previous message after DB error", exc_info=e2)
		await delete_message_after_delay(chat_id=chat_id, message_id=previous_message_id, delay_seconds=5)
		return
	finally:
		text = 'Регистрация прошла успешно' if saved else 'Не удалось зарегистрироваться.'
		await bot.edit_message_text(text=text, chat_id=chat_id, message_id=previous_message_id)
		await delete_message_after_delay(chat_id=chat_id, message_id=previous_message_id, delay_seconds=5)


		if saved:
			try:
				await main_menu(user_id=user_id, chat_id=chat_id)
			except Exception as e:
				logger.exception('Failed to open main menu after registration')
