from logging import exception

from code.database.databaseUtil import checkCursor
import functools

def require_cursor(func):
    @functools.wraps(func)
    def wrapper(cursor, *args, **kwargs):
        if not checkCursor(cursor):
            return None
        return func(cursor, *args, **kwargs)
    return wrapper

@require_cursor
def getAll(cursor=None, tableName=None):
    try:
        cursor.execute(f"SELECT rowid, *  FROM {tableName}")
        output = cursor.fetchall()
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
            exception("Invalid input type")
        output = cursor.fetchone()
        return output
    except Exception as e:
        print(e)
        return None
