from code.database.repo import chairRepo
from code.database.repo import queries
from code.database.classes import directionClass
TABLE_NAME = 'directions'
def getAll(cursor=None):
    return queries.getAll(cursor=cursor, tableName=TABLE_NAME)
def get(cursor=None, input=None):
   return queries.get(cursor=cursor, tableName=TABLE_NAME, input=input)
def getObject(cursor=None, directionID=None):
    return directionClass.Direction(get(cursor=cursor, input=directionID))
def isExists(cursor=None, input=None):
    return queries.isExists(cursor=cursor, tableName=TABLE_NAME, input=input)
def add(cursor=None, name=None, chairID=None):
    if isExists(cursor=cursor, input=name) or (not chairRepo.isExists(cursor=cursor, input=chairID)):
        return False
    return queries.add(cursor=cursor, tableName=TABLE_NAME, input=[chairID, name])
def remove(cursor=None, directionID=None):
    return queries.remove(cursor=cursor, tableName=TABLE_NAME, input=directionID)
def removeList(cursor=None, idList=None):
    return queries.remove(cursor=cursor, tableName=TABLE_NAME, input=idList)