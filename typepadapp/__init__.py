class TypePadAppException(Exception):
    """Generic exception for anything that goes
    bad in a TypePad app.
    """
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)