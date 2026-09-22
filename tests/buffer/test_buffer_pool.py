from collections.abc import Iterator
from pathlib import Path

import pytest

from beaver_db.buffer.buffer_pool import BufferPoolManager
from beaver_db.exceptions import BufferPoolFullError, PageNotAllocatedError, PageNotPinnedError
from beaver_db.storage.page_manager import PAGE_SIZE, PageManager
from beaver_db.storage.slotted_page import SlottedPage


class CountingPageManager(PageManager):
    # PageManager che conta le letture e scritture, per verificare hit/miss/write-back.
    def __init__(self, path: str | Path) -> None:
        super().__init__(path)
        self.reads = 0
        self.writes = 0

    def read_page(self, page_id: int) -> bytearray:
        self.reads += 1
        return super().read_page(page_id)

    def write_page(self, page_id: int, data: bytes | bytearray) -> None:
        self.writes += 1
        super().write_page(page_id, data)


@pytest.fixture
def manager(tmp_path: Path) -> Iterator[CountingPageManager]:
    # Fixture: un page manager (con contatori) su un file nuovo.
    mgr = CountingPageManager(tmp_path / "db.bin")
    yield mgr
    mgr.close()


# --- fetch_page ---
def test_fetch_returns_a_full_page(manager: CountingPageManager) -> None:
    # La pagina letta è un bytearray di esattamente PAGE_SIZE byte.
    page_id = manager.allocate_page()
    pool = BufferPoolManager(2, manager)
    data = pool.fetch_page(page_id)
    assert isinstance(data, bytearray)
    assert len(data) == PAGE_SIZE


def test_fetch_miss_reads_from_disk(manager: CountingPageManager) -> None:
    page_id = manager.allocate_page()
    pool = BufferPoolManager(2, manager)
    pool.fetch_page(page_id)
    assert manager.reads == 1


def test_fetch_hit_returns_the_same_buffer_without_disk_read(manager: CountingPageManager) -> None:
    page_id = manager.allocate_page()
    pool = BufferPoolManager(2, manager)
    first = pool.fetch_page(page_id)
    reads_after_first = manager.reads
    second = pool.fetch_page(page_id)
    assert second is first
    assert manager.reads == reads_after_first


def test_fetch_unallocated_page_raises(manager: CountingPageManager) -> None:
    pool = BufferPoolManager(2, manager)
    with pytest.raises(PageNotAllocatedError):
        pool.fetch_page(0)


# --- unpin_page ---
def test_unpin_page_not_in_pool_raises(manager: CountingPageManager) -> None:
    pool = BufferPoolManager(2, manager)
    with pytest.raises(PageNotPinnedError):
        pool.unpin_page(0, dirty=False)


def test_double_unpin_raises(manager: CountingPageManager) -> None:
    page_id = manager.allocate_page()
    pool = BufferPoolManager(2, manager)
    pool.fetch_page(page_id)
    pool.unpin_page(page_id, dirty=False)
    with pytest.raises(PageNotPinnedError):
        pool.unpin_page(page_id, dirty=False)


def test_pin_count_prevents_eviction_until_all_unpins(manager: CountingPageManager) -> None:
    # Due fetch = due pin: finché non si fa il secondo unpin la pagina non è evincibile.
    page_a = manager.allocate_page()
    page_b = manager.allocate_page()
    pool = BufferPoolManager(1, manager)
    pool.fetch_page(page_a)
    pool.fetch_page(page_a)
    pool.unpin_page(page_a, dirty=False)
    with pytest.raises(BufferPoolFullError):
        pool.fetch_page(page_b)
    pool.unpin_page(page_a, dirty=False)
    pool.fetch_page(page_b)  # ora l'eviction è possibile


# --- eviction e LRU ---
def test_eviction_reuses_a_single_frame(manager: CountingPageManager) -> None:
    page_a = manager.allocate_page()
    page_b = manager.allocate_page()
    pool = BufferPoolManager(1, manager)
    pool.fetch_page(page_a)
    pool.unpin_page(page_a, dirty=False)
    pool.fetch_page(page_b)  # evince la pagina a
    pool.unpin_page(page_b, dirty=False)
    assert manager.reads == 2
    pool.fetch_page(page_a)  # a non è più in memoria: va riletta
    assert manager.reads == 3


def test_lru_evicts_the_least_recently_used(manager: CountingPageManager) -> None:
    page_a = manager.allocate_page()
    page_b = manager.allocate_page()
    page_c = manager.allocate_page()
    pool = BufferPoolManager(2, manager)
    pool.fetch_page(page_a)
    pool.unpin_page(page_a, dirty=False)
    pool.fetch_page(page_b)
    pool.unpin_page(page_b, dirty=False)
    pool.fetch_page(page_a)  # a diventa la più recente
    pool.unpin_page(page_a, dirty=False)

    pool.fetch_page(page_c)  # deve evincere b (la meno recente), non a
    reads = manager.reads
    pool.fetch_page(page_a)  # hit: ancora in memoria
    assert manager.reads == reads
    pool.unpin_page(page_a, dirty=False)
    pool.fetch_page(page_b)  # miss: b era stato evinto
    assert manager.reads == reads + 1


def test_evicting_a_dirty_page_writes_it_back(manager: CountingPageManager) -> None:
    page_a = manager.allocate_page()
    page_b = manager.allocate_page()
    pool = BufferPoolManager(1, manager)
    data = pool.fetch_page(page_a)
    data[:] = bytes([0xAB]) * PAGE_SIZE
    pool.unpin_page(page_a, dirty=True)
    pool.fetch_page(page_b)  # evince a, che è sporca
    assert manager.writes == 1
    assert manager.read_page(page_a) == bytes([0xAB]) * PAGE_SIZE


def test_evicting_a_clean_page_does_not_write(manager: CountingPageManager) -> None:
    page_a = manager.allocate_page()
    page_b = manager.allocate_page()
    pool = BufferPoolManager(1, manager)
    pool.fetch_page(page_a)
    pool.unpin_page(page_a, dirty=False)
    pool.fetch_page(page_b)
    assert manager.writes == 0


def test_a_clean_unpin_does_not_clear_the_dirty_flag(manager: CountingPageManager) -> None:
    page_a = manager.allocate_page()
    page_b = manager.allocate_page()
    pool = BufferPoolManager(1, manager)
    pool.fetch_page(page_a)
    pool.unpin_page(page_a, dirty=True)
    pool.fetch_page(page_a)  # hit
    pool.unpin_page(page_a, dirty=False)  # non deve azzerare il dirty
    pool.fetch_page(page_b)  # evince a: deve scriverla
    assert manager.writes == 1


# --- flush_page / flush_all ---
def test_flush_page_writes_and_clears_dirty(manager: CountingPageManager) -> None:
    page_id = manager.allocate_page()
    pool = BufferPoolManager(1, manager)
    data = pool.fetch_page(page_id)
    data[:] = bytes([0x11]) * PAGE_SIZE
    pool.unpin_page(page_id, dirty=True)
    pool.flush_page(page_id)
    assert manager.writes == 1
    pool.flush_page(page_id)  # non è più sporca
    assert manager.writes == 1


def test_flush_page_not_in_pool_raises(manager: CountingPageManager) -> None:
    pool = BufferPoolManager(1, manager)
    with pytest.raises(PageNotPinnedError):
        pool.flush_page(0)


def test_flush_all_writes_every_dirty_page_including_page_zero(
    manager: CountingPageManager,
) -> None:
    # Il test chiave: la pagina 0 è un id valido e non deve essere saltata.
    page_zero = manager.allocate_page()
    page_one = manager.allocate_page()
    assert page_zero == 0
    pool = BufferPoolManager(2, manager)
    data_zero = pool.fetch_page(page_zero)
    data_zero[:] = bytes([0x22]) * PAGE_SIZE
    pool.unpin_page(page_zero, dirty=True)
    data_one = pool.fetch_page(page_one)
    data_one[:] = bytes([0x33]) * PAGE_SIZE
    pool.unpin_page(page_one, dirty=True)
    pool.flush_all()
    assert manager.writes == 2
    assert manager.read_page(page_zero) == bytes([0x22]) * PAGE_SIZE
    assert manager.read_page(page_one) == bytes([0x33]) * PAGE_SIZE


# --- new_page ---
def test_new_page_returns_a_new_pinned_page(manager: CountingPageManager) -> None:
    pool = BufferPoolManager(2, manager)
    page_id, data = pool.new_page()
    assert page_id == 0
    assert len(data) == PAGE_SIZE
    assert data == bytes(PAGE_SIZE)  # pagina nuova: tutti zeri
    assert manager.num_pages() == 1
    pool.unpin_page(page_id, dirty=False)  # era pinnata


def test_new_page_fails_when_pool_is_full_and_all_pinned(manager: CountingPageManager) -> None:
    pool = BufferPoolManager(1, manager)
    pool.new_page()  # occupa e pinna l'unico frame
    with pytest.raises(BufferPoolFullError):
        pool.new_page()


# --- integrazione ---
def test_buffer_pool_with_slotted_page(manager: CountingPageManager) -> None:
    pool = BufferPoolManager(2, manager)
    page_id, data = pool.new_page()
    page = SlottedPage(data)
    page.insert(b"hello")
    pool.unpin_page(page_id, dirty=True)
    pool.flush_page(page_id)

    # Rileggiamo dal disco, fuori dal pool, e la pagina si riapre identica.
    reopened = SlottedPage(manager.read_page(page_id))
    assert reopened.read(0) == b"hello"
