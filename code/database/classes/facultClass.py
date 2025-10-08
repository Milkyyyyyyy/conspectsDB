class FacultInterface:
    def __init__(self, facultTuple:tuple = None):
        if not isinstance(facultTuple, tuple):
            print("No such facult")
            self.id = None
            self.name = None
            return
        else:
            self.id = facultTuple[0]
            self.name = facultTuple[1]
    # Returns name of facult
    def getName(self) -> str:
        return self.name
    def getID(self) -> int:
        return self.id