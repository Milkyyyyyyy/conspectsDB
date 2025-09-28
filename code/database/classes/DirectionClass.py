from code.database.Repo import directionRepo, chairRepo


class Direction:
    def __init__(self, directionID=None, cursor=None):
        directionTuple = directionRepo.getOne(cursor=cursor, directionID=directionID)
        if directionTuple is None:
            self.id = None
            self.chairID = None
            self.name = None
        else:
            self.id = directionTuple[0]
            self.chairID = directionTuple[1]
            self.name = directionTuple[2]
    def getName(self):
        return self.name
    def getID(self):
        return self.id
    def getChairID(self):
        return self.chairID
    def getFacultID(self):
        return chairRepo.getObject(self.getChairID()).getFacultID()

