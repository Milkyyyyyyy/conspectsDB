from turtledemo.clock import datum

import FacultClass
import ChairClass
import sqlite3

# ======== Methods ========
# -------- Facults --------
def get_all_facults():
    database = sqlite3.connect('conspects.db')
    cursor = database.cursor()
    cursor.execute("SELECT rowid, name FROM facults")
    output = cursor.fetchall()
    database.close()
    return output
def get_facult_by_id(facult_id):
    database = sqlite3.connect('conspects.db')
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
    if facult_object.id != -1:
        return facult_object
    else:
        return None
def is_facult_exists(name=None):
    database = sqlite3.connect('conspects.db')
    cursor = database.cursor()
    cursor.execute(f'SELECT * FROM facults WHERE name = "{name}"')
    output = cursor.fetchone()
    database.close()
    if output != None:
        return True
    else:
        return False

def add_facult(facult_name=None):
    database = sqlite3.connect('conspects.db')
    cursor = database.cursor()
    if is_facult_exists(name=facult_name):
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
    database = sqlite3.connect('conspects.db')
    cursor = database.cursor()
    cursor.execute(f"DELETE FROM facults WHERE rowid = {facult_id}")
    database.commit()
    database.close()
    return None


# ------- Chairs --------
def get_all_chairs():
    database = sqlite3.connect('conspects.db')
    cursor = database.cursor()
    cursor.execute(f'SELECT rowid, name, facult_id FROM chairs')
    output = cursor.fetchall()
    daatabase.close()
    return output
def get_chair_by_id(chair_id):
    database = sqlite3.connect('conspects.db')
    cursor = database.cursor()
    cursor.execute(f"SELECT * FROM chairs WHERE rowid = {chair_id}")
    output = cursor.fetchone()
    database.close()
    return output
def get_chair_object(chair_id):
    chair_object = ChairClass.Chair(chair_id)
    if chair_object.id != None:
        return None
    else:
        return chair_object
def is_chair_exists(name=None):
    database = sqlite3.connect('conspects.db')
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
    database = sqlite3.connect('conspects.db')
    cursor = database.cursor()
    if is_chair_exists(name=chair_name) or chair_name is None or facult_id is None:
        return None
    cursor.execute(f"INSERT INTO chairs VALUES ('{chair_name}')")

