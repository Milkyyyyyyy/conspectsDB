from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from zoneinfo import ZoneInfo
from datetime import datetime
from code.bot.bot_instance import bot
from code.bot.callbacks import call_factory
from code.bot.handlers.main_menu import main_menu
from code.bot.services.requests import request, request_list, request_confirmation
from code.bot.services.user_service import is_user_exists, save_user_in_database
from code.bot.services.validation import validators
from code.bot.utils import delete_message_after_delay, send_temporary_message
from code.database.queries import get_all
from code.database.service import connect_db
from code.logging import logger

@bot.callback_query_handler(func=call_factory.filter(area='conspects_menu').check)
async def callback_handler(call):
	logger.debug('Handle callback in creation...')
	user_id = call.from_user.id
	chat_id = call.message.chat.id
	message_id = call.message.id

	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))

	action = call_factory.parse(callback_data=call.data)['action']
	match action:
		case 'upload_conspect':
			await create_conspect(user_id=user_id, chat_id=chat_id)
			await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)

@bot.message_handler(commands=['new_conspect'])
async def create_conspect(message=None, user_id=None, chat_id=None):

	if user_id is None:
		user_id = message.from_user.id
	if chat_id is None:
		chat_id = message.chat.id

	conspect_date, theme, upload_data = '', '', ''

	try:
		theme = await request(
			user_id=user_id,
			chat_id=chat_id,
			request_message='Введите тему текущего конспекта:',
			validator=validators.theme
		)
		if theme is None:
			logger.info("Name request returned None — stopping creation conspect", extra={"user_id": user_id})
			await stop_creation(chat_id)
			return
		conspect_date = await request(
			user_id=user_id,
			chat_id=chat_id,
			request_message='Введите дату текущего конспекта:',
			validator=validators.conspect_data
		)
		if conspect_date is None:
			logger.info("Surname request returned None — stopping conspect", extra={"user_id": user_id})
			await stop_creation(chat_id)
			return

		upload_data = datetime.now(ZoneInfo('Europe/Ulyanovsk'))

		if upload_data is None:
			logger.info("Group request returned None — stopping conspect", extra={"user_id": user_id})
			await stop_creation(chat_id)
			return
	except Exception as e:
		logger.exception("Unexpected error during creation flow", exc_info=e)
		await send_temporary_message(chat_id, 'Произошла ошибка при вводе данных. Попробуйте ещё раз.', delay_seconds=5)
		return
	await accept_creation(
		user_id=user_id,
		chat_id=chat_id,
		theme=theme,
		conspect_date=conspect_date,
		upload_data=upload_data
	)

async def stop_creation(chat_id):
	logger.info("stop_creation called — user cancelled the flow", extra={"chat_id": chat_id})
	await send_temporary_message(chat_id, 'Завершаю создание конспекта...', delay_seconds=10)
	raise Exception('Interrupt creation')

async def accept_creation(
		user_id=None, chat_id=None, theme=None, conspect_date=None, upload_data=None):
	logger.debug("Presenting registration confirmation to user",
	             extra={"user_id": user_id, "chat_id": chat_id,
	                    "theme": theme, "conspect_date": conspect_date, "upload_data": upload_data})
	buttons = InlineKeyboardMarkup()
	buttons.add(InlineKeyboardButton("Всё правильно", callback_data="registration_accepted"))
	buttons.add(InlineKeyboardButton("Повторить попытку", callback_data="register"))
	text = (f"Проверьте правильность данных\n\n"
			f"<blockquote><b>Тема</b>: {theme}\n"
			f"<b>Дата конспекта</b>: {conspect_date}\n"
			f"<b>Дата загрузки конспекта</b>: {upload_data}\n")
	try:
		response = await request_confirmation(
			user_id=user_id,
			chat_id=chat_id,
			text=text,
			accept_text='Всё правильно',
			decline_text='Повторить попытку',
		)
	except Exception as e:
		logger.exception("Error while asking for creation confirmation", exc_info=e)
		await send_temporary_message(chat_id, text='Произошла ошибка. Повторите позже.', delay_seconds=5)
		return
	if response is None:
		logger.info("User cancelled at confirmation step", extra={"user_id": user_id})
		await send_temporary_message(chat_id, text='Отменяю создание конспекта...', delay_seconds=5)
		return
	if response:
		logger.info("User accepted registration — proceeding to save", extra={"user_id": user_id})
		await end_creation(
			user_id=user_id,
			chat_id=chat_id,
			theme=theme,
			conspect_date=conspect_date,
			upload_data=upload_data
		)
	else:
		logger.info("User requested to repeat registration", extra={"user_id": user_id})
		await create_conspect(user_id=user_id, chat_id=chat_id)
		return
#async def end_creation(
#		):kk