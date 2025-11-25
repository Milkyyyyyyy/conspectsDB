import aiosqlite

from code.database.config import CONSPECTS_DB
from code.logging import logger
# Контекстный менеджер для асинхронного подключения к датабазе
class AsyncDBConnection:
	def __init__(self, db_or_conn):
		if isinstance(db_or_conn, aiosqlite.Connection):
			self.conn = db_or_conn
			self.db_path = None
			self.owns_connection = False
		else:
			self.db_path = db_or_conn
			self.conn = None
			self.owns_connection = True

	async def __aenter__(self):
		if self.owns_connection:
			self.conn = await aiosqlite.connect(self.db_path)
			self.conn.row_factory = aiosqlite.Row
		return self.conn

	async def __aexit__(self, exc_type, exc_val, exc_tb):
		if self.owns_connection:
			if exc_type is None:
				await self.conn.commit()
			else:
				await self.conn.rollback()
			await self.conn.close()


def connect_db(db_or_connection=None):
	logger.debug('Async connecting to database...')
	if db_or_connection is None or not isinstance(db_or_connection, aiosqlite.Connection):
		db_or_connection = CONSPECTS_DB
	output = AsyncDBConnection(db_or_connection)
	logger.debug(output)
	return output
