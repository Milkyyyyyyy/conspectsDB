import sqlite3

# Returns facult by facult_id
def getFacult(facult_id):
    database = sqlite3.connect('conspects.db')
    cursor = database.cursor()
    cursor.execute(f"SELECT * FROM facults WHERE rowid = {facult_id}")
    output = cursor.fetchone()
    database.close()
    return output
print(getFacult(1))