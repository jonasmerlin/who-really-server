class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class URLError(Error):
    """Exception raised for errors in the input.

    Attributes:
        message -- explanation of what was wrong with the url
    """

    def __init__(self, message):
        self.message = message
