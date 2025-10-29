import aiosqlite

from code.database.config import CONSPECTS_DB
from code.logging import logger
# TODO Поправить логи
# Контекстный менеджер для асинхронного подключения к датабазе
class AsyncDBConnection:
	def __init__(self, db_path):
		self.db_path = db_path
		self.conn = None

	async def __aenter__(self):
		self.conn = await aiosqlite.connect(self.db_path)
		self.conn.row_factory = aiosqlite.Row
		return self.conn

	async def __aexit__(self, exc_type, exc_val, exc_tb):
		if exc_type is None:
			await self.conn.commit()
		else:
			await self.conn.rollback()
		await self.conn.close()


def connectDB():
	logger.debug('Async connecting to database...')
	output = AsyncDBConnection(CONSPECTS_DB)
	logger.debug(output)
	return output
