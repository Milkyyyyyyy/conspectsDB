import asyncio
import re

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from code.bot.bot_instance import bot
from code.bot.handlers.main_menu import main_menu
from code.bot.services.user_service import is_user_exists, save_user_in_database
from code.bot.states import RegStates, MenuStates
from code.bot.utils import delete_message_after_delay, send_temporary_message
from code.database.queries import getAll, get
from code.database.service import connectDB
from code.bot.services.requests import request, request_list
from code.bot.services.validation import validators
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
		# async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
		# 	data['table'] = 'FACULTS'
		# 	data['page'] = 1
		# 	data['filters'] = {}
		# 	data['previous_message_id'] = None
		# await bot.set_state(user_id=user_id, state = RegStates.wait_for_direction, chat_id=chat_id)
		# await choose_direction(userID=user_id, chatID=chat_id)
		name = await request(
			user_id=user_id,
			chat_id=chat_id,
			request_message='Введите <b>ваше</b> имя:',
			waiting_for='name',
			validator=validators.name
		)
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
				input_field = 'name',
				output_field = ['name', 'rowid']
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

		async with bot.retrieve_data(user_id=user_id, chat_id=chat_id) as data:
			data['name'] = name
			data['surname'] = surname
			data['group'] = group
			data['facult_id']=facult[1]
			data['chair_id'] = chair[1]
			data['direction_id'] = direction[1]
		await accept_registration(
			user_id=user_id,
			chat_id=chat_id,
			name=name,
			surname=surname,
			group=group,
			facult_name=facult[0],
			chair_name=chair[0],
			direction_name=direction[0]
		)

# Проверяем у пользователя правильность информации. Если нет - начинаем регистрацию заново
async def accept_registration(user_id=None, chat_id=None, name=None, surname=None, group=None, facult_name=None, chair_name=None, direction_name=None):
	# Собираем кнопки
	buttons = InlineKeyboardMarkup()
	buttons.add(InlineKeyboardButton("Всё правильно", callback_data="registration_accepted"))
	buttons.add(InlineKeyboardButton("Повторить регистрацию", callback_data="register"))
	await bot.send_message(chat_id,
						   f"Проверьте правильность данных\n\n"
						   f"<blockquote><b>Имя</b>: {name}\n"
						   f"<b>Фамилия</b>: {surname}\n"
						   f"<b>Учебная группа</b>: {group}\n\n"
						   f"<b>Факультет</b>: {facult_name}\n"
						   f"<b>Кафедра</b>: {chair_name}\n"
						   f"<b>Направление</b>: {direction_name}</blockquote>\n",
						   reply_markup=buttons, parse_mode='HTML')


# Сохраняем информацию в датабазу
@bot.callback_query_handler(func=lambda call: call.data == 'registration_accepted')
async def end_registration(call):
	async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
		data['previous_message_id'] = None
	logger.info('Registration accepted.')
	await bot.answer_callback_query(call.id)
	message = await bot.send_message(call.message.chat.id, 'Завершаю регистрацию...')
	try:
		await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
	except Exception:
		pass
	# Сохраняем информацию в датабазу
	async with bot.retrieve_data(user_id=call.from_user.id, chat_id=call.message.chat.id) as data:
		name = data['name']
		surname = data['surname']
		group = data['group']
		direction_id = data['direction_id']

	# Добавляю запись в датабазу
	saved = await save_user_in_database(
		user_id=call.from_user.id,
		name=name,
		surname=surname,
		group=group,
		direction_id=direction_id,
		role='user'
	)
	if saved:
		await bot.edit_message_text('Готово!', call.message.chat.id, message.message_id)
		logger.info('Successfully saved user in database.')
		await bot.set_state(call.from_user.id, MenuStates.main_menu, call.message.chat.id)
		await main_menu(user_id=call.from_user.id, chat_id=call.message.chat.id)
	else:
		await bot.send_message(call.message.chat.id, 'Не удалось зарегестрироваться')
