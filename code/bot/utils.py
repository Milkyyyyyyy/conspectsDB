from code.logging import logger
from code.database.queries import connectDB, isExists
import asyncio

# Удаляет сообщение через некоторое количество времени
async def delete_message_after_delay(bot, chat_id, message_id, delay_seconds=10):
	logger.debug(f'Delayed message deletion after {delay_seconds} seconds.')
	await asyncio.sleep(delay_seconds)
	try:
		await bot.delete_message(chat_id, message_id)
		logger.debug(f'Message {message_id} deleted')
	except Exception as e:
		logger.warning(f'Failed to delete message {message_id} in chat {chat_id}\n {e}')
		pass
async def is_user_exists(user_id):
	async with connectDB() as database:
		logger.debug(database)
		user_id = str(user_id)
		isUserExists = await isExists(database=database, table="USERS", filters={"telegram_id": user_id})
	return isUserExists