from code.database.repo import facultRepo


class Facult:
    def __init__(self, facultID=None, cursor=None):
        facult_tuple = facultRepo.getOne(cursor=cursor, facultID=facultID)
        if facult_tuple is None:
            print("No such facult")
            self.id = None
            self.name = None
            return
        self.id = facultID
        self.name = facult_tuple[0]
    # Returns name of facult
    def getName(self):
        return self.name
    def getID(self):
        return self.id