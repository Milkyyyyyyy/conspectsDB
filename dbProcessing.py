import FacultClass
import sqlite3

# --------- Methods ---------
# Returns tuple of information from table about facult
# On errors returns None
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