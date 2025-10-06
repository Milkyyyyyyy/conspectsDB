from code.database.repo import directionRepo
from code.database.repo import queries
from code.database.classes import subjectClass

TABLE_NAME = 'subjects'
def getAll(cursor=None):
    return queries.getAll(cursor=cursor, tableName=TABLE_NAME)
def get(cursor=None, input=None):
   return queries.get(cursor=cursor, tableName=TABLE_NAME, input=input)
def getObject(cursor=None, subjectID=None):
    return subjectClass.Subject(get(cursor=cursor, input=subjectID))
def isExists(cursor=None, input=None):
    return queries.isExists(cursor=cursor, tableName=TABLE_NAME, input=input)
def add(cursor=None, directionID=None, name=None):
    if isExists(cursor=cursor, input=name):
        return False
    return queries.add(cursor=cursor, tableName=TABLE_NAME, input=[directionID, name])
def remove(cursor=None, input=None):
    return queries.remove(cursor=cursor, tableName=TABLE_NAME, input=input)
def removeList(cursor=None, idList=None):
    return queries.remove(cursor=cursor, tableName=TABLE_NAME, input=idList)
