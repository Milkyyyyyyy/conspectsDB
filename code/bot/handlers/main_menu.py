"""
В этом файле происходит обработка главного меню (пока что это только само главное меню и вывод информации о пользователе)
"""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from code.bot.bot_instance import bot
from code.bot.callbacks import vote_cb
from code.bot.services.user_service import get_user_info
from code.bot.utils import get_greeting, send_temporary_message
from code.logging import logger
from code.bot.services.requests import request
from code.bot.services.validation import validators
from code.database.queries import update
from code.database.service import connect_db

async def main_menu(user_id, chat_id, previous_message_id=None):
	logger.info(f'User({user_id}) is requesting main menu.')

	greeting = await get_greeting()
	# Собираем markup
	markup = InlineKeyboardMarkup()
	show_info = InlineKeyboardButton('О пользователе 👤', callback_data='show_info')
	markup.row(show_info)
	try:
		if previous_message_id is None:
			message = await bot.send_message(chat_id=chat_id, text=greeting, reply_markup=markup, parse_mode='HTML')
			logger.info("Sent new main menu message to user=%s chat=%s message_id=%s",
			            user_id, chat_id, getattr(message, "message_id", getattr(message, "id", None)))
		else:
			try:
				await bot.edit_message_text(text=greeting, chat_id=chat_id, message_id=previous_message_id,
												parse_mode='HTML')
				await bot.edit_message_reply_markup(chat_id=chat_id, message_id=previous_message_id, reply_markup=markup)
				logger.info("Edited existing message %s with main menu for user=%s chat=%s",
				            previous_message_id, user_id, chat_id)
			except Exception as e:
				logger.error("Can't edit message with id {%s}", previous_message_id)
	except Exception as e:
		logger.error(f'Unexpected error: {e}')

@bot.callback_query_handler(func=lambda call: call.data == 'show_info')
async def call_show_info(call):
	# Ответ на callback
	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))

	# Получаем информацию из callback
	user_id = call.from_user.id
	chat_id = call.message.chat.id
	previous_message_id = call.message.id
	username = call.from_user.username

	logger.debug("Callback show_info: user_id=%s chat_id=%s previous_message_id=%s",
	             user_id, chat_id, previous_message_id)
	await print_user_info(user_id=user_id, chat_id=chat_id, previous_message_id=previous_message_id, username=username)

async def print_user_info(user_id=None, chat_id=None, previous_message_id=None, username=None):
	logger.info("Showing user info: user_id=%s chat_id=%s message_id=%s", user_id, chat_id, previous_message_id)
	try:
		user_info = await get_user_info(chat_id=chat_id, user_id=user_id)
	except Exception as e:
		logger.exception(f"Failed to get user_info for user=%s chat=%s", user_id, chat_id)
		await send_temporary_message(bot, chat_id, 'Произошла ошибка')
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
	back_button = InlineKeyboardButton('Назад',
									   callback_data=vote_cb.new(action='open menu', amount=str(previous_message_id)))
	change_name_button = InlineKeyboardButton('Изменить имя', callback_data='change_name')
	change_surname_button = InlineKeyboardButton('Изменить фамилию', callback_data='change_surname')
	markup.row(change_name_button, change_surname_button)
	markup.row(back_button)
	try:
		if previous_message_id is None or not isinstance(previous_message_id, int):
			# Если id сообщения невалидный, отправляем новое сообщение вместо редактирования
			sent = await bot.send_message(chat_id=chat_id, text=text_message, reply_markup=markup, parse_mode='HTML')
			logger.info("Sent user info as new message to chat=%s message_id=%s", chat_id,
			            getattr(sent, "message_id", getattr(sent, "id", None)))
		else:
			await bot.edit_message_text(text=text_message,
			                            chat_id=chat_id,
			                            message_id=previous_message_id,
			                            parse_mode='HTML')
			await bot.edit_message_reply_markup(chat_id=chat_id, message_id=previous_message_id, reply_markup=markup)
			logger.info("Updated message %s with user info for user=%s", previous_message_id, user_id)
	except Exception:
		logger.exception("Failed to display user info for user=%s chat=%s", user_id, chat_id)
		try:
			await send_temporary_message(bot, chat_id, text='Не удалось отобразить информацию. Попробуйте ещё раз.',
			                             delay_seconds=3)
		except Exception:
			logger.exception("Also failed to send fallback error message to chat=%s", chat_id)

@bot.callback_query_handler(func=lambda call: call.data == 'change_name')
async def change_name(call):
	try:
		await bot.answer_callback_query(call.id)
	except Exception:
		logger.exception("Failed to answer callback_query (change_name) for user=%s",
		                 getattr(call.from_user, "id", None))

	user_id, chat_id, username = call.from_user.id, call.message.chat.id, call.from_user.username
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
	except Exception as e:
		logger.exception("Request for new name failed for user=%s chat=%s", user_id, chat_id)
		return
	if not isinstance(name, str):
		logger.info('User %s provided invalid name input: %r', user_id, name)
		await send_temporary_message(bot, chat_id, text='Имя не было изменено.', delay_seconds=10)
		return

	updated = None
	try:
		async with connect_db() as db:
			updated = await update(
				database=db,
				values=[name,],
				table='USERS',
				columns=['name'],
				filters={'telegram_id': user_id}
			)
			logger.info("Database update result for user=%s: %r", user_id, updated)
	except Exception as e:
		logger.exception(f'Database update failed for user=%s\n{e}', user_id)
		await send_temporary_message(bot, chat_id, text='Произошла ошибка!', delay_seconds=5)
		return
	finally:
		text = 'Обновлено' if updated else 'Не удалось обновить'
		await send_temporary_message(bot, chat_id, text=text, delay_seconds=3)
		await print_user_info(user_id=user_id, chat_id=chat_id, previous_message_id=call.message.message_id, username=username)

@bot.callback_query_handler(func=lambda call: call.data == 'change_surname')
async def change_surname(call):
	try:
		await bot.answer_callback_query(call.id)
	except Exception:
		logger.exception("Failed to answer callback_query for user=%s",
		                 getattr(call.from_user, "id", None))

	user_id, chat_id, username = call.from_user.id, call.message.chat.id, call.from_user.username
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
	except Exception as e:
		logger.exception("Request for new name failed for user=%s chat=%s", user_id, chat_id)
		return
	if not isinstance(surname, str):
		logger.info('User %s provided invalid name input: %r', user_id, surname)
		await send_temporary_message(bot, chat_id, text='Фамилия не была изменена.', delay_seconds=10)
		return

	updated = None
	try:
		async with connect_db() as db:
			updated = await update(
				database=db,
				values=[surname,],
				table='USERS',
				columns=['surname'],
				filters={'telegram_id': user_id}
			)
			logger.info("Database update result for user=%s: %r", user_id, updated)
	except Exception as e:
		logger.exception(f'Database update failed for user=%s\n{e}', user_id)
		await send_temporary_message(bot, chat_id, text='Произошла ошибка!', delay_seconds=5)
		return
	finally:
		text = 'Обновлено' if updated else 'Не удалось обновить'
		await send_temporary_message(bot, chat_id, text=text, delay_seconds=3)
		await print_user_info(user_id=user_id, chat_id=chat_id, previous_message_id=call.message.message_id, username=username)
