from code.database import dbProcessing

class Facult:
    def __init__(self, facult_id):
        facult_tuple = dbProcessing.get_facult_by_id(facult_id)
        if facult_tuple is None:
            print("No such facult")
            self.id = None
            self.name = None
            return
        self.id = facult_id
        self.name = dbProcessing.get_facult_by_id(facult_id)[0]
    # Returns name of facult
    def getName(self):
        return self.name
    def getID(self):
        return self.id