"""
Прочие утилиты
"""
from code.bot.bot_instance import bot
from code.logging import logger
from code.bot.callbacks import call_factory
# Обрабатывает нажатия на кнопки, которые ничего не должны делать
# При необходимости высвечивает сообщение на экран
@bot.callback_query_handler(func=lambda call: 'empty' in call.data)
async def empty_button(call):
	logger.debug('Empty button pressed', extra={'call': call})
	data = call.data.split()
	if len(data) == 1:
		await bot.answer_callback_query(call.id)
	else:
		message = ' '.join(data[1:])
		await bot.answer_callback_query(call.id, text=message, show_alert=False)
@bot.callback_query_handler(func=call_factory.filter(action='delete').check)
async def delete_button(call):
	try:
		await bot.answer_callback_query(call.id)
	except:
		logger.exception('Failed to answer callback query for user=%s', getattr(call.from_user, 'id', None))

	try:
		await bot.delete_message(call.message.chat.id, call.message.id)
	except:
		logger.exception('Failed to delete message %s', getattr(call.message, 'id', None))
