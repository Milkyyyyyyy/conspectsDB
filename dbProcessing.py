import sqlite3
import FacultClass

from main import facultObject

# --------- Methods ---------
# Returns tuple of information from table about facult
# On errors returns None
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