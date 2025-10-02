from code.database import databaseUtil
from code.database.repo import queries
from code.database.classes import facultClass

TABLE_NAME = 'facults'
def getAll(cursor=None):
    return queries.getAll(cursor=cursor, tableName=TABLE_NAME)

def get(cursor=None, input=None):
   return queries.get(cursor=cursor, tableName=TABLE_NAME, input=input)
def getObject(cursor=None, facultID=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return None
    if isinstance(facultID, int):
        facultObject = facultClass.Facult(facultID=facultID, cursor=cursor)
        return facultObject
    else:
        return None
def isExists(cursor=None, input=None):
    return queries.isExists(cursor=cursor, tableName=TABLE_NAME, input=input)

def add(cursor=None, name=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if not isinstance(name, str):
        return False
    if isExists(cursor=cursor, input=name):
        print(f'Facult "{name}" already exists')
        return False
    cursor.execute(f"INSERT INTO facults VALUES ('{name}')")
    return True
def remove(cursor=None, facultID=None):
    return queries.remove(cursor=cursor, tableName=TABLE_NAME, input=facultID)
def removeList(cursor=None, idList=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if  isinstance(idList, list):
        for facultID in idList:
            if not isExists(cursor=cursor, input=facultID):
                continue
            cursor.execute(f"DELETE FROM facults WHERE rowid = {facultID}")
        return True
    return False