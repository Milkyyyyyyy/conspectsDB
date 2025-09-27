from code.database.databaseProcessing import databaseUtil
from code.database.databaseProcessing.Repo import directionRepo
from code.database import SubjectClass

def getAll(cursor=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return None
    cursor.execute('SELECT rowid, direction_id, name FROM subjects')
    output = cursor.fetchall()
    return output
def getOne(cursor=None, subjectID=None, subjectName=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return None
    if not isinstance(subjectID, int) and not isinstance(subjectName, str):
        return None
    if isinstance(subjectID, int):
        cursor.execute(f"SELECT rowid, direction_id, name FROM subjects WHERE rowid = {subjectID}")
    elif isinstance(subjectName, str):
        cursor.execute(f'SELECT rowid, direction_id, name FROM subjects WHERE name = "{subjectName}"')
    output = cursor.fetchone()
    return output

def getObject(cursor=None, subjectID=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return None
    if not isinstance(subjectID, int):
        return None
    subjectObject = SubjectClass.Subject(cursor=cursor, subjectID=subjectID)
    return subjectObject
def isExists(cursor=None, subjectID=None, subjectName=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if not isinstance(subjectID, int) and not isinstance(subjectName, str):
        return False
    output = None
    if isinstance(subjectID, int):
        output = getOne(cursor=cursor, subjectID=subjectID)
    elif isinstance(subjectName, str):
        output = getOne(cursor=cursor, subjectName=subjectName)
    if output is not None:
        return True
    else:
        return False
def add(cursor=None, directionID=None, subjectName=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if isExists(cursor=cursor, subjectName=subjectName) or not directionRepo.isExists(cursor=cursor, directionID=directionID):
        print("Subject already exists or direction not exists")
        return False
    if isinstance(directionID, int) and isinstance(subjectName, str):
        cursor.execute(f'INSERT INTO subjects VALUES ({directionID}, "{subjectName}")')
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
def removeList(cursor=None, subjectIDList=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if isinstance(subjectIDList, list):
        for subjectID in subjectIDList:
            cursor.execute(f"DELETE FROM subjects WHERE rowid = {subjectID}")
        return True
    return False
