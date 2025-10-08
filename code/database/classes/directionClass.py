class DirectionInterface:
    def __init__(self, directionTuple:tuple = None):
        if not isinstance(directionTuple, tuple):
            self.id = None
            self.chairID = None
            self.name = None
        else:
            self.id = directionTuple[0]
            self.chairID = directionTuple[1]
            self.name = directionTuple[2]
    def getName(self) -> str:
        return self.name
    def getID(self) -> int:
        return self.id
    def getChairID(self) -> int:
        return self.chairID
