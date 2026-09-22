from dataclasses import dataclass

from beaver_db.exceptions import BufferPoolFullError, PageNotPinnedError
from beaver_db.storage.page_manager import PAGE_SIZE, PageManager


@dataclass
class Frame:
    page_id: int | None  # None vuol dire frame libero
    data: bytearray
    pin_count: int
    dirty: bool
    last_used: int


class BufferPoolManager:
    def __init__(self, capacity: int, page_manager: PageManager) -> None:
        self._frames = [
            Frame(page_id=None, data=bytearray(PAGE_SIZE), pin_count=0, dirty=False, last_used=0)
            for _ in range(capacity)
        ]
        self._page_table: dict[int, Frame] = {}
        self._page_manager = page_manager
        self._clock: int = 0

    def fetch_page(self, page_id: int) -> bytearray:
        frame = self._page_table.get(page_id)
        if frame is not None:
            # HIT: la pagina è già in memoria, basta pinnarla e aggiornarne la recenza.
            self._clock += 1
            frame.pin_count += 1
            frame.last_used = self._clock
            return frame.data

        # MISS: scegli un frame libero, oppure evinci la pagina meno usata di recente.
        free_index = next(
            (index for index, candidate in enumerate(self._frames) if candidate.page_id is None),
            None,
        )
        if free_index is not None:
            target_index = free_index
        else:
            candidates = [
                (index, candidate)
                for index, candidate in enumerate(self._frames)
                if candidate.page_id is not None and candidate.pin_count == 0
            ]
            if not candidates:
                raise BufferPoolFullError("not enough space in the buffer pool")
            target_index, victim = min(candidates, key=lambda item: item[1].last_used)
            victim_page_id = victim.page_id
            assert victim_page_id is not None  # un frame evincibile è occupato
            if victim.dirty:
                self._page_manager.write_page(victim_page_id, victim.data)
            self._page_table.pop(victim_page_id)

        # Solo ora leggiamo la pagina dal disco: sappiamo già dove metterla.
        data = self._page_manager.read_page(page_id)
        self._clock += 1
        new_frame = Frame(
            page_id=page_id, data=data, pin_count=1, dirty=False, last_used=self._clock
        )
        self._frames[target_index] = new_frame
        self._page_table[page_id] = new_frame
        return data

    def unpin_page(self, page_id: int, dirty: bool) -> None:
        frame = self._page_table.get(page_id)
        if frame is None:
            raise PageNotPinnedError(f"page {page_id} is not in the buffer pool")
        if frame.pin_count == 0:
            raise PageNotPinnedError(f"page {page_id} is not pinned")
        frame.pin_count -= 1
        if dirty:
            frame.dirty = True

    def flush_page(self, page_id: int) -> None:
        frame = self._page_table.get(page_id)
        if frame is None:
            raise PageNotPinnedError(f"page {page_id} is not in the buffer pool")
        if frame.dirty:
            self._page_manager.write_page(page_id, frame.data)
        frame.dirty = False

    def flush_all(self) -> None:
        for frame in self._frames:
            if frame.page_id is not None and frame.dirty:
                self._page_manager.write_page(frame.page_id, frame.data)
                frame.dirty = False

    def new_page(self) -> tuple[int, bytearray]:
        page_id = self._page_manager.allocate_page()
        data = self.fetch_page(page_id)
        return page_id, data
