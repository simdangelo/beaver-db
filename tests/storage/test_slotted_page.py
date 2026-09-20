import struct
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from beaver_db.exceptions import InvalidPageSizeError, PageFullError, SlotNotAllocatedError
from beaver_db.storage.page_manager import PAGE_SIZE, PageManager
from beaver_db.storage.slotted_page import HEADER_SIZE, SLOT_SIZE, SlottedPage


@pytest.fixture
def page() -> SlottedPage:
    # Fixture: una slotted page nuova su un buffer di zeri.
    return SlottedPage(bytearray(PAGE_SIZE))


def make_page(num_slots: int, data_start: int, slots: list[tuple[int, int]]) -> bytearray:
    # Costruisce a mano una pagina formattata, per testare read/insert senza dipendere da insert.
    buf = bytearray(PAGE_SIZE)
    struct.pack_into("<HH", buf, 0, num_slots, data_start)
    for index, (offset, length) in enumerate(slots):
        struct.pack_into("<HH", buf, HEADER_SIZE + index * SLOT_SIZE, offset, length)
    return buf


# --- __init__ e lettura dell'header ---
def test_new_page_is_formatted(page: SlottedPage) -> None:
    # Una pagina nuova parte formattata: nessuno slot e tutto lo spazio libero.
    assert page.num_slots() == 0
    assert page.free_space() == PAGE_SIZE - HEADER_SIZE


def test_wrong_buffer_size_raises() -> None:
    # Un buffer che non è PAGE_SIZE byte va rifiutato subito.
    with pytest.raises(InvalidPageSizeError):
        SlottedPage(bytearray(PAGE_SIZE - 1))


def test_existing_header_is_read_not_reset() -> None:
    # Una pagina già formattata non viene riformattata: si legge il suo stato.
    buf = bytearray(PAGE_SIZE)
    struct.pack_into("<HH", buf, 0, 3, PAGE_SIZE - 8)  # num_slots=3, data_start=PAGE_SIZE-8
    page = SlottedPage(buf)
    assert page.num_slots() == 3
    assert page.free_space() == (PAGE_SIZE - 8) - (HEADER_SIZE + 3 * SLOT_SIZE)


# --- read ---
def test_read_returns_the_record_bytes() -> None:
    # Slot che punta a un record: read restituisce esattamente quei byte.
    buf = make_page(1, PAGE_SIZE - 2, [(PAGE_SIZE - 2, 2)])
    buf[PAGE_SIZE - 2 : PAGE_SIZE] = b"AB"
    page = SlottedPage(buf)
    assert page.read(0) == b"AB"


def test_read_returns_immutable_bytes() -> None:
    # Il tipo restituito è bytes (immutabile), non bytearray.
    buf = make_page(1, PAGE_SIZE - 1, [(PAGE_SIZE - 1, 1)])
    buf[PAGE_SIZE - 1] = 0x41
    page = SlottedPage(buf)
    assert isinstance(page.read(0), bytes)


def test_read_returns_a_copy_independent_from_the_page() -> None:
    # Modificare il buffer dopo la lettura non cambia il record già restituito.
    buf = make_page(1, PAGE_SIZE - 2, [(PAGE_SIZE - 2, 2)])
    buf[PAGE_SIZE - 2 : PAGE_SIZE] = b"AB"
    page = SlottedPage(buf)
    record = page.read(0)
    buf[PAGE_SIZE - 2] = 0x5A  # 'Z'
    assert record == b"AB"


def test_read_rejects_free_slot() -> None:
    # Uno slot con offset=0 (tombstone) non ha record da leggere.
    page = SlottedPage(make_page(1, PAGE_SIZE, [(0, 0)]))
    with pytest.raises(SlotNotAllocatedError):
        page.read(0)


def test_read_rejects_out_of_range() -> None:
    # Un indice oltre num_slots è un errore (qui la pagina è vuota).
    page = SlottedPage(bytearray(PAGE_SIZE))
    with pytest.raises(SlotNotAllocatedError):
        page.read(0)


def test_read_rejects_negative_slot() -> None:
    # Un indice negativo è un errore.
    page = SlottedPage(make_page(1, PAGE_SIZE - 1, [(PAGE_SIZE - 1, 1)]))
    with pytest.raises(SlotNotAllocatedError):
        page.read(-1)


# --- insert: casi base ---
def test_insert_returns_slot_zero_and_is_readable(page: SlottedPage) -> None:
    # Il primo insert prende lo slot 0 e il record si rilegge identico.
    assert page.insert(b"AB") == 0
    assert page.read(0) == b"AB"
    assert page.num_slots() == 1


def test_insert_returns_sequential_slot_ids(page: SlottedPage) -> None:
    # Gli id degli slot crescono di uno a ogni insert (nessun buco).
    assert page.insert(b"a") == 0
    assert page.insert(b"bb") == 1
    assert page.insert(b"ccc") == 2
    assert page.num_slots() == 3


def test_insert_reduces_free_space_by_record_plus_slot(page: SlottedPage) -> None:
    # Con uno slot nuovo si consumano i byte del record più una voce slot.
    before = page.free_space()
    page.insert(b"hello")
    assert page.free_space() == before - len(b"hello") - SLOT_SIZE


def test_insert_keeps_previous_records_intact(page: SlottedPage) -> None:
    # Inserimenti successivi non sovrascrivono i record precedenti.
    records = [b"alpha", b"beta", b"gamma"]
    for index, record in enumerate(records):
        assert page.insert(record) == index
    for index, record in enumerate(records):
        assert page.read(index) == record


def test_insert_writes_records_from_the_end_backwards() -> None:
    # I record si accodano dalla fine: il primo sta in fondo, il secondo prima di lui.
    buf = bytearray(PAGE_SIZE)
    page = SlottedPage(buf)
    page.insert(b"AB")
    page.insert(b"CDE")
    assert struct.unpack_from("<HH", buf, HEADER_SIZE) == (PAGE_SIZE - 2, 2)
    assert struct.unpack_from("<HH", buf, HEADER_SIZE + SLOT_SIZE) == (PAGE_SIZE - 5, 3)


def test_insert_updates_the_header_in_the_buffer() -> None:
    # Dopo l'insert l'header nel buffer riflette num_slots e data_start aggiornati.
    buf = bytearray(PAGE_SIZE)
    page = SlottedPage(buf)
    page.insert(b"abcd")
    num_slots, data_start = struct.unpack_from("<HH", buf, 0)
    assert num_slots == 1
    assert data_start == PAGE_SIZE - 4
    # Un nuovo SlottedPage sullo stesso buffer vede lo stesso stato.
    reopened = SlottedPage(buf)
    assert reopened.num_slots() == 1
    assert reopened.read(0) == b"abcd"


def test_insert_empty_record_is_readable_as_empty() -> None:
    # Edge case: un record vuoto si inserisce e si rilegge come b"".
    page = SlottedPage(bytearray(PAGE_SIZE))
    slot = page.insert(b"")
    assert slot == 0
    assert page.read(0) == b""
    assert page.num_slots() == 1


# --- insert: riuso di uno slot libero ---
def test_insert_reuses_a_free_slot() -> None:
    # Uno slot libero (tombstone) viene riusato invece di aggiungerne uno nuovo.
    buf = make_page(2, PAGE_SIZE - 2, [(0, 0), (PAGE_SIZE - 2, 2)])
    buf[PAGE_SIZE - 2 : PAGE_SIZE] = b"AB"
    page = SlottedPage(buf)
    assert page.insert(b"XY") == 0
    assert page.num_slots() == 2  # invariato: riuso, non nuovo slot
    assert page.read(0) == b"XY"
    assert page.read(1) == b"AB"


def test_insert_reusing_a_free_slot_does_not_consume_slot_space() -> None:
    # Con il riuso si consumano solo i byte del record, non una voce slot.
    buf = make_page(1, 32, [(0, 0)])
    page = SlottedPage(buf)
    before = page.free_space()
    page.insert(b"XYZ")
    assert page.free_space() == before - len(b"XYZ")


def test_insert_reuses_the_first_free_slot() -> None:
    # Con più slot liberi si riusa il primo disponibile.
    buf = make_page(3, PAGE_SIZE, [(0, 0), (0, 0), (0, 0)])
    page = SlottedPage(buf)
    assert page.insert(b"a") == 0
    assert page.insert(b"b") == 1


# --- insert: pagina piena ---
def test_insert_raises_when_page_is_full(page: SlottedPage) -> None:
    # Riempita la pagina, un altro insert (con slot nuovo) solleva PageFullError.
    fill = PAGE_SIZE - HEADER_SIZE - SLOT_SIZE
    assert page.insert(b"A" * fill) == 0
    assert page.free_space() == 0
    with pytest.raises(PageFullError):
        page.insert(b"B")


def test_insert_fills_the_page_exactly(page: SlottedPage) -> None:
    # Un record della dimensione massima riempie la pagina senza sforare.
    fill = PAGE_SIZE - HEADER_SIZE - SLOT_SIZE
    page.insert(b"A" * fill)
    assert page.read(0) == b"A" * fill
    assert page.free_space() == 0


def test_insert_raises_on_full_page_even_with_a_free_slot() -> None:
    # C'è uno slot libero, ma zero spazio contiguo: non si può inserire nulla.
    buf = make_page(1, HEADER_SIZE + SLOT_SIZE, [(0, 0)])  # data_start=8 -> free_space=0
    page = SlottedPage(buf)
    assert page.free_space() == 0
    with pytest.raises(PageFullError):
        page.insert(b"x")


def test_insert_fills_exactly_reusing_a_free_slot() -> None:
    # Con uno slot libero, un record grande quanto lo spazio libero entra esatto.
    length = 8
    buf = make_page(1, HEADER_SIZE + SLOT_SIZE + length, [(0, 0)])  # free_space == length
    page = SlottedPage(buf)
    assert page.free_space() == length
    assert page.insert(b"A" * length) == 0
    assert page.free_space() == 0
    assert page.read(0) == b"A" * length


# --- insert: invarianti (property-based) ---
@given(st.lists(st.binary(min_size=1, max_size=30), min_size=1, max_size=30))
def test_insert_keeps_space_accounting(records: list[bytes]) -> None:
    # Dopo N insert, lo spazio libero è esattamente quello iniziale meno
    # (record + slot) di ogni record inserito.
    page = SlottedPage(bytearray(PAGE_SIZE))
    count = 0
    total = 0
    for record in records:
        try:
            page.insert(record)
        except PageFullError:
            break
        count += 1
        total += len(record)
    assert page.num_slots() == count
    expected_free = PAGE_SIZE - HEADER_SIZE - count * SLOT_SIZE - total
    assert page.free_space() == expected_free


@given(st.lists(st.binary(min_size=1, max_size=30), min_size=1, max_size=30))
def test_insert_then_read_round_trip(records: list[bytes]) -> None:
    # Ogni record inserito (finché c'è spazio) si rilegge identico dal suo slot.
    page = SlottedPage(bytearray(PAGE_SIZE))
    written: list[tuple[int, bytes]] = []
    for record in records:
        try:
            written.append((page.insert(record), record))
        except PageFullError:
            break
    for slot, record in written:
        assert page.read(slot) == record


def test_insert_packs_records_contiguously_from_the_end() -> None:
    # Gli offset dei record sono impacchettati dalla fine, senza buchi.
    buf = bytearray(PAGE_SIZE)
    page = SlottedPage(buf)
    lengths = [3, 5, 2, 1]
    for length in lengths:
        page.insert(b"A" * length)
    expected = PAGE_SIZE
    for index, length in enumerate(lengths):
        expected -= length
        offset, stored_length = struct.unpack_from("<HH", buf, HEADER_SIZE + index * SLOT_SIZE)
        assert (offset, stored_length) == (expected, length)


# --- delete ---
def test_delete_makes_the_slot_unreadable(page: SlottedPage) -> None:
    # Dopo il delete lo slot è un tombstone: leggerlo solleva.
    page.insert(b"AB")
    page.delete(0)
    with pytest.raises(SlotNotAllocatedError):
        page.read(0)


def test_delete_does_not_change_num_slots(page: SlottedPage) -> None:
    # Lo slot non viene rimosso: il numero di slot resta invariato.
    page.insert(b"AB")
    page.delete(0)
    assert page.num_slots() == 1


def test_delete_does_not_change_free_space(page: SlottedPage) -> None:
    # Il record diventa un buco: lo spazio contiguo disponibile non aumenta.
    page.insert(b"AB")
    before = page.free_space()
    page.delete(0)
    assert page.free_space() == before


def test_delete_does_not_affect_other_slots(page: SlottedPage) -> None:
    # Cancellare uno slot non tocca gli altri record.
    page.insert(b"aa")
    page.insert(b"bbb")
    page.insert(b"cccc")
    page.delete(1)
    assert page.read(0) == b"aa"
    assert page.read(2) == b"cccc"


def test_insert_reuses_a_slot_freed_by_delete(page: SlottedPage) -> None:
    # Uno slot liberato dal delete viene riusato, senza far crescere num_slots.
    page.insert(b"aa")
    page.insert(b"bb")
    page.delete(0)
    assert page.insert(b"XY") == 0
    assert page.num_slots() == 2
    assert page.read(0) == b"XY"


def test_delete_twice_raises(page: SlottedPage) -> None:
    # Cancellare due volte lo stesso slot è un errore evidente.
    page.insert(b"AB")
    page.delete(0)
    with pytest.raises(SlotNotAllocatedError):
        page.delete(0)


def test_delete_rejects_out_of_range(page: SlottedPage) -> None:
    with pytest.raises(SlotNotAllocatedError):
        page.delete(0)


def test_delete_rejects_negative_slot(page: SlottedPage) -> None:
    page.insert(b"AB")
    with pytest.raises(SlotNotAllocatedError):
        page.delete(-1)


# --- compact ---
def test_compact_keeps_live_records(page: SlottedPage) -> None:
    # Dopo la compaction tutti i record vivi si rileggono identici.
    page.insert(b"alpha")
    page.insert(b"beta")
    page.insert(b"gamma")
    page.delete(1)
    page.compact()
    assert page.read(0) == b"alpha"
    assert page.read(2) == b"gamma"


def test_compact_does_not_change_num_slots(page: SlottedPage) -> None:
    # Gli slot (anche quelli liberi) restano: num_slots non cambia.
    page.insert(b"alpha")
    page.insert(b"beta")
    page.delete(0)
    page.compact()
    assert page.num_slots() == 2


def test_compact_moves_all_free_space_to_the_end() -> None:
    # Dopo la compaction data_start = PAGE_SIZE meno la somma dei record vivi.
    buf = bytearray(PAGE_SIZE)
    page = SlottedPage(buf)
    page.insert(b"A" * 10)
    page.insert(b"B" * 20)
    page.insert(b"C" * 30)
    page.delete(1)
    page.compact()
    _, data_start = struct.unpack_from("<HH", buf, 0)
    assert data_start == PAGE_SIZE - (10 + 30)


def test_compact_all_slots_free_empties_the_data_area(page: SlottedPage) -> None:
    # Se non c'è più nessun record vivo, la zona dati torna tutta libera.
    page.insert(b"aa")
    page.insert(b"bb")
    page.delete(0)
    page.delete(1)
    page.compact()
    assert page.free_space() == PAGE_SIZE - HEADER_SIZE - 2 * SLOT_SIZE
    with pytest.raises(SlotNotAllocatedError):
        page.read(0)


def test_compact_allows_an_insert_that_did_not_fit_before(page: SlottedPage) -> None:
    # Frammentazione: il buco del delete non basta finché non si compatta.
    page.insert(b"A" * 100)
    page.insert(b"B" * 100)
    page.insert(b"C" * 100)
    page.delete(1)
    with pytest.raises(PageFullError):
        page.insert(b"D" * 3800)
    page.compact()
    assert page.insert(b"D" * 3800) == 1
    assert page.read(1) == b"D" * 3800
    assert page.read(0) == b"A" * 100
    assert page.read(2) == b"C" * 100


def test_compact_is_idempotent() -> None:
    # Compattare una pagina già compatta non cambia nulla.
    buf = bytearray(PAGE_SIZE)
    page = SlottedPage(buf)
    page.insert(b"alpha")
    page.insert(b"beta")
    page.delete(0)
    page.compact()
    state = buf[:]
    page.compact()
    assert buf[:] == state


@given(st.lists(st.binary(min_size=1, max_size=20), min_size=1, max_size=15))
def test_insert_delete_compact_preserves_survivors(records: list[bytes]) -> None:
    # Dopo cancellazioni e compaction, i record rimasti si rileggono identici
    # e i vivi sono impacchettati fino alla fine della pagina.
    buf = bytearray(PAGE_SIZE)
    page = SlottedPage(buf)
    inserted: list[tuple[int, bytes]] = []
    for record in records:
        try:
            inserted.append((page.insert(record), record))
        except PageFullError:
            break

    survivors: list[tuple[int, bytes]] = []
    for slot, record in inserted:
        if slot % 2 == 0:
            survivors.append((slot, record))
        else:
            page.delete(slot)

    page.compact()

    for slot, record in survivors:
        assert page.read(slot) == record
    _, data_start = struct.unpack_from("<HH", buf, 0)
    assert data_start == PAGE_SIZE - sum(len(record) for _, record in survivors)


# --- integrazione col PageManager ---
def test_insert_persists_through_page_manager(tmp_path: Path) -> None:
    # La pagina modificata in memoria, riscritta su disco, si rilegge identica.
    path = tmp_path / "db.bin"
    manager = PageManager(path)
    try:
        page_id = manager.allocate_page()
        data = manager.read_page(page_id)
        page = SlottedPage(data)
        page.insert(b"hello")
        page.insert(b"world!")
        manager.write_page(page_id, data)
    finally:
        manager.close()

    reopened_manager = PageManager(path)
    try:
        data = reopened_manager.read_page(page_id)
        page = SlottedPage(data)
        assert page.read(0) == b"hello"
        assert page.read(1) == b"world!"
    finally:
        reopened_manager.close()
