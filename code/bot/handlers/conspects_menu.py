from code.bot.bot_instance import bot
from code.logging import logger
from code.bot.states import MainStates
from code.bot.handlers.main_menu import main_menu

# TODO Переделать структуру callback'ов

@bot.callback_query_handler(func=lambda call: call.data == 'upload_conspect')
async def call_upload_conspect(call):
	try:
		await bot.answer_callback_query(call.id)
	except Exception as e:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))
	await upload_conspect(user_id=call.from_user.id, chat_id=call.message.chat.id)

async def upload_conspect(user_id, chat_id):
	await bot.set_state(user_id=user_id, chat_id=chat_id, state=MainStates.conspect_upload_state)
	await bot.send_message(chat_id, 'Заглушка')

	# Здесь  нужно получить список всех subjects из датабазы
	# ВАЖНО(!!!!).
	# В поле direction_id в subjects хранится не один ID direction, а список (то есть просто разные ID через пробел)
	
	await main_menu(user_id, chat_id)

