# TODO !СДЕЛАТЬ РЕФАКТОРИНГ, ВСЁ ПЕРЕМЕСТИТЬ В РАЗНЫЕ ФАЙЛЫ!!!
# !!!!!!!!!!!!!!!!!!!!!!
# bot_project/
# ├─ code/
# │  ├─ database/queries.py        # у тебя уже есть
# │  ├─ logging.py                 # у тебя уже есть
# │  └─ ... 
# ├─ bot/
# │  ├─ __init__.py                # опционально — точка доступа к bot instance
# │  ├─ app.py                     # entrypoint: создание ботa, middlewares, polling
# │  ├─ config.py                  # чтение env и констант (TOKEN, DOWNLOAD_DIR и т.д.)
# │  ├─ states.py                  # RegStates, MenuStates
# │  ├─ utils.py                   # утилиты (delete_message_after_delay, get_greeting, др.)
# │  ├─ keyboards.py (?)           # фабрики InlineKeyboardMarkup / InlineKeyboardButton
# │  ├─ handlers/
# │  │  ├─ __init__.py
# │  │  ├─ start.py                # /start, меню открытия
# │  │  ├─ registration.py         # все state-обработчики регистрации
# │  │  ├─ navigation.py (?)       # choose_direction, пагинация, кнопки "next page"
# │  │  ├─ info.py                 # show_info, get_user_info
# │  │  └─ misc.py                 # логирование апдейтов, пустые колбэки и пр.
# │  ├─ services/
# │  │  └─ user_service.py         # get_user_info, сохранение пользователя, валидации
# │  └─ callbacks.py               # CallbackData фабрики и вспом. функции
# └─ README.md

import asyncio
import os
import random
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from code.bot.bot_instance import bot
from telebot.callback_data import CallbackData
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from code.bot.states import RegStates, MenuStates
from code.bot.utils import delete_message_after_delay, is_user_exists
from code.bot.handlers.info import get_user_info

from code.database.queries import connectDB, isExists, getAll, get, insert
from code.logging import logger

import code.bot.handlers.start

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


vote_cb = CallbackData('action', 'amount', prefix='vote')




# Обрабатывает кнопки, в случаях, если они ничего не должны делать, и при необходимости выводит сообщение на экран
@bot.callback_query_handler(func=lambda call: 'empty' in call.data)
async def empty_button(call):
	data = call.data.split()
	if len(data) == 1:
		await bot.answer_callback_query(call.id)
	else:
		message = ' '.join(data[1:])
		await bot.answer_callback_query(call.id, text=message, show_alert=False)


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
	async with connectDB() as database:
		isUserExists = await isExists(database=database, table="USERS", filters={"telegram_id": user_id})
	# Если пользователь найден, обрываем процесс регистрации
	if isUserExists:
		logger.info(f'The user ({user_id}) already exist. Stopping registration')
		await bot.send_message(chat_id, 'Вы уже зарегистрированы.')
		return
	else:
		async with bot.retrieve_data(user_id, chat_id) as data:
			data['table'] = 'FACULTS'
			data['page'] = 1
			data['filters'] = {}
			data['previous_message_id'] = None
		await bot.set_state(user_id, RegStates.wait_for_name, chat_id)
		await bot.send_message(chat_id, "Введите имя:")


# Сохранение имени пользователя
@bot.message_handler(state=RegStates.wait_for_name)
async def process_name(message=None):
	name = message.text
	if not re.fullmatch(r"^[А-Яа-яA-Za-z\-]{2,30}$", name):
		error_message = await bot.send_message(message.chat.id, "<b>Некорректное имя.</b>\n"
																"Оно должно содержать <b>только буквы</b> (от 2 до 30).\n"
																"Попробуйте ещё раз:", parse_mode='HTML')
		asyncio.create_task(delete_message_after_delay(bot, message.chat.id, error_message.message_id, 4))
		asyncio.create_task(delete_message_after_delay(bot, message.chat.id, message.id, 4))
		return
	async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
		data['name'] = name
	await bot.set_state(message.from_user.id, RegStates.wait_for_surname, message.chat.id)
	await bot.send_message(message.chat.id, "Введите фамилию:")


# Сохранение фамилии пользователя
@bot.message_handler(state=RegStates.wait_for_surname)
async def process_surname(message):
	surname = message.text
	if not re.fullmatch(r"^[А-Яа-яA-Za-z\-]{2,30}$", surname):
		error_message = await bot.send_message(message.chat.id, "<b>Некорректная фамилия.</b>\n"
																"Она должно содержать <b>только буквы</b> (от 2 до 30).\n"
																"Попробуйте ещё раз:\n", parse_mode='HTML')
		asyncio.create_task(delete_message_after_delay(bot, message.chat.id, error_message.message_id, 4))
		asyncio.create_task(delete_message_after_delay(bot, message.chat.id, message.id, 4))
		return
	async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
		data['surname'] = surname
	await bot.set_state(message.from_user.id, RegStates.wait_for_group, message.chat.id)
	await bot.send_message(message.chat.id, "Из какой вы группы?")


# Сохранение группы пользователя
@bot.message_handler(state=RegStates.wait_for_group)
async def process_group(message):
	group = message.text
	if not re.fullmatch(r"^[А-Яа-я]{1,10}-\d{1,3}[А-Яа-я]?$", group):
		error_message = await bot.send_message(message.chat.id, "<b>Некорректный формат группы</b>\n"
																"Ожидается что-то вроде <i>'ПИбд-12'</i> или <i>'МОАИСбд-11'</i>\n"
																"Попробуйте ещё раз:", parse_mode='HTML')
		asyncio.create_task(await delete_message_after_delay(bot, message.chat.id, error_message.message_id, 4))
		asyncio.create_task(await delete_message_after_delay(bot, message.chat.id, message.id, 4))
		return
	async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
		data['group'] = group
	await bot.set_state(message.from_user.id, RegStates.wait_for_facult, message.chat.id)
	await choose_direction(userID=message.from_user.id, chatID=message.chat.id)


# Обработка изменения страницы
@bot.callback_query_handler(func=lambda call: 'page' in call.data)
async def process_change_page_call(call):
	await bot.answer_callback_query(call.id)
	async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
		data['previous_message_id'] = call.message.message_id
		if 'next' in call.data:
			data['page'] += 1
		else:
			data['page'] -= 1
	await choose_direction(userID=call.from_user.id, chatID=call.message.chat.id)


# Обработка выбора пользователя
@bot.callback_query_handler(func=lambda call: 'next step' in call.data)
async def process_next_step_list(call):
	await bot.answer_callback_query(call.id)
	message = call.data.split()
	choice = message[2]
	async with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
		# Получаем rowid
		data[data['table']] = choice
		# Определяем следующую таблицу и фильтры
		match data['table']:
			case 'FACULTS':
				data['table'] = 'CHAIRS'
				data['filters'] = {'facult_id': int(choice)}
			case 'CHAIRS':
				data['table'] = 'DIRECTIONS'
				data['filters'] = {'chair_id': int(choice)}
			case 'DIRECTIONS':
				data['table'] = 'END_CHOOSING'
				data['filters'] = {}
		data['page'] = 1
		data['previous_message_id'] = call.message.message_id

	await choose_direction(userID=call.from_user.id, chatID=call.message.chat.id)


# Выводим список с выбором факультета, кафедры и направления
async def choose_direction(userID=None, chatID=None):
	# Получаем из даты информацию о текущей странице и таблице
	async with bot.retrieve_data(userID, chatID) as data:
		# Пробуем получить информации из data. Если её нет - записываем дефолтную
		try:
			table = data['table']
		except:
			data['table'] = 'FACULTS'
			table = 'FACULTS'
		try:
			previous_message_id = data['previous_message_id']
		except:
			previous_message_id = None
		try:
			page = data['page']
		except:
			data['page'] = 1
			page = 1
		try:
			filters = data['filters']
		except:
			data['filters'] = {}
			filters = {}
	if table == 'END_CHOOSING':
		await accept_registration(user_id=userID, chat_id=chatID)
		return
	# Получаем список из таблицы
	async with connectDB() as database:
		all_list = await getAll(database=database, table=table, filters=filters)

	# Определяем текущий индекс, последний индекс
	MAX_ELEMENTS_PER_PAGE = 6
	ELEMENTS_PER_ROW = 2
	max_page = max(len(all_list) // MAX_ELEMENTS_PER_PAGE, 1)
	if page > max_page:
		page = max_page
	current_index = (page - 1) * MAX_ELEMENTS_PER_PAGE
	max_index = min(len(all_list), current_index + MAX_ELEMENTS_PER_PAGE)

	# Собираем кнопки
	new_row = []
	markup = InlineKeyboardMarkup()
	for ind in range(current_index, max_index):
		row = all_list[ind]
		button = InlineKeyboardButton(row['name'], callback_data=f"next step {row['rowid']}")
		new_row.append(button)
		if len(new_row) >= ELEMENTS_PER_ROW:
			markup.row(*new_row)
			new_row = []
	# Кнопки перемещения страниц
	next_page_button = InlineKeyboardButton("--->", callback_data='empty' if page == max_page else 'next page')
	previous_page_button = InlineKeyboardButton("<---", callback_data='empty' if page == 1 else 'previous page')
	# question_button = InlineKeyboardButton("Не могу найти", callback_data='message moderator')
	markup.row(previous_page_button, next_page_button)

	# Собираем текст сообщения
	table_text = ''
	match table:
		case 'FACULTS':
			table_text = 'факультет'
		case 'CHAIRS':
			table_text = 'кафедру'
		case 'DIRECTIONS':
			table_text = 'направление'
	message_text = f"🔎 Выберите {table_text}\nСтр. {page} из {max_page}"

	# Выводим сообщение (если есть previous_message_id - меняем старое)
	if previous_message_id is None:
		await bot.send_message(chatID, message_text, reply_markup=markup)
	else:
		await bot.edit_message_text(message_text, chatID, previous_message_id)
		await bot.edit_message_reply_markup(chatID, previous_message_id, reply_markup=markup)


# Выводит сообщение, чтобы пользователь проверил правильность данных
# Если всё правильно -> переходим в end_register, где сохраняем всю нужную информацию в датабазу
# Если нет, просто заново начинаем процесс регистрации
async def get_registration_info(user_id=None, chat_id=None):
	async with bot.retrieve_data(user_id, chat_id) as data:
		name = data['name']
		surname = data['surname']
		group = data['group']
		direction_id = data['DIRECTIONS']
	async with connectDB() as database:
		direction = await get(database=database, table='DIRECTIONS', filters={'rowid': direction_id})
		chair = await get(database=database, table='CHAIRS', filters={'rowid': direction['chair_id']})
		facult = await get(database=database, table='FACULTS', filters={'rowid': chair['facult_id']})
	return name, surname, group, facult, chair, direction


# Проверяем у пользователя правильность информации. Если нет - начинаем регистрацию заново
async def accept_registration(user_id=None, chat_id=None):
	async with bot.retrieve_data(user_id, chat_id) as data:
		try:
			await bot.delete_message(chat_id, data['previous_message_id'])
		except Exception:
			pass
	name, surname, group, facult, chair, direction = await get_registration_info(user_id=user_id,
																				 chat_id=chat_id)

	# Собираем кнопки
	buttons = InlineKeyboardMarkup()
	buttons.add(InlineKeyboardButton("Всё правильно", callback_data="registration_accepted"))
	buttons.add(InlineKeyboardButton("Повторить регистрацию", callback_data="register"))
	await bot.send_message(chat_id,
						   f"Проверьте правильность данных\n\n"
						   f"<blockquote><b>Имя</b>: {name}\n"
						   f"<b>Фамилия</b>: {surname}\n"
						   f"<b>Учебная группа</b>: {group}\n\n"
						   f"<b>Факультет</b>: {facult['name']}\n"
						   f"<b>Кафедра</b>: {chair['name']}\n"
						   f"<b>Направление</b>: {direction['name']}</blockquote>\n",
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
	logger.info('Saving user in database.')
	name, surname, group, _, _, direction_ns = await get_registration_info(call.from_user.id, call.message.chat.id)

	# Добавляю запись в датабазу
	async with connectDB() as db:
		values = [str(call.from_user.id), name, surname, group, direction_ns["rowid"], 'user']
		columns = ['telegram_id', 'name', 'surname', 'study_group', 'direction_id', 'role']
		await insert(database=db, table='USERS', values=values, columns=columns)
	await bot.edit_message_text('Готово!', call.message.chat.id, message.message_id)
	logger.info('Successfully saved user in database.')
	await bot.set_state(call.from_user.id, MenuStates.main_menu, call.message.chat.id)
	await main_menu(user_id=call.from_user.id, chat_id=call.message.chat.id)


async def get_greeting():
	now = datetime.now(ZoneInfo('Europe/Ulyanovsk'))
	hour = now.hour
	if 5 <= hour < 12:
		greet = 'Доброе утро'
	elif 12 <= hour < 18:
		greet = 'Добрый день'
	elif 18 <= hour < 23:
		greet = 'Добрый вечер'
	else:
		greet = 'Доброй ночи.'
	phrases = ['С чего начнём?', 'Выберите нужную вам кнопку', 'Выберите действие ниже',
			   'Рад вас видеть.\nВыберите действие']
	return f'<b>{greet}!</b>\n\n{random.choice(phrases)}'


@bot.callback_query_handler(func=vote_cb.filter(action='open menu').check)
async def open_menu(call):
	await bot.answer_callback_query(call.id)
	await main_menu(call.from_user.id, call.message.chat.id, call.message.message_id)


async def main_menu(user_id, chat_id, previous_message_id=None):
	logger.info(f'Printing main menu for user({user_id})')
	greeting = await get_greeting()
	# Собираем markup
	markup = InlineKeyboardMarkup()
	show_info = InlineKeyboardButton('О пользователе 👤', callback_data='show_info')
	markup.row(show_info)
	async with bot.retrieve_data(user_id, chat_id) as data:
		if previous_message_id is None:
			message = await bot.send_message(chat_id=chat_id, text=greeting, reply_markup=markup, parse_mode='HTML')
		else:
			await bot.edit_message_text(text=greeting, chat_id=chat_id, message_id=previous_message_id,
										parse_mode='HTML')
			await bot.edit_message_reply_markup(chat_id=chat_id, message_id=previous_message_id, reply_markup=markup)





@bot.callback_query_handler(func=lambda call: call.data == 'show_info')
async def print_user_info(call):
	await bot.answer_callback_query(call.id)
	user_id = call.from_user.id
	chat_id = call.message.chat.id
	user_info = await get_user_info(chat_id=chat_id, user_id=user_id)
	text_message = ("<blockquote><b>Информация о пользователе</b>\n\n"
					f"<b>Имя</b>: {user_info['name']}\n"
					f"<b>Фамилия</b>: {user_info['surname']}\n"
					f"<b>Юзернейм</b>: @{call.from_user.username}\n\n"
					f"<b>Учебная группа</b>: {user_info['study_group']}\n"
					f"<b>Факультет</b>: {user_info['facult_name']}\n"
					f"<b>Кафедра</b>: {user_info['chair_name']}\n"
					f"<b>Направление</b>: {user_info['direction_name']}\n\n"
					f"<b>Кол-во загруженных конспектов</b>: В РАЗРАБОТКЕ</blockquote>")
	markup = InlineKeyboardMarkup()
	back_button = InlineKeyboardButton('Назад', callback_data=vote_cb.new(action='open menu',
																		  amount=str(call.message.message_id)))
	markup.row(back_button)

	await bot.edit_message_text(text=text_message, chat_id=chat_id, message_id=call.message.message_id,
									  parse_mode='HTML')
	await bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)


# Логирование всех обновлений (например, сообщений от пользователя)
async def log_updates(updates):
	for upd in updates:
		# Я как понял, в старых версиях upd был объектом со множеством подобъектов. Но сейчас это просто Message
		# Но на всякий случай сделаю try-except
		try:
			msg = upd.message
		except:
			msg = upd
		if not msg: continue
		logger.debug("%s | %s | %s | %s", datetime.now(timezone.utc).isoformat(),
					 msg.from_user.id, msg.from_user.username, msg.text)


async def main():
	try:
		logger.info("Starting polling...")
		bot.set_update_listener(log_updates)
		await bot.infinity_polling()
	finally:
		# гарантированно закрываем сессию aiohttp, чтобы не было "Unclosed client session"
		try:
			if hasattr(bot, "session") and bot.session:
				await bot.session.close()
				logger.debug("bot.session closed")
		except Exception as e:
			logger.exception("End session %s", e)


if __name__ == "__main__":
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		logger.info("Interrupted by user (KeyboardInterrupt)")
