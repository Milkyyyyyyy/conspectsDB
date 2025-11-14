from code.bot.bot_instance import bot
from code.bot.callbacks import call_factory
from code.bot.handlers.main_menu import main_menu
from code.bot.states import MainStates
from code.bot.utils import safe_edit_message
from code.logging import logger


@bot.callback_query_handler(func=call_factory.filter(area='conspects_menu').check)
async def callback_handler(call):
	logger.debug('Handle callback in conspects menu...')
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
			await upload_conspect(user_id=user_id, chat_id=chat_id, previous_message_id=message_id)


async def upload_conspect(user_id, chat_id, previous_message_id):
	await bot.set_state(user_id=user_id, chat_id=chat_id, state=MainStates.conspect_upload_state)
	await safe_edit_message(
		previous_message_id=previous_message_id,
		chat_id=chat_id,
		user_id=user_id,
		text='Заглушка...',
	)

	# Здесь  нужно получить список всех subjects из датабазы
	# ВАЖНО(!!!!).
	# В поле direction_id в subjects хранится не один ID direction, а список (то есть просто разные ID через пробел)

	await main_menu(user_id, chat_id)
