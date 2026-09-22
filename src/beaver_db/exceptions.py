class CorruptFileError(Exception):
    """The database file size is not a whole number of pages."""


class PageNotAllocatedError(Exception):
    """The requested page is outside the allocated range."""


class InvalidPageSizeError(Exception):
    """The page size is not standard size."""


class SlotNotAllocatedError(Exception):
    """The requested slot is free or out of range."""


class PageFullError(Exception):
    """The page has no enough space."""


class BufferPoolFullError(Exception):
    """The buffer pool has no evictable frame."""


class PageNotPinnedError(Exception):
    """The page is not in the buffer pool or is not pinned."""
