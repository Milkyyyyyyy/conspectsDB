from code.database import dbProcessing

class Facult:
    def __init__(self, facultID=None, cursor=None):
        facult_tuple = dbProcessing.getFacult(cursor=cursor, facultID=facultID)
        if facult_tuple is None:
            print("No such facult")
            self.id = None
            self.name = None
            return
        self.id = facultID
        self.name = dbProcessing.getFacultByID(facultID)[0]
    # Returns name of facult
    def getName(self):
        return self.name
    def getID(self):
        return self.id