from code.database.repo import subjectRepo, directionRepo


class Subject:
    def __init__(self, subjectID=None, cursor=None):
        subjectTuple = subjectRepo.get(cursor=cursor, subjectID=subjectID)
        if subjectTuple is None:
            self.id = None
            self.directionID = None
            self.name = None
        else:
            self.id = subjectTuple[0]
            self.directionID = subjectTuple[1]
            self.name = subjectTuple[2]
    def getID(self):
        return self.id
    def getDirectionID(self):
        return self.directionID
    # def getChairID(self):
    #     return directionRepo.getObject(cursor=cursor, directionID=.getDirectionID()).getChairID()
    # def getFacultID(self):
    #     return dbProcessing.getDirection(self.getDirectionID()).getFacultID()
    def getName(self):
        return self.name

