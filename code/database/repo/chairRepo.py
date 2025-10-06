from code.database.repo import queries
from code.database.classes import chairClass

TABLE_NAME = 'chairs'

def getAll(cursor=None, value=None, valueName=None):
    return queries.getAll(cursor=cursor, tableName=TABLE_NAME, value=value, valueName=valueName)
def get(cursor=None, ID=None, name=None):
    if not ID is None:
        return queries.get(cursor=cursor, tableName=TABLE_NAME, input=ID)
    elif not name is None:
        return queries.get(cursor=cursor, tableName=TABLE_NAME, input=name, valueName="name")
def getObject(cursor=None, chairID=None):
    return chairClass.Chair(get(cursor=cursor, ID=chairID))
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
