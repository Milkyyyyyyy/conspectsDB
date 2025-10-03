import logging
import sqlite3
import functools

# TODO
# [ ] Доделать логи и новую архитектуру

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename='logs/app.log',
    level=logging.DEBUG,
    format='[%(asctime)s] - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

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
    try:
        cursor.execute(f"SELECT rowid, *  FROM {tableName}")
        output = cursor.fetchall()
        if output is None:
            Exception(f"{tableName} table has no rows")
        return output
    except Exception as e:
        print(e)
        return None
@require_cursor
def get(cursor=None, tableName=None, input=None):
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
        return output
    except Exception as e:
        print(e)
        return None
@require_cursor
def isExists(cursor=None, tableName=None, input=None):
    try:
        if isinstance(input, int):
            cursor.execute(f"SELECT rowid, *  FROM {tableName} WHERE rowid = {input}")
        elif isinstance(input, str):
            cursor.execute(f'SELECT rowid, *  FROM {tableName} WHERE name = "{input}"')
        else:
            Exception("Invalid input type")
        output = cursor.fetchone()
        if output is not None:
            return True
        else:
            return False
    except Exception as e:
        print(e)
        return None
@require_cursor
def remove(cursor=None, tableName=None, input=None):
    try:
        if not isExists(cursor=cursor, tableName=tableName, input=input):
            return False
        elif isinstance(input, int):
            cursor.execute(f"DELETE FROM {tableName} WHERE rowid = {input}")
            return True
        elif isinstance(input, str):
            cursor.execute(f'DELETE FROM {tableName} WHERE name = "{input}"')
            return True
        else:
            Exception("Invalid input type")
    except Exception as e:
        print(e)
        return False
@require_cursor
def removeList(cursor=None, tableName=None, input=None):
    try:
        if not isinstance(input, list):
            Exception("Invalid input type")
        for item in input:
            remove(cursor=cursor, tableName=tableName, input=item)
        return True
    except Exception as e:
        print(e)
        return False
def add(cursor=None, tableName=None, input=None):
    try:
        if isinstance(input, list) and len(input) >= 1:
            cursor.execute(f"INSERT INTO {tableName} VALUES ({', '.join(input)})")
            return True
        else:
            Exception("Invalid input type or list size")
    except Exception as e:
        print(e)
        return False
