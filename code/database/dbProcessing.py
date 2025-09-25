from code.database import FacultClass
from code.database import ChairClass
import sqlite3
databasePath = 'files/database/conspects.db'
# ======== Methods ========
# -------- Facults --------
def get_all_facults():
    database = sqlite3.connect(databasePath)
    cursor = database.cursor()
    cursor.execute("SELECT rowid, name FROM facults")
    output = cursor.fetchall()
    database.close()
    return output

def get_facult_by_id(facult_id):
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
def get_facult_object(facult_id):
    facult_object = FacultClass.Facult(facult_id)
    return facult_object
def is_facult_exists_name(name=None):
    database = sqlite3.connect(databasePath)
    cursor = database.cursor()
    cursor.execute(f'SELECT * FROM facults WHERE name = "{name}"')
    output = cursor.fetchone()
    database.close()
    if output is not None:
        return True
    else:
        return False
def is_facult_exists_id(facult_id=None):
    database = sqlite3.connect(databasePath)
    cursor = database.cursor()
    cursor.execute(f'SELECT * FROM facults WHERE rowid = "{facult_id}"')
    output = cursor.fetchone()
    database.close()
    if output is not None:
        return True
    else:
        return False

def add_facult(facult_name=None):
    database = sqlite3.connect(databasePath)
    cursor = database.cursor()
    if is_facult_exists_name(name=facult_name):
        print('Facult already exists')
        return None
    try:
        cursor.execute(f"INSERT INTO facults VALUES ('{facult_name}')")
    except:
        print("Error name")
    database.commit()
    database.close()
    return None
def remove_facult(facult_id):
    database = sqlite3.connect(databasePath)
    cursor = database.cursor()
    cursor.execute(f"DELETE FROM facults WHERE rowid = {facult_id}")
    database.commit()
    database.close()
    return None
def remove_many_facults(facult_id_list=[]):
    for facult_id in facult_id_list:
        remove_facult(facult_id)


# ------- Chairs --------
def get_all_chairs():
    database = sqlite3.connect(databasePath)
    cursor = database.cursor()
    cursor.execute(f'SELECT rowid, name, facult_id FROM chairs')
    output = cursor.fetchall()
    database.close()
    return output
def get_chair_by_id(chair_id):
    database = sqlite3.connect(databasePath)
    cursor = database.cursor()
    cursor.execute(f"SELECT rowid, facult_id, name FROM chairs WHERE rowid = {chair_id}")
    output = cursor.fetchone()
    database.close()
    return output
def get_chair_object(chair_id):
    chair_object = ChairClass.Chair(chair_id)
    return chair_object
def is_chair_exists(name=None):
    database = sqlite3.connect(databasePath)
    cursor = database.cursor()
    cursor.execute(f'SELECT * FROM chairs WHERE name = "{name}"')
    output = cursor.fetchone()
    database.close()
    if output is not None:
        return True
    else:
        return False
#!!!! Доделать
def add_chair(chair_name=None,facult_id=None):
    database = sqlite3.connect(databasePath)
    cursor = database.cursor()
    if is_chair_exists(name=chair_name) or chair_name is None or facult_id is None or not is_facult_exists_id(facult_id):
        return None
    cursor.execute(f"INSERT INTO chairs VALUES ({facult_id}, '{chair_name}')")
    database.commit()
    database.close()
def remove_chair(chair_id):
    database = sqlite3.connect(databasePath)
    cursor = database.cursor()
    cursor.execute(f"DELETE FROM chairs WHERE rowid = {chair_id}")
    database.commit()
    database.close()
    return None
def remove_many_chairs(chair_id_list=[]):
    for chair_id in chair_id_list:
        remove_chair(chair_id)

