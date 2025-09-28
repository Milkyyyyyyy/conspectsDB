from code.database import databaseUtil
from code.database.repo import directionRepo
from code.database.classes import subjectClass

def getAll(cursor=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return None
    cursor.execute('SELECT rowid, direction_id, name FROM subjects')
    output = cursor.fetchall()
    return output
def getOne(cursor=None, subjectID=None, name=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return None
    if not isinstance(subjectID, int) and not isinstance(name, str):
        return None
    if isinstance(subjectID, int):
        cursor.execute(f"SELECT rowid, direction_id, name FROM subjects WHERE rowid = {subjectID}")
    elif isinstance(name, str):
        cursor.execute(f'SELECT rowid, direction_id, name FROM subjects WHERE name = "{name}"')
    output = cursor.fetchone()
    return output

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
        output = getOne(cursor=cursor, subjectID=subjectID)
    elif isinstance(name, str):
        output = getOne(cursor=cursor, name=name)
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
