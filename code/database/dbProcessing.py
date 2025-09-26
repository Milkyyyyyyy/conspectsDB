from code.database import FacultClass
from code.database import ChairClass
from code.database import DirectionClass
import sqlite3
CONSPECTS_DB = 'files/database/conspects.db'

# ======== Methods ========
# -------- Facults --------
def getAllFacults():
    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()
    cursor.execute("SELECT rowid, name FROM facults")
    output = cursor.fetchall()
    database.close()
    return output

def getFacultByID(facultID=None):
    if not isinstance(facultID, int):
        return None
    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()
    try:
        cursor.execute(f"SELECT * FROM facults WHERE rowid = {facultID}")
        output = cursor.fetchone()
        database.close()
        return output
    except:
        database.close()
        return None
def getFacultObject(facultID=None):
    if not isinstance(facultID, int):
        return None
    facultObject = FacultClass.Facult(facultID)
    return facultObject
def isFacultExists(name=None, facultID=None):
    if not isinstance(name, str) and not isinstance(facultID, int):
        return False

    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()

    if isinstance(name, str):
        cursor.execute(f'SELECT * FROM facults WHERE name = "{name}"')
    elif isinstance(facultID, int):
        cursor.execute(f'SELECT * FROM facults WHERE rowid = {facultID}')

    output = cursor.fetchone()
    database.close()

    if output is not None:
        return True
    else:
        return False

def addFacult(facultName=None):
    if not isinstance(facultName, str):
        return False

    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()

    if isFacultExists(name=facultName):
        print('Facult already exists')
        return False

    cursor.execute(f"INSERT INTO facults VALUES ('{facultName}')")
    database.commit()
    database.close()
    return True
def removeFacult(facultID=None):
    if not isinstance(facultID, int):
        return False
    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()
    cursor.execute(f"DELETE FROM facults WHERE rowid = {facultID}")
    database.commit()
    database.close()
    return True
def removeFacultsList(facultIDList=None):
    if not isinstance(facultIDList, list):
        return False
    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()
    for facultID in facultIDList:
        cursor.execute(f"DELETE FROM facults WHERE rowid = {facultID}")
    database.commit()
    database.close()
    return True

# ------- Chairs --------
def getAllChairs():
    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()
    cursor.execute(f'SELECT rowid, name, facult_id FROM chairs')
    output = cursor.fetchall()
    database.close()
    return output
def getAllChairsOfFacult(facultID=None):
    if not isinstance(facultID, int):
        return None
    if isFacultExists(facultID=facultID):
        database = sqlite3.connect(CONSPECTS_DB)
        cursor = database.cursor()
        cursor.execute(f"SELECT * FROM chairs WHERE facult_id = {facultID}")
        output = cursor.fetchall()
        database.close()
        return output
    else:
        return None
def getChairByID(chairID=None):
    if not isinstance(chairID, int):
        return None
    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()
    cursor.execute(f"SELECT rowid, facult_id, name FROM chairs WHERE rowid = {chairID}")
    output = cursor.fetchone()
    database.close()
    return output
def getChairObject(chairID):
    if not isinstance(chairID, int):
        return None
    chairObject = ChairClass.Chair(chairID)
    return chairObject
def isChairExists(name=None, chairID=None):
    # Checks if name_or_id is not str or int, or if name_or_id is None
    if not isinstance(name, str) and not isinstance(chairID, int):
        return False
    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()

    # If name_or_id is integer, then search by rowid
    if isinstance(chairID, int):
        cursor.execute(f'SELECT * FROM chairs WHERE rowid = {chairID}')
    # Else if name_or_id is string, then search by name
    elif isinstance(name, str):
        cursor.execute(f'SELECT * FROM chairs WHERE name = "{name}"')

    output = cursor.fetchone()
    database.close()
    if output is not None:
        return True
    else:
        return False
def addChair(chairName=None, facultID=None):
    if not isinstance(chairName, str) or not isinstance(facultID, int):
        return False
    if isChairExists(chairName) or not isFacultExists(facultID=facultID):
        return False

    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()
    cursor.execute(f"INSERT INTO chairs VALUES ({facultID}, '{chairName}')")
    database.commit()
    database.close()
    return True
def removeChair(chair_id):
    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()
    cursor.execute(f"DELETE FROM chairs WHERE rowid = {chair_id}")
    database.commit()
    database.close()
    return True
def removeChairsList(chairIDList=None):
    if not isinstance(chairIDList, list):
        return False
    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()
    for chair_id in chairIDList:
        cursor.execute(f"DELETE FROM chairs WHERE rowid = {chair_id}")
    database.commit()
    database.close()
    return True
# ------------ DIRECTION ------------
def getAllDirections():
    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()
    cursor.execute('SELECT rowid, chair_id, name FROM directions')
    output = cursor.fetchall()
    database.close()
    return output
def getDirectionByID(directionID):
    if not isinstance(directionID, int):
        return None
    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()
    cursor.execute(f"SELECT rowid, chair_id, name FROM directions WHERE rowid = {directionID}")
    output = cursor.fetchone()
    database.close()
    return output
def getDirectionObject(directionID):
    if not isinstance(directionID, int):
        return None
    directionObject = DirectionClass.Direction(directionID)
    return directionObject
def isDirectionExists(name=None, directionID=None):
    if not isinstance(name, str) and not isinstance(directionID, int):
        return False
    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()
    if isinstance(directionID, int):
        cursor.execute(f"SELECT * FROM directions WHERE rowid = {directionID}")
    elif isinstance(name, str):
        cursor.execute(f'SELECT * FROM directions WHERE name = "{name}"')
    output = cursor.fetchone()
    database.close()
    if output is not None:
        return True
    else:
        return False
def addDirection(directionName=None, chairID=None):
    if not isinstance(directionName, str) or not isinstance(chairID, int):
        print("Direction name must be string and chairID must be integer")
        return False
    if isDirectionExists(name=directionName) or not isChairExists(chairID=chairID):
        print("Direction name already exists or chairID does not exist")
        return False
    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()
    cursor.execute(f'INSERT INTO directions VALUES ({chairID}, "{directionName}")')
    database.commit()
    database.close()
def removeDirection(directionID=None):
    if not isinstance(directionID, int):
        return False
    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()
    cursor.execute(f"DELETE FROM directions WHERE rowid = {directionID}")
    database.commit()
    database.close()
    return True
def removeDirectionList(directionIDList=None):
    if not isinstance(directionIDList, list):
        return False
    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()
    for directionID in directionIDList:
        cursor.execute(f"DELETE FROM directions WHERE rowid = {directionID}")
    database.commit()
    database.close()
    return True