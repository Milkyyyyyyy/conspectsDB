from code.database.databaseProcessing import databaseUtil
from code.database.databaseProcessing.Repo import facultRepo
from code.database import ChairClass

def getAll(cursor=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return None
    cursor.execute(f'SELECT rowid, facult_id, name  FROM chairs')
    output = cursor.fetchall()
    return output
def getAllWithFacult(cursor=None, facultID=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return None
    if not isinstance(facultID, int):
        return None
    if facultRepo.isExists(cursor=cursor, facultID=facultID):
        cursor.execute(f"SELECT * FROM chairs WHERE facult_id = {facultID}")
        output = cursor.fetchall()
        return output
    else:
        return None
def getOne(cursor=None, chairID=None, chairName=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return None
    if not isinstance(chairID, int) and not isinstance(chairName, str):
        return None
    if isinstance(chairID, int):
        cursor.execute(f"SELECT rowid, facult_id, name FROM chairs WHERE rowid = {chairID}")
    elif isinstance(chairName, str):
        cursor.execute(f'SELECT rowid, facult_id, name FROM chairs WHERE name = "{chairName}"')
    output = cursor.fetchone()
    return output
def getObject(cursor=None, chairID=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return None
    if not isinstance(chairID, int):
        return None
    chairObject = ChairClass.Chair(cursor=cursor, chairID=chairID)
    return chairObject
def isExists(cursor=None, name=None, chairID=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return None
    # Checks if name_or_id is not str or int, or if name_or_id is None
    if (not isinstance(name, str) and not isinstance(chairID, int)) or not isinstance(cursor, sqlite3.Cursor):
        return False
    # If name_or_id is integer, then search by rowid
    if isinstance(chairID, int):
        cursor.execute(f'SELECT * FROM chairs WHERE rowid = {chairID}')
    # Else if name_or_id is string, then search by name
    elif isinstance(name, str):
        cursor.execute(f'SELECT * FROM chairs WHERE name = "{name}"')

    output = cursor.fetchone()
    if output is not None:
        return True
    else:
        return False
def add(cursor=None, chairName=None, facultID=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if not isinstance(chairName, str) or not isinstance(facultID, int):
        return False
    if isExists(cursor=cursor, name=chairName) or not isFacultExists(cursor=cursor, facultID=facultID):
        return False
    cursor.execute(f"INSERT INTO chairs VALUES ({facultID}, '{chairName}')")
    return True
def remove(cursor=None, chairID=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if isinstance(chairID, int) and isExists(cursor=cursor, chairID=chairID):
        cursor.execute(f"DELETE FROM chairs WHERE rowid = {chairID}")
        return True
    return False
def removeList(cursor=None, chairIDList=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if not isinstance(chairIDList, list):
        return False
    for chair_id in chairIDList:
        cursor.execute(f"DELETE FROM chairs WHERE rowid = {chair_id}")
    return True
