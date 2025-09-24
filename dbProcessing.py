import sqlite3

from main import facultObject


# --------- Classes ---------
# Returns facult by facult_id
class Facult:
    def __init__(self, facult_id):
        facult_tuple = getFacult(facult_id)
        if facult_tuple is None:
            print("No such facult")
            self.id = -1
            self.name = ""
            return
        self.id = facult_id
        self.name = getFacult(facult_id)[0]
    def getName(self):
        return self.name


# --------- Methods ---------
# Returns tuple of information from table about facult
# On errors returns None
def getFacult(facult_id):
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
def getFacultObject(facult_id):
    facultObject = Facult(facult_id)
    if facultObject.id != -1:
        return facultObject
    else:
        return None