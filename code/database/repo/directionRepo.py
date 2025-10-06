from code.database.repo import chairRepo
from code.database.repo import queries
from code.database.classes import directionClass
TABLE_NAME = 'directions'
def getAll(cursor=None, value=None, valueName=None):
    return queries.getAll(cursor=cursor, tableName=TABLE_NAME, value=value, valueName=valueName)
def get(cursor=None, ID=None, name=None):
    if not ID is None:
        return queries.get(cursor=cursor, tableName=TABLE_NAME, input=ID)
    elif not name is None:
        return queries.get(cursor=cursor, tableName=TABLE_NAME, input=name, valueName='name')
def getObject(cursor=None, directionID=None):
    return directionClass.Direction(get(cursor=cursor, ID=directionID))
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