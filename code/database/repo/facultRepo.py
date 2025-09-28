from code.database import databaseUtil
from code.database.classes import facultClass

def getAll(cursor=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return None
    try:
        cursor.execute("SELECT rowid, name FROM facults")
        output = cursor.fetchall()
        return output
    except Exception as e:
        print(e)
        return None
def getOne(cursor=None, facultID=None, name=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return None
    if isinstance(facultID, int) or isinstance(name, str):
        try:
            if isinstance(facultID, int):
                cursor.execute(f"SELECT * FROM facults WHERE rowid = {facultID}")
            elif isinstance(name, str):
                cursor.execute(f'SELECT * FROM facults WHERE name = "{name}"')
            output = cursor.fetchone()
            return output
        except Exception as e:
            print(e)
            return None
def getObject(cursor=None, facultID=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return None
    if isinstance(facultID, int):
        facultObject = facultClass.Facult(facultID=facultID, cursor=cursor)
        return facultObject
    else:
        return None
def isExists(cursor=None, name=None, facultID=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if isinstance(facultID, int) or isinstance(name, str):
        try:
            if isinstance(name, str):
                cursor.execute(f'SELECT * FROM facults WHERE name = "{name}"')
            elif isinstance(facultID, int):
                cursor.execute(f'SELECT * FROM facults WHERE rowid = {facultID}')
            output = cursor.fetchone()
            if output is not None:
                return True
            else:
                return False
        except Exception as e:
            print(e)
            return False
def add(cursor=None, name=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if not isinstance(name, str):
        return False
    if isExists(cursor=cursor, name=name):
        print(f'Facult "{name}" already exists')
        return False
    cursor.execute(f"INSERT INTO facults VALUES ('{name}')")
    return True
def remove(cursor=None, facultID=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if  isinstance(facultID, int) and isExists(cursor=cursor, facultID=facultID):
        cursor.execute(f"DELETE FROM facults WHERE rowid = {facultID}")
        return True
    return False
def removeList(cursor=None, idList=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if  isinstance(idList, list):
        for facultID in idList:
            if not isExists(cursor=cursor, facultID=facultID):
                continue
            cursor.execute(f"DELETE FROM facults WHERE rowid = {facultID}")
        return True
    return False