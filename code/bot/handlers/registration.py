from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from code.bot.bot_instance import bot
from code.bot.handlers.main_menu import main_menu
from code.bot.services.requests import request, request_list, request_confirmation
from code.bot.services.user_service import is_user_exists, save_user_in_database
from code.bot.services.validation import validators
from code.bot.utils import delete_message_after_delay, send_temporary_message
from code.database.queries import getAll
from code.database.service import connectDB
from code.logging import logger


# =================== Регистрация ===================
# Обработка команды кнопки регистрации
@bot.callback_query_handler(func=lambda call: call.data == 'register')
async def callback_start_register(call):
	logger.info(f'The registration button has been pressed (user_id = {call.from_user.id})')
	await bot.answer_callback_query(call.id)
	# Удаляем кнопку регистрации из сообщения (если не получилось, то ничего не делаем
	try:
		await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
	except Exception:
		pass
	await cmd_register(user_id=call.from_user.id, chat_id=call.message.chat.id)


# Обработка команды /register
@bot.message_handler(commands=['register'])
async def cmd_register(message=None, user_id=None, chat_id=None):
	logger.info('The /register command has been invoked')
	# Если на вход не подано user_id и chat_id, получаем эту информацию из объекта message
	if user_id is None:
		user_id = message.from_user.id
	if chat_id is None:
		chat_id = message.chat.id
	logger.debug(f'user_id={user_id}, chat_id={chat_id}')
	# Проверяем, существует ли пользователь
	isUserExists = await is_user_exists(user_id)
	# Если пользователь найден, обрываем процесс регистрации
	if isUserExists:
		logger.info(f'The user ({user_id}) already exist. Stopping registration')
		await bot.send_message(chat_id, 'Вы уже зарегистрированы.')
		return
	else:
		# Запрашиваем у пользователя всю нужную информацию
		name, surname, group = '', '', ''
		try:
			name = await request(
				user_id=user_id,
				chat_id=chat_id,
				request_message='Введите <b>ваше</b> имя:',
				waiting_for='name',
				validator=validators.name
			)
			if name is None:
				await stop_registration(chat_id)
			surname = await request(
				user_id=user_id,
				chat_id=chat_id,
				request_message='Введите <b>вашу</b> фамилию:',
				waiting_for='surname',
				validator=validators.surname
			)
			group = await request(
				user_id=user_id,
				chat_id=chat_id,
				request_message='Введите учебную группу:',
				waiting_for='group',
				validator=validators.group
			)
			async with connectDB() as db:
				facult_db = await getAll(database=db, table='FACULTS')
				facult = await request_list(
					user_id=user_id,
					chat_id=chat_id,
					header='Выберите ваш <b>факультет</b>\n',
					items_list=facult_db,
					input_field='name',
					output_field=['name', 'rowid']
				)

				chair_db = await getAll(database=db, table='CHAIRS', filters={'facult_id': facult[1]})
				chair = await request_list(
					user_id=user_id,
					chat_id=chat_id,
					header='Выберите вашу <b>кафедру</b>\n',
					items_list=chair_db,
					input_field='name',
					output_field=['name', 'rowid']
				)

				direction_db = await getAll(database=db, table='DIRECTIONS', filters={'chair_id': chair[1]})
				direction = await request_list(
					user_id=user_id,
					chat_id=chat_id,
					header='Выберите ваше <b>направление</b>\n',
					items_list=direction_db,
					input_field='name',
					output_field=['name', 'rowid']
				)
		finally:
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
	await send_temporary_message(bot, chat_id, 'Завершаю регистрацию...', delay_seconds=10)
	raise Exception('Interrupt registration')


# Проверяем у пользователя правильность информации. Если нет - начинаем регистрацию заново
async def accept_registration(user_id=None, chat_id=None, name=None, surname=None, group=None, facult=None, chair=None,
							  direction=None):
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
	response = await request_confirmation(
		user_id=user_id,
		chat_id=chat_id,
		text=text,
		accept_text='Всё правильно',
		decline_text='Повторить регистрацию',
	)
	# Пользователь вызвал команду /cancel
	if response is None:
		await send_temporary_message(bot, chat_id, text='Отменяю регситрацию...', delay_seconds=5)
		return
	# Сохраняем пользователя в датабазу и выводим сообщение
	if response:
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
		await cmd_register(user_id=user_id, chat_id=chat_id)
		return


# Завершает регистрацию
async def end_registration(user_id=None, chat_id=None, name=None, surname=None, group=None, direction_id=None,
						   role=None):
	previous_message_id = (await bot.send_message(chat_id, 'Завершаю регистрацию...')).id
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
	except:
		await bot.edit_message_text(text='Произошла ошибка. Повторите попытку позже', chat_id=chat_id,
									message_id=previous_message_id)
		await delete_message_after_delay(bot, chat_id=chat_id, message_id=previous_message_id, delay_seconds=5)
	finally:
		text = 'Регистрация прошла успешно' if saved else 'Не удалось зарегистрироваться.'
		await bot.edit_message_text(text=text, chat_id=chat_id, message_id=previous_message_id)
		await delete_message_after_delay(bot, chat_id=chat_id, message_id=previous_message_id, delay_seconds=5)
		if saved:
			await main_menu(user_id=user_id, chat_id=chat_id)
