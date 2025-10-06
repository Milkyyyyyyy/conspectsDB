from code.database.repo import directionRepo
from code.database.repo import queries
from code.database.classes import subjectClass

TABLE_NAME = 'subjects'
def getAll(cursor=None, value=None, valueName=None):
    return queries.getAll(cursor=cursor, tableName=TABLE_NAME, value=value, valueName=valueName)
def get(cursor=None, ID=None, name=None):
   if not ID is None:
       return queries.get(cursor=cursor, tableName=TABLE_NAME, input=ID)
   elif not name is None:
       return queries.get(cursor=cursor, tableName=TABLE_NAME, input=name, valueName='name')
def getObject(cursor=None, subjectID=None):
    return subjectClass.Subject(get(cursor=cursor, ID=subjectID))
def isExists(cursor=None, input=None, valueName="rowid"):
    return queries.isExists(cursor=cursor, tableName=TABLE_NAME, input=input, valueName=valueName)
def add(cursor=None, directionID=None, name=None):
    if isExists(cursor=cursor, input=directionID):
        return False
    return queries.add(cursor=cursor, tableName=TABLE_NAME, input=[directionID, name])
def remove(cursor=None, input=None):
    return queries.remove(cursor=cursor, tableName=TABLE_NAME, input=input)
def removeList(cursor=None, idList=None):
    return queries.removeList(cursor=cursor, tableName=TABLE_NAME, input=idList)
