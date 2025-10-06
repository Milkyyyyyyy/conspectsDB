class Subject:
    def __init__(self, subjectTuple=None):
        if not isinstance(subjectTuple, tuple):
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
    def getName(self):
        return self.name

