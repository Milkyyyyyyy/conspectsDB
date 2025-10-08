from code.logging import logger

class ChairInterface:
    def __init__(self, chairTuple:tuple = None):
        if not isinstance(chairTuple, tuple):
            logger.error("Can't parse information from non tuple var")
            self.id = None
            self.name = None
            self.facult_id = None
        else:
            self.id = chairTuple[0]
            self.facult_id = chairTuple[1]
            self.name = chairTuple[2]
            logger.info("Successfully parsed information")
            logger.debug("ID=%s, facult_id=%s, name=%s", self.id, self.facult_id, self.name)

    def getName(self) -> str:
        logger.debug("Returning chair name %s", self.name)
        return self.name

    def getFacultID(self) -> int:
        return self.facult_id

    def getID(self) -> int:
        return self.id
