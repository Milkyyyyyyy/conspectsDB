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
	"""

	:param cursor: Курсор, полученный из метода из queries.py
	:param row: Кортеж строки, полученный из метода из queries.py
	:return: namespaces

	Пример
	response, cursor = get(...) # Здесь ты, например, получил какую-то строку из датабазы
	# response - это основной ответ из функции get, например кортеж строки
	# cursor - возвращаемый курсор
	coolInterface = getRowNamespaces(cursor=cursor, row=row)

	# И теперь ты можешь получать все значения вот таким образом:
	coolInterface.rowid
	coolInterface.name
	coolInterface.someVariables
	"""

	try:
		return SimpleNamespace(**rowToDict(cursor, row))
	except Exception as e:
		logger.error(e)
		return None