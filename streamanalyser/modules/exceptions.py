class DifferentListSizeError(Exception):
    """Raises when list sizes are not the same"""

    pass


class ConstantsNotAscendingError(Exception):
    """Raises when a series of numbers are not in ascending order"""

    pass


class ConstantsNotUniqueError(Exception):
    """Raises when a series of numbers are not unique"""

    pass


class StreamIsLiveOrUpcomingError(Exception):
    """Raises when a live stream is live or upcoming"""

    pass


class DuplicateContextException(Exception):
    """Raised when a context is duplicated"""
    def __init__(self, message, encounters:list):
        self.message = message
        self.encounters = encounters 
    

class PathAlreadyExistsException(Exception):
    """Raised when a path is already exists in the sources"""
    
    pass

class UnexpectedException(Exception):
    """Raised when an unexpected event occurs"""
    
    pass

class ContextsAllCorruptException(Exception):
    """Raised when an all the contexts are corrupt"""
    
    pass