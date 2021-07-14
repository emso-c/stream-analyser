class DifferentListSizeError(Exception):
    """ Raises when list sizes are not the same """
    pass

class ConstantsNotAscendingError(Exception):
    """ Raises when a series of numbers are not in ascending order """
    pass

class ConstantsNotUniqueError(Exception):
    """ Raises when a series of numbers are not unique """
    pass
