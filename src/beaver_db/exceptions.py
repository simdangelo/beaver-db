class CorruptFileError(Exception):
    """The database file size is not a whole number of pages."""


class PageNotAllocatedError(Exception):
    """The requested page is outside the allocated range."""


class InvalidPageSizeError(Exception):
    """The page size is not standard size."""
