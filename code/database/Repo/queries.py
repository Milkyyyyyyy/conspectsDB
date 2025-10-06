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
def getAll(cursor=None, tableName=None):
    logger.info(f'Getting all rows in "{tableName}"...')
    try:
        cursor.execute(f"SELECT rowid, *  FROM {tableName}")
        output = cursor.fetchall()
        if output is None:
            Exception(f"{tableName} table has no rows")
        logger.info("Successfully fetched all rows")
        return output
    except Exception as e:
        logger.exception(e)
        return None
@require_cursor
def get(cursor=None, tableName=None, input=None):
    logger.info(f'Getting row from "{tableName}" with input={input}...')
    try:
        if isinstance(input, int):
            cursor.execute(f"SELECT rowid, *  FROM {tableName} WHERE rowid = {input}")
        elif isinstance(input, str):
            cursor.execute(f'SELECT rowid, *  FROM {tableName} WHERE name = "{input}"')
        else:
            Exception("Invalid input type")
        output = cursor.fetchone()
        if output is None:
            Exception(f"Row not exists")
        logger.info("Successfully fetched row")
        return output
    except Exception as e:
        logger.exception(e)
        return None
@require_cursor
def isExists(cursor=None, tableName=None, input=None):
    logger.info(f'Check if "{tableName}" entry exists...')
    try:
        if isinstance(input, int):
            cursor.execute(f"SELECT rowid, *  FROM {tableName} WHERE rowid = {input}")
        elif isinstance(input, str):
            cursor.execute(f'SELECT rowid, *  FROM {tableName} WHERE name = "{input}"')
        else:
            Exception("Invalid input type")
        output = cursor.fetchone()
        logger.info("Successfully fetched row")
        if output is not None:
            logger.info(f'Row with {input} exists')
            return True
        else:
            logger.info(f'Row with {input} NOT exists')
            return False
    except Exception as e:
        logger.exception(e)
        return None
@require_cursor
def remove(cursor=None, tableName=None, input=None):
    logger.info(f'Removing row from "{tableName}" with input={input}...')
    try:
        if not isExists(cursor=cursor, tableName=tableName, input=input):
            Exception(f"Row not exists")
        elif isinstance(input, int):
            cursor.execute(f"DELETE FROM {tableName} WHERE rowid = {input}")
            logger.info("Successfully removed row")
            return True
        elif isinstance(input, str):
            cursor.execute(f'DELETE FROM {tableName} WHERE name = "{input}"')
            logger.info("Successfully removed row with")
            return True
        else:
            Exception("Invalid input type")
    except Exception as e:
        logger.exception(e)
        return False
@require_cursor
def removeList(cursor=None, tableName=None, input=None):
    logger.info("Removing many rows from list...")
    try:
        if not isinstance(input, list):
            Exception("Invalid input type")
        for item in input:
            remove(cursor=cursor, tableName=tableName, input=item)
        logger.info("Successfully removed many rows")
        return True
    except Exception as e:
        logger.exception(e)
        return False
def add(cursor=None, tableName=None, input=None):
    logger.info(f'Adding row to "{tableName}" with input={input}...')
    try:
        if isinstance(input, list) and len(input) >= 1:
            val = ""
            for item in input:
                valConverted = None
                if isinstance(item, str):
                    valConverted = '"' + item + '"'
                elif isinstance(item, int) or isinstance(item, float):
                    valConverted = str(item)
                else: continue
                if val == "":
                    val += valConverted
                    continue
                else:
                    val += ", " + valConverted
            cursor.execute(f"INSERT INTO {tableName} VALUES ({val})")
            logger.info("Successfully added row")
            return True
        else:
            Exception("Invalid input type or list size")
    except Exception as e:
        logger.exception(e)
        return False
