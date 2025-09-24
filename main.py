import sqlite3

def getFacult(facult_id):
    database = sqlite3.connect('conspects.db')
    cursor = database.cursor()
    cursor.execute(f"SELECT * FROM facult WHERE rowid = {facult_id}")
    output = cursor.fetchone()
    database.close()
    return output
print(getFacult(2))