class Facult:
    def __init__(self, facult_tuple):
        if not isinstance(facult_tuple, tuple):
            print("No such facult")
            self.id = None
            self.name = None
            return
        else:
            self.id = facult_tuple[0]
            self.name = facult_tuple[1]
    # Returns name of facult
    def getName(self):
        return self.name
    def getID(self):
        return self.id