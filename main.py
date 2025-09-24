import sqlite3

# # Create conspects table
# cursor.execute("""CREATE TABLE IF NOT EXISTS conspects(
#     subject_id INTEGER,
#     upload_date TEXT,
#     conspect_date TEXT,
#     user_telegram_id TEXT,
#     theme TEXT,
#     keywords TEXT,
#     views INTEGER,
#     status TEXT,
#     rating INTEGER,
#     anonymous INTEGER
# )""")
#
# # Create conspects_files table
# cursor.execute("""CREATE TABLE IF NOT EXISTS conspects_files(
#     conspect_id INTEGER,
#     path TEXT
# )""")
#
# # Create users table
# cursor.execute("""CREATE TABLE IF NOT EXISTS users(
#     telegram_id TEXT,
#     name TEXT,
#     surname TEXT,
#     study_group TEXT,
#     direction_id INTEGER,
#     role STRING
# )""")
#
# # Create reactions table
# cursor.execute("""CREATE TABLE IF NOT EXISTS reactions(
#     conspect_id INTEGER,
#     user_telegram_id TEXT,
#     reaction INTEGER
# )""")
#
# # Create facult table
# cursor.execute("""CREATE TABLE IF NOT EXISTS facult(
#     name TEXT
# )""")
#
# # Create chair table
# cursor.execute("""CREATE TABLE IF NOT EXISTS chair(
#     facult_id INTEGER,
#     name TEXT
# )""")
#
# # Create direction table
# cursor.execute("""CREATE TABLE IF NOT EXISTS directoin(
#     chair_id INTEGER,
#     name TEXT
# )""")
#
# # Create direction table
# cursor.execute("""CREATE TABLE IF NOT EXISTS subject(
#     direction_id INTEGER,
#     name TEXT
# )""")
# cursor.execute("INSERT INTO facults VALUES('ТЕСТ ФАКУЛЬТЕТ 2')")

# test functions for database
def getFacult(facult_id):
    database = sqlite3.connect('conspects.db')
    cursor = database.cursor()
    cursor.execute(f"SELECT * FROM facults WHERE rowid={facult_id}")
    output = cursor.fetchone()
    database.close()
    return output