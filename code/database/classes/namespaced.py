from code.logging import logger
from types import SimpleNamespace
from sqlite3 import Cursor

def _cols_from_cursor(cursor:Cursor=None):
	logger.info("Trying to get column names from cursor")
	try:
		logger.info("Successfully parsed columns names")
		return [col[0] for col in cursor.description]
	except:
		errorMessage = "Cursor must be valid"
		logger.error(errorMessage)
		raise errorMessage

def rowToDict(cursor:Cursor=None, row:tuple=None):
	try:
		cols = _cols_from_cursor(cursor)
		return dict(zip(cols, row))
	except Exception as e:
		logger.error(e)
		raise e

def getRowNamespaces(cursor:Cursor=None, row:tuple=None):
	try:
		return SimpleNamespace(**rowToDict(cursor, row))
	except Exception as e:
		logger.error(e)
		return None