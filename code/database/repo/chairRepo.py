from code.database.repo import facultRepo
from code.database.repo import queries
from code.database.classes import chairClass

TABLE_NAME = 'chairs'

def getAll(cursor=None):
    return queries.getAll(cursor=cursor, tableName=TABLE_NAME)
def get(cursor=None, input=None):
   return queries.get(cursor=cursor, tableName=TABLE_NAME, input=input)
# def getAllWithFacult(cursor=None, facultID=None):
#     if not databaseUtil.checkCursor(cursor):
#         print("Set cursor variable")
#         return None
#     if not isinstance(facultID, int):
#         return None
#     if facultRepo.isExists(cursor=cursor, facultID=facultID):
#         cursor.execute(f"SELECT * FROM chairs WHERE facult_id = {facultID}")
#         output = cursor.fetchall()
#         return output
#     else:
#         return None
def getObject(cursor=None, chairID=None):
    return chairClass.Chair(get(cursor=cursor, input=chairID))
def isExists(cursor=None, input=None):
    return queries.isExists(cursor=cursor, tableName=TABLE_NAME, input=input)
def add(cursor=None, name=None, facultID=None):
    if queries.isExists(cursor=cursor, tableName=TABLE_NAME, input=name):
        return False
    return queries.add(cursor=cursor, tableName=TABLE_NAME, input = [facultID, name])
def remove(cursor=None, chairID=None):
    return queries.remove(cursor=cursor, tableName=TABLE_NAME, input = chairID)
def removeList(cursor=None, idList=None):
    return queries.removeList(cursor=cursor, tableName=TABLE_NAME, input = idList)
