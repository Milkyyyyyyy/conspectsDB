import logging
import sqlite3
import functools

# TODO
# [ ] Доделать логи и новую архитектуру

CONSPECTS_DB = 'files/database/conspects.db'

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename='logs/app.log',
    level=logging.DEBUG,
    format='[%(asctime)s] - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
def connectDB():
    logger.info('Connecting to database...')
    try:
        output = sqlite3.connect(CONSPECTS_DB)
        logger.info('Successfully connected to database.')
        return output
    except sqlite3.Error as e:
        logger.error(e)
        return None
def checkCursor(cursor):
    if isinstance(cursor, sqlite3.Cursor):
        return True
    return False
def require_cursor(func):
    @functools.wraps(func)
    def wrapper(cursor, *args, **kwargs):
        if not checkCursor(cursor):
            Exception("Invalid cursor")
        return func(cursor, *args, **kwargs)
    return wrapper

@require_cursor
def getAll(cursor=None, tableName=None, value=None, valueName=None):
    logger.info(f'Getting all rows in "{tableName}"...')

    valuesTuple = ()
    sql_query = f"SELECT rowid, * FROM {tableName}"
    if value is not None and valueName is not None:
        sql_query += f" WHERE {valueName} = ?"
        valuesTuple = (value,)

    try:
        cursor.execute(sql_query, valuesTuple)
        output = cursor.fetchall()
        logger.info("Successfully fetched all existing rows")
        return output
    except Exception as e:
        logger.exception(e)
        return None
@require_cursor
def get(cursor=None, tableName=None, input=None, valueName="rowid"):
    logger.info(f'Getting row from "{tableName}" with input={input}...')

    if input is None:
        logger.error("Invalid input type")
        return False
    sql_query = f"SELECT rowid, * FROM {tableName} WHERE {valueName} = ?"

    try:
        cursor.execute(sql_query, (input, ))
        output = cursor.fetchone()
        logger.info("Successfully fetched row")
        return output
    except Exception as e:
        logger.exception(e)
        return None
@require_cursor
def isExists(cursor=None, tableName=None, input=None, valueName="rowid"):
    logger.info(f'Check if "{tableName}" entry exists...')
    sql_query = f'SELECT rowid, *  FROM {tableName} WHERE {valueName} = ?'
    try:
        cursor.execute(sql_query, (input, ))
        output = cursor.fetchone()
        logger.info("Successfully fetched row")
        if output is not None:
            logger.info(f"Row with {valueName}={input} exists")
            return True
        else:
            logger.info(f"Row with {valueName}={input} NOT exists")
            return False
    except Exception as e:
        logger.exception(e)
        return None
@require_cursor
def remove(cursor=None, tableName=None, ID=None):
    logger.info(f'Removing row from "{tableName}" with ID={ID}...')

    if not isExists(cursor=cursor, tableName=tableName, input=ID):
        logger.error(f"Row {ID} not exists")
        return False
    sql_query = f"DELETE FROM {tableName} WHERE rowid = ?"

    try:
        if isinstance(ID, int):
            cursor.execute(sql_query, (ID,))
            logger.info("Successfully removed row")
            return True
        else:
            Exception("Invalid input type")
    except Exception as e:
        logger.exception(e)
        return False
@require_cursor
def removeList(cursor=None, tableName=None, input=None):
    logger.info("Removing many rows from list...")

    if not isinstance(input, list) or len(input) == 0:
        logger.error("Invalid input type or empty list")
        return False

    try:
        for item in input:
            remove(cursor=cursor, tableName=tableName, ID=item)
        logger.info("Successfully removed many rows")
        return True
    except Exception as e:
        logger.exception(e)
        return False
def add(cursor=None, tableName=None, input=None):
    logger.info(f'Adding row to "{tableName}" with input={input}...')
    if not isinstance(input, list) or len(input) == 0:
        logger.error("Invalid input type or empty list")
        return False

    placeholders = ['?'] * len(input)
    placeholders_str = "(" + ", ".join(placeholders) + ")"

    sql_query = f"INSERT INTO {tableName} VALUES {placeholders_str}"

    try:
        cursor.execute(sql_query, input)
        logger.info("Successfully added row")
        return True
    except Exception as e:
        logger.exception(e)
        return False
