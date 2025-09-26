from code.database import FacultClass, SubjectClass, ChairClass, DirectionClass
import sqlite3
CONSPECTS_DB = 'files/database/conspects.db'


def checkCursor(cursor=None):
    return isinstance(cursor, sqlite3.Cursor)

# TODO
# 1. Доделать все проверки и архитектуру

# ======== Methods ========
# -------- Facults --------
def getAllFacults(cursor=None):
    if not checkCursor(cursor):
        print("Set cursor variable")
        return None
    try:
        cursor.execute("SELECT rowid, name FROM facults")
        output = cursor.fetchall()
        return output
    except Exception as e:
        print(e)
        return None
def getFacult(cursor=None, facultID=None, facultName=None):
    if not checkCursor(cursor):
        print("Set cursor variable")
        return None
    if isinstance(facultID, int) or isinstance(facultName, str):
        try:
            if isinstance(facultID, int):
                cursor.execute(f"SELECT * FROM facults WHERE rowid = {facultID}")
            elif isinstance(facultName, str):
                cursor.execute(f'SELECT * FROM facults WHERE name = "{facultName}"')
            output = cursor.fetchone()
            return output
        except Exception as e:
            print(e)
            return None
def getFacultObject(cursor=None, facultID=None):
    if not checkCursor(cursor):
        print("Set cursor variable")
        return None
    if isinstance(facultID, int):
        facultObject = FacultClass.Facult(facultID=facultID, cursor=cursor)
        return facultObject
    else:
        return None
def isFacultExists(cursor=None, name=None, facultID=None):
    if not checkCursor(cursor):
        print("Set cursor variable")
        return False
    if isinstance(facultID, int) or isinstance(name, str):
        try:
            if isinstance(name, str):
                cursor.execute(f'SELECT * FROM facults WHERE name = "{name}"')
            elif isinstance(facultID, int):
                cursor.execute(f'SELECT * FROM facults WHERE rowid = {facultID}')
            output = cursor.fetchone()
            if output is not None:
                return True
            else:
                return False
        except Exception as e:
            print(e)
            return False
def addFacult(cursor=None, facultName=None):
    if not checkCursor(cursor):
        print("Set cursor variable")
        return False
    if not isinstance(facultName, str):
        return False
    if isFacultExists(cursor=cursor, name=facultName):
        print('Facult already exists')
        return False
    cursor.execute(f"INSERT INTO facults VALUES ('{facultName}')")
    return True
def removeFacult(cursor=None, facultID=None):
    if not checkCursor(cursor):
        print("Set cursor variable")
        return False
    if  isinstance(facultID, int) and isFacultExists(cursor=cursor, facultID=facultID):
        cursor.execute(f"DELETE FROM facults WHERE rowid = {facultID}")
        return True
    return False
def removeFacultsList(cursor=None, facultIDList=None):
    if not checkCursor(cursor):
        print("Set cursor variable")
        return False
    if  isinstance(facultIDList, list):
        for facultID in facultIDList:
            cursor.execute(f"DELETE FROM facults WHERE rowid = {facultID}")
        return True
    return False

# ------- Chairs --------
def getAllChairs(cursor=None):
    if not checkCursor(cursor):
        print("Set cursor variable")
        return None
    cursor.execute(f'SELECT rowid, facult_id, name  FROM chairs')
    output = cursor.fetchall()
    return output
def getAllChairsOfFacult(cursor=None, facultID=None):
    if not checkCursor(cursor):
        print("Set cursor variable")
        return None
    if not isinstance(facultID, int):
        return None
    if isFacultExists(cursor=cursor, facultID=facultID):
        cursor.execute(f"SELECT * FROM chairs WHERE facult_id = {facultID}")
        output = cursor.fetchall()
        return output
    else:
        return None
def getChair(cursor=None, chairID=None, chairName=None):
    if not checkCursor(cursor):
        print("Set cursor variable")
        return None
    if not isinstance(chairID, int) and not isinstance(chairName, str):
        return None
    if isinstance(chairID, int):
        cursor.execute(f"SELECT rowid, facult_id, name FROM chairs WHERE rowid = {chairID}")
    elif isinstance(chairName, str):
        cursor.execute(f'SELECT * FROM chairs WHERE name = "{chairName}"')
    output = cursor.fetchone()
    return output
def getChairObject(cursor=None, chairID=None):
    if not checkCursor(cursor):
        print("Set cursor variable")
        return None
    if not isinstance(chairID, int):
        return None
    chairObject = ChairClass.Chair(cursor=cursor, chairID=chairID)
    return chairObject
def isChairExists(cursor=None, name=None, chairID=None):
    if not checkCursor(cursor):
        print("Set cursor variable")
        return None
    # Checks if name_or_id is not str or int, or if name_or_id is None
    if (not isinstance(name, str) and not isinstance(chairID, int)) or not isinstance(cursor, sqlite3.Cursor):
        return False
    # If name_or_id is integer, then search by rowid
    if isinstance(chairID, int):
        cursor.execute(f'SELECT * FROM chairs WHERE rowid = {chairID}')
    # Else if name_or_id is string, then search by name
    elif isinstance(name, str):
        cursor.execute(f'SELECT * FROM chairs WHERE name = "{name}"')

    output = cursor.fetchone()
    if output is not None:
        return True
    else:
        return False
def addChair(cursor=None, chairName=None, facultID=None):
    if not isinstance(chairName, str) or not isinstance(facultID, int) or not isinstance(cursor, sqlite3.Cursor):
        return False
    if isChairExists(cursor=cursor, name=chairName) or not isFacultExists(cursor=cursor, facultID=facultID):
        return False
    cursor.execute(f"INSERT INTO chairs VALUES ({facultID}, '{chairName}')")
    return True
def removeChair(cursor=None, chairID=None):
    if isinstance(cursor, sqlite3.Cursor) and isinstance(chairID, int) and isChairExists(cursor=cursor, chairID=chairID):
        cursor.execute(f"DELETE FROM chairs WHERE rowid = {chairID}")
        return True
    return False
def removeChairsList(cursor=None, chairIDList=None):
    if not isinstance(chairIDList, list) or isinstance(cursor, sqlite3.Cursor):
        return False
    for chair_id in chairIDList:
        cursor.execute(f"DELETE FROM chairs WHERE rowid = {chair_id}")
    return True

# ------------ DIRECTION ------------
def getAllDirections(cursor=None):
    if not isinstance(cursor, sqlite3.Cursor):
        return None
    cursor.execute('SELECT rowid, chair_id, name FROM directions')
    output = cursor.fetchall()
    return output
def getDirection(cursor=None, directionID = None, directionName=None):
    if (not isinstance(directionID, int) and not isinstance(directionName, str)) or not isinstance(cursor, sqlite3.Cursor):
        return None
    if isinstance(directionID, int):
        cursor.execute(f"SELECT * FROM directions WHERE rowid = {directionID}")
    elif isinstance(directionName, str):
        cursor.execute(f'SELECT * FROM directions WHERE name = "{directionName}"')
    output = cursor.fetchone()
    return output
def getDirectionObject(cursor=None, directionID=None):
    if not isinstance(directionID, int) or not isinstance(cursor, sqlite3.Cursor):
        return None
    directionObject = DirectionClass.Direction(cursor=cursor, directionID=directionID)
    return directionObject
def isDirectionExists(cursor=None, name=None, directionID=None):
    if not (isinstance(name, str) and not isinstance(directionID, int)) or not isinstance(cursor, sqlite3.Cursor):
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
def addDirection(cursor=None, directionName=None, chairID=None):
    if not isinstance(directionName, str) or not isinstance(chairID, int) or not isinstance(cursor, sqlite3.Cursor):
        print("Direction name must be string and chairID must be integer")
        return False
    if isDirectionExists(cursor=cursor, name=directionName) or not isChairExists(cursor=cursor, chairID=chairID):
        print("Direction name already exists or chairID does not exist")
        return False
    cursor.execute(f'INSERT INTO directions VALUES ({chairID}, "{directionName}")')
def removeDirection(cursor=None, directionID=None):
    if isinstance(directionID, int) and isDirectionExists(directionID=directionID) and isinstance(cursor, sqlite3.Cursor):
        cursor.execute(f"DELETE FROM directions WHERE rowid = {directionID}")
        return True
    return False
def removeDirectionList(cursor=None, directionIDList=None):
    if not isinstance(directionIDList, list) or not isinstance(cursor, sqlite3.Cursor):
        return False
    for directionID in directionIDList:
        cursor.execute(f"DELETE FROM directions WHERE rowid = {directionID}")
    return True

# ------------ SUBJECT ------------
def getAllSubjects(cursor=None):
    if not isinstance(cursor, sqlite3.Cursor):
        return None
    cursor.execute('SELECT rowid, direction_id, name FROM subjects')
    output = cursor.fetchall()
    return output
def getSubject(cursor=None, subjectID=None, subjectName=None):
    if (not isinstance(subjectID, int) and not isinstance(subjectName, str)) or not isinstance(cursor, sqlite3.Cursor):
        return None
    if isinstance(subjectID, int):
        cursor.execute(f"SELECT * FROM subjects WHERE rowid = {subjectID}")
    elif isinstance(subjectName, str):
        cursor.execute(f'SELECT * FROM subjects WHERE name = "{subjectName}"')
    output = cursor.fetchone()
    return output

def getSubjectObject(cursor=None, subjectID=None):
    if not isinstance(subjectID, int) or not isinstance(cursor, sqlite3.Cursor):
        return None
    subjectObject = SubjectClass.Subject(cursor=cursor, subjectID=subjectID)
    return subjectObject
def isSubjectExists(cursor=None, subjectID=None, subjectName=None):
    if (not isinstance(subjectID, int) and not isinstance(subjectName, str)) or not isinstance(cursor, sqlite3.Cursor):
        return False
    output = None
    if isinstance(subjectID, int):
        output = getSubject(cursor=cursor, subjectID=subjectID)
    elif isinstance(subjectName, str):
        output = getSubject(cursor=cursor, subjectName=subjectName)
    if output is not None:
        return True
    else:
        return False
def addSubject(cursor=None, directionID=None, subjectName=None):
    if not isinstance(cursor, sqlite3.Cursor):
        return None
    if isSubjectExists(cursor=cursor, subjectName=subjectName) or not isDirectionExists(cursor=cursor, directionID=directionID):
        print("Subject already exists or direction not exists")
        return False
    if isinstance(directionID, int) and isinstance(subjectName, str):
        cursor.execute(f'INSERT INTO subjects VALUES ({directionID}, "{subjectName}")')
        return True
    else:
        return False
def removeSubject(cursor=None, subjectID=None):
    if isinstance(cursor, sqlite3.Cursor) and isinstance(subjectID, int) and isSubjectExists(subjectID=subjectID):
        cursor.execute(f"DELETE FROM subjects WHERE rowid = {subjectID}")
        return True
    else:
        return False
def removeSubjectList(cursor=None, subjectIDList=None):
    if isinstance(subjectIDList, list) and isinstance(cursor, sqlite3.Cursor):
        for subjectID in subjectIDList:
            cursor.execute(f"DELETE FROM subjects WHERE rowid = {subjectID}")
        return True
    return False
# =========================================================
# ---------------- USER ----------------
def getAllUsers(cursor=None):
    if not isinstance(cursor, sqlite3.Cursor):
        return None
    cursor.execute('SELECT * FROM users')
    output = cursor.fetchall()
    return output

