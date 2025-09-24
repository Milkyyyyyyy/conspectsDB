import sqlite3

# Returns facult by facult_id

class Facult:
    # Returns tuple of information from table about facult
    # On errors returns None

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

def getFacult(facult_id):
    database = sqlite3.connect('conspects.db')
    try:
        cursor = database.cursor()
        cursor.execute(f"SELECT * FROM facults WHERE rowid = {facult_id}")
        output = cursor.fetchone()
        database.close()
        return output
    except:
        database.close()
        return None


facultObject = Facult(2)
print(facultObject.getName())