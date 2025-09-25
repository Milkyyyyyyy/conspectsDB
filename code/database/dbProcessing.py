from code.database import FacultClass
from code.database import ChairClass
import sqlite3
databasePath = 'files/database/conspects.db'
# ======== Methods ========
# -------- Facults --------
def getAllFacults():
    database = sqlite3.connect(databasePath)
    cursor = database.cursor()
    cursor.execute("SELECT rowid, name FROM facults")
    output = cursor.fetchall()
    database.close()
    return output

def getFacultByID(facult_id):
    database = sqlite3.connect(databasePath)
    cursor = database.cursor()
    try:
        cursor.execute(f"SELECT * FROM facults WHERE rowid = {facult_id}")
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
    database = sqlite3.connect(databasePath)
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

def addFacult(facult_name=None):
    if facult_name is None or not isinstance(facult_name, str):
        return False
    database = sqlite3.connect(databasePath)
    cursor = database.cursor()
    if isFacultExists(name=facult_name):
        print('Facult already exists')
        return False
    cursor.execute(f"INSERT INTO facults VALUES ('{facult_name}')")
    database.commit()
    database.close()
    return True
def removeFacult(facult_id):
    database = sqlite3.connect(databasePath)
    cursor = database.cursor()
    cursor.execute(f"DELETE FROM facults WHERE rowid = {facult_id}")
    database.commit()
    database.close()
    return True
def removeManyFacults(facult_id_list=None):
    if facult_id_list is None or not isinstance(facult_id_list, list):
        return False
    for facult_id in facult_id_list:
        removeFacult(facult_id)
    return True


# ------- Chairs --------
def getAllChairs():
    database = sqlite3.connect(databasePath)
    cursor = database.cursor()
    cursor.execute(f'SELECT rowid, name, facult_id FROM chairs')
    output = cursor.fetchall()
    database.close()
    return output
def getChairByID(chair_id):
    database = sqlite3.connect(databasePath)
    cursor = database.cursor()
    cursor.execute(f"SELECT rowid, facult_id, name FROM chairs WHERE rowid = {chair_id}")
    output = cursor.fetchone()
    database.close()
    return output
def getChairObject(chair_id):
    chair_object = ChairClass.Chair(chair_id)
    return chair_object
def isChairExists(name=None, chairID=None):
    # Checks if name_or_id is not str or int, or if name_or_id is None
    if name is None and chairID is None:
        return False
    database = sqlite3.connect(databasePath)
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
def addChair(chair_name=None, facult_id=None):
    if not isinstance(chair_name, str) or not isinstance(facult_id, int):
        return False
    database = sqlite3.connect(databasePath)
    cursor = database.cursor()
    if isChairExists(chair_name) or not isFacultExists(facultID=facult_id):
        return False
    cursor.execute(f"INSERT INTO chairs VALUES ({facult_id}, '{chair_name}')")
    database.commit()
    database.close()
    return True

def removeChair(chair_id):
    database = sqlite3.connect(databasePath)
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
