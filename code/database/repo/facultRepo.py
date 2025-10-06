from code.database.repo import queries
from code.database.classes import facultClass

TABLE_NAME = 'facults'
def getAll(cursor=None):
    return queries.getAll(cursor=cursor, tableName=TABLE_NAME)

def get(cursor=None, input=None):
   return queries.get(cursor=cursor, tableName=TABLE_NAME, input=input)
def getObject(cursor=None, facultID=None):
    return facultClass.Facult(get(cursor=cursor, input=facultID))
def isExists(cursor=None, input=None):
    return queries.isExists(cursor=cursor, tableName=TABLE_NAME, input=input)

def add(cursor=None, name=None):
    if queries.isExists(cursor=cursor, tableName=TABLE_NAME, input=name):
        return None
    return queries.add(cursor=cursor, tableName=TABLE_NAME, input=[name])

def remove(cursor=None, facultID=None):
    return queries.remove(cursor=cursor, tableName=TABLE_NAME, input=facultID)
def removeList(cursor=None, IDList=None):
    return queries.removeList(cursor=cursor, tableName=TABLE_NAME, input=IDList)