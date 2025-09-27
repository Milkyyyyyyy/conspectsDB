from code.database.databaseProcessing import databaseUtil
from code.database.databaseProcessing.Repo import chairRepo
from code.database import DirectionClass

def getAll(cursor=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return None
    cursor.execute('SELECT rowid, chair_id, name FROM directions')
    output = cursor.fetchall()
    return output
def getOne(cursor=None, directionID = None, directionName=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return None
    if not isinstance(directionID, int) and not isinstance(directionName, str):
        return None
    if isinstance(directionID, int):
        cursor.execute(f"SELECT rowid, chair_id, name FROM directions WHERE rowid = {directionID}")
    elif isinstance(directionName, str):
        cursor.execute(f'SELECT rowid, chair_id, name FROM directions WHERE name = "{directionName}"')
    output = cursor.fetchone()
    return output
def getObject(cursor=None, directionID=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return None
    if not isinstance(directionID, int):
        return None
    directionObject = DirectionClass.Direction(cursor=cursor, directionID=directionID)
    return directionObject
def isExists(cursor=None, name=None, directionID=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if not isinstance(name, str) and not isinstance(directionID, int):
        return False
    if isinstance(directionID, int):
        cursor.execute(f"SELECT * FROM directions WHERE rowid = {directionID}")
    elif isinstance(name, str):
        cursor.execute(f'SELECT * FROM directions WHERE name = "{name}"')
    output = cursor.fetchone()
    if output is not None:
        return True
    else:
        return False
def add(cursor=None, directionName=None, chairID=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if not isinstance(directionName, str) or not isinstance(chairID, int):
        print("Direction name must be string and chairID must be integer")
        return False
    if isExists(cursor=cursor, name=directionName) or not chairRepo.isExists(cursor=cursor, chairID=chairID):
        print("Direction name already exists or chairID does not exist")
        return False
    cursor.execute(f'INSERT INTO directions VALUES ({chairID}, "{directionName}")')
def remove(cursor=None, directionID=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if isinstance(directionID, int) and isExists(cursor=cursor, directionID=directionID):
        cursor.execute(f"DELETE FROM directions WHERE rowid = {directionID}")
        return True
    return False
def removeList(cursor=None, directionIDList=None):
    if not databaseUtil.checkCursor(cursor):
        print("Set cursor variable")
        return False
    if not isinstance(directionIDList, list):
        return False
    for directionID in directionIDList:
        cursor.execute(f"DELETE FROM directions WHERE rowid = {directionID}")
    return True