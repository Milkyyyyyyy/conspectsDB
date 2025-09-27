import sqlite3

CONSPECTS_DB = 'files/database/conspects.db'

def checkCursor(cursor=None):
    return isinstance(cursor, sqlite3.Cursor)