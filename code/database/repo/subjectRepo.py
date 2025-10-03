from code.database import databaseUtil
from code.database.repo import directionRepo
from code.database.repo import queries
from code.database.classes import subjectClass

TABLE_NAME = 'subjects'
def getAll(cursor=None):
    return queries.getAll(cursor=cursor, tableName=TABLE_NAME)
def get(cursor=None, input=None):
   return queries.get(cursor=cursor, tableName=TABLE_NAME, input=input)
def getObject(cursor=None, subjectID=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return None
    if not isinstance(subjectID, int):
        return None
    subjectObject = subjectClass.Subject(cursor=cursor, subjectID=subjectID)
    return subjectObject
def isExists(cursor=None, subjectID=None, name=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if not isinstance(subjectID, int) and not isinstance(name, str):
        return False
    output = None
    if isinstance(subjectID, int):
        output = get(cursor=cursor, subjectID=subjectID)
    elif isinstance(name, str):
        output = get(cursor=cursor, name=name)
    if output is not None:
        return True
    else:
        return False
def add(cursor=None, directionID=None, name=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if isExists(cursor=cursor, name=name) or not directionRepo.isExists(cursor=cursor, directionID=directionID):
        print("Subject already exists or direction not exists")
        return False
    if isinstance(directionID, int) and isinstance(name, str):
        cursor.execute(f'INSERT INTO subjects VALUES ({directionID}, "{name}")')
        return True
    else:
        return False
def remove(cursor=None, subjectID=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if isinstance(subjectID, int) and isExists(subjectID=subjectID):
        cursor.execute(f"DELETE FROM subjects WHERE rowid = {subjectID}")
        return True
    else:
        return False
def removeList(cursor=None, idList=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if isinstance(idList, list):
        for subjectID in idList:
            cursor.execute(f"DELETE FROM subjects WHERE rowid = {subjectID}")
        return True
    return False
