from code.database import FacultClass, SubjectClass, ChairClass, DirectionClass
import sqlite3





# TODO
# 1. Доделать все проверки и архитектуру

# ======== Methods ========
# -------- Facults --------


# ------- Chairs --------

# ------------ DIRECTION ------------


# ------------ SUBJECT ------------

# =========================================================
# ---------------- USER ----------------
def getAllUsers(cursor=None):
    if not checkCursor(cursor):
        print("Set cursor variable")
        return None
    cursor.execute('SELECT * FROM users')
    output = cursor.fetchall()
    return output
def getUser(cursor=None, telegramID=None, rowID=None):
    if not checkCursor(cursor):
        print("Set cursor variable")
        return None
    output = None
    if isinstance(rowID, int):
        cursor.execute(f"SELECT * FROM users WHERE rowid = {rowID}")
        output = cursor.fetchone()
    elif isinstance(telegramID, str):
        cursor.execute(f'SELECT * FROM users WHERE telegram_id = "{telegramID}"')
        output = cursor.fetchone()
    return output