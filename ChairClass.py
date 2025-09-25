import dbProcessing
class Chair:
    def __init__(self, chair_id):
        chair_tuple = dbProcessing.get_chair_by_id(chair_id)
        if chair_tuple is None:
            self.id = None
            self.name = None
            self.facult_id = None
        else:
            self.id = chair_tuple[0]
            self.name = chair_tuple[1]
            self.facult_id = chair_tuple[2]
