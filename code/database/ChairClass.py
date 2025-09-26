from code.database import dbProcessing

class Chair:
    def __init__(self, chairID):
        chair_tuple = dbProcessing.getChair(chairID=chairID)
        if chair_tuple is None:
            self.id = None
            self.name = None
            self.facult_id = None
        else:
            self.id = chair_tuple[0]
            self.facult_id = chair_tuple[1]
            self.name = chair_tuple[2]

    def getName(self):
        return self.name

    def getFacult_id(self):
        return self.facult_id

    def getID(self):
        return self.id
