from code.database import FacultClass
from code.database import ChairClass
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
def getFacultObject(facult_id):
    facult_object = FacultClass.Facult(facult_id)
    return facult_object
def isFacultExists(name=None, facultID=None):
    if name is None or facultID is None:
        return False

    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()

    if name is not None:
        cursor.execute(f'SELECT * FROM facults WHERE name = "{name}"')
    elif facultID is not None:
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
def removeManyFacults(facultIDList=None):
    if not isinstance(facultIDList, list):
        return False

    for facult_id in facultIDList:
        removeFacult(facult_id)
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
    chair_object = ChairClass.Chair(chairID)
    return chair_object
def isChairExists(name=None, chairID=None):
    # Checks if name_or_id is not str or int, or if name_or_id is None
    if name is None or chairID is None:
        return False

    database = sqlite3.connect(CONSPECTS_DB)
    cursor = database.cursor()

    # If name_or_id is integer, then search by rowid
    if chairID is not None:
        cursor.execute(f'SELECT * FROM chairs WHERE rowid = "{chairID}"')
    # Else if name_or_id is string, then search by name
    elif name is not None:
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
def removeManyChairs(chair_id_list=None):
    if chair_id_list is None or not isinstance(chair_id_list, list):
        return False

    for chair_id in chair_id_list:
        removeChair(chair_id)
    return True
