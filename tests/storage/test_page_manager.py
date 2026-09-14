import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from beaver_db.exceptions import CorruptFileError, InvalidPageSizeError, PageNotAllocatedError
from beaver_db.storage.page_manager import PAGE_SIZE, PageManager, hex_dump, page_offset


@pytest.fixture
def pm(tmp_path: Path) -> Iterator[PageManager]:
    # Fixture: un PageManager su un file nuovo, chiuso automaticamente a fine test.
    manager = PageManager(tmp_path / "db.bin")
    yield manager
    manager.close()


# --- page_offset: la mappa page_id -> offset nel file ---
def test_page_zero_starts_at_zero() -> None:
    # La prima pagina comincia all'offset 0.
    assert page_offset(0) == 0


def test_first_pages_have_fixed_stride() -> None:
    # Le prime pagine distano l'una dall'altra esattamente PAGE_SIZE.
    assert page_offset(1) == PAGE_SIZE
    assert page_offset(2) == 2 * PAGE_SIZE


@given(st.integers(min_value=0, max_value=1_000_000))
def test_offset_is_page_id_times_page_size(page_id: int) -> None:
    # Proprietà: per qualunque id, offset = id * PAGE_SIZE.
    assert page_offset(page_id) == page_id * PAGE_SIZE


@given(st.integers(min_value=0, max_value=1_000_000))
def test_consecutive_pages_are_adjacent(page_id: int) -> None:
    # Proprietà: due pagine consecutive sono adiacenti, senza buchi né sovrapposizioni.
    first_byte = page_offset(page_id)
    next_page_first_byte = page_offset(page_id + 1)
    last_byte_included = next_page_first_byte - 1
    assert last_byte_included - first_byte + 1 == PAGE_SIZE


# --- hex_dump: stampa dei byte a gruppi di 16, con offset e ASCII ---
def test_hex_dump_empty_data() -> None:
    # Con input vuoto non c'è nessuna riga da stampare.
    assert hex_dump(b"") == ""


def test_hex_dump_single_full_line() -> None:
    # 16 byte stanno in una sola riga, che parte dall'offset 0.
    lines = hex_dump(bytes(16)).splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("00000000")


def test_hex_dump_offsets_increment_by_16() -> None:
    # Ogni riga mostra l'offset di inizio, che cresce di 16.
    lines = hex_dump(bytes(32)).splitlines()
    assert lines[0].startswith("00000000")
    assert lines[1].startswith("00000010")


def test_hex_dump_non_printable_bytes_become_dots() -> None:
    # I byte non stampabili diventano punti nella colonna ASCII.
    # 0x00 non stampabile, 0x41 = 'A', 0x20 = spazio
    line = hex_dump(bytes([0x00, 0x41, 0x20])).splitlines()[0]
    assert ".A " in line


def test_hex_dump_last_line_can_be_short() -> None:
    # L'ultima riga può avere meno di 16 byte (20 = 16 + 4).
    lines = hex_dump(bytes(20)).splitlines()
    assert len(lines) == 2


def test_hex_dump_golden() -> None:
    # Fissa il formato esatto di una riga piena: è la regressione sul layout.
    data = b"Hello!" + bytes(10)
    expected = "00000000  48 65 6c 6c 6f 21 00 00  00 00 00 00 00 00 00 00  |Hello!..........|"
    assert hex_dump(data) == expected


@given(st.binary(max_size=64))
def test_hex_dump_line_count(data: bytes) -> None:
    # Proprietà: il numero di righe è ceil(len / 16).
    expected_lines = (len(data) + 15) // 16
    assert len(hex_dump(data).splitlines()) == expected_lines


# --- __init__: apertura del file e rifiuto dei file corrotti ---
def test_new_manager_rejects_partial_page(tmp_path: Path) -> None:
    # Una dimensione non multipla di PAGE_SIZE segnala un file corrotto e va rifiutata.
    path = tmp_path / "db.bin"
    path.write_bytes(bytes(3 * PAGE_SIZE + 1))
    with pytest.raises(CorruptFileError):
        PageManager(path)


# --- num_pages: quante pagine contiene il file ---
def test_num_pages_empty_file(pm: PageManager) -> None:
    # Un file nuovo non contiene pagine.
    assert pm.num_pages() == 0


def test_num_pages_counts_whole_pages(tmp_path: Path) -> None:
    # La dimensione viene convertita in un numero intero di pagine.
    path = tmp_path / "db.bin"
    path.write_bytes(bytes(3 * PAGE_SIZE))
    pm = PageManager(path)
    try:
        assert pm.num_pages() == 3
    finally:
        pm.close()


@given(st.integers(min_value=1, max_value=50))
def test_num_pages_equals_number_of_allocations(count: int) -> None:
    # Proprietà: dopo N allocazioni num_pages vale N (coglie anche un flush mancante).
    with tempfile.TemporaryDirectory() as tmp:
        manager = PageManager(Path(tmp) / "db.bin")
        try:
            for _ in range(count):
                manager.allocate_page()
            assert manager.num_pages() == count
        finally:
            manager.close()


# --- allocate_page: crescita del file e id progressivi ---
def test_allocate_page_first_id_is_zero(pm: PageManager) -> None:
    # La prima pagina allocata ha id 0 ed è subito visibile a num_pages.
    assert pm.allocate_page() == 0
    assert pm.num_pages() == 1


def test_allocate_page_returns_sequential_ids(pm: PageManager) -> None:
    # Gli id crescono di uno a ogni allocazione.
    assert pm.allocate_page() == 0
    assert pm.allocate_page() == 1
    assert pm.allocate_page() == 2
    assert pm.num_pages() == 3


def test_allocate_page_grows_file_by_one_page(pm: PageManager, tmp_path: Path) -> None:
    # Ogni allocazione fa crescere il file esattamente di una pagina.
    pm.allocate_page()
    assert (tmp_path / "db.bin").stat().st_size == PAGE_SIZE


def test_allocate_page_writes_a_zero_filled_page(pm: PageManager, tmp_path: Path) -> None:
    # La pagina nuova nasce riempita di zeri.
    pm.allocate_page()
    assert (tmp_path / "db.bin").read_bytes() == bytes(PAGE_SIZE)


def test_allocate_page_appends_without_touching_existing_pages(tmp_path: Path) -> None:
    # L'allocazione aggiunge in coda e non tocca le pagine già esistenti.
    path = tmp_path / "db.bin"
    path.write_bytes(b"A" * PAGE_SIZE + b"B" * PAGE_SIZE)
    manager = PageManager(path)
    try:
        assert manager.allocate_page() == 2
        content = path.read_bytes()
        assert content[:PAGE_SIZE] == b"A" * PAGE_SIZE
        assert content[PAGE_SIZE : 2 * PAGE_SIZE] == b"B" * PAGE_SIZE
    finally:
        manager.close()


def test_allocate_page_persists_across_reopen(tmp_path: Path) -> None:
    # Le pagine allocate sopravvivono alla chiusura e riapertura del file.
    path = tmp_path / "db.bin"
    first = PageManager(path)
    first.allocate_page()
    first.close()

    second = PageManager(path)
    try:
        assert second.num_pages() == 1
        assert second.allocate_page() == 1
    finally:
        second.close()


# --- read_page: lettura di una pagina per id ---
def test_read_page_returns_exactly_page_size(pm: PageManager) -> None:
    # Restituisce un bytearray lungo esattamente PAGE_SIZE.
    pm.allocate_page()
    page = pm.read_page(0)
    assert isinstance(page, bytearray)
    assert len(page) == PAGE_SIZE


def test_read_page_returns_zero_filled_allocated_page(pm: PageManager) -> None:
    # Una pagina allocata e mai scritta si legge come tutti zeri.
    pm.allocate_page()
    assert pm.read_page(0) == bytes(PAGE_SIZE)


def test_read_page_reads_the_right_offset(tmp_path: Path) -> None:
    # Legge i byte alla pagina giusta, non quelli della vicina.
    path = tmp_path / "db.bin"
    path.write_bytes(b"A" * PAGE_SIZE + b"B" * PAGE_SIZE)
    pm = PageManager(path)
    try:
        assert pm.read_page(0) == b"A" * PAGE_SIZE
        assert pm.read_page(1) == b"B" * PAGE_SIZE
    finally:
        pm.close()


def test_read_page_rejects_unallocated_page(pm: PageManager) -> None:
    # Chiedere una pagina che non esiste solleva PageNotAllocatedError.
    with pytest.raises(PageNotAllocatedError):
        pm.read_page(0)


def test_read_page_rejects_out_of_range(pm: PageManager) -> None:
    # Un id oltre il range allocato solleva PageNotAllocatedError.
    pm.allocate_page()
    with pytest.raises(PageNotAllocatedError):
        pm.read_page(1)


def test_read_page_rejects_negative_page_id(pm: PageManager) -> None:
    # Un id negativo solleva PageNotAllocatedError.
    pm.allocate_page()
    with pytest.raises(PageNotAllocatedError):
        pm.read_page(-1)


def test_read_page_does_not_modify_the_file(tmp_path: Path) -> None:
    # Leggere una pagina non altera i byte del file.
    path = tmp_path / "db.bin"
    path.write_bytes(b"A" * PAGE_SIZE)
    pm = PageManager(path)
    try:
        before = path.read_bytes()
        pm.read_page(0)
        assert path.read_bytes() == before
    finally:
        pm.close()


@given(st.integers(min_value=1, max_value=20))
def test_read_page_always_returns_full_page(count: int) -> None:
    # Proprietà: ogni pagina nel range si legge per intero, qualunque sia l'id.
    with tempfile.TemporaryDirectory() as tmp:
        manager = PageManager(Path(tmp) / "db.bin")
        try:
            for _ in range(count):
                manager.allocate_page()
            for page_id in range(count):
                assert len(manager.read_page(page_id)) == PAGE_SIZE
        finally:
            manager.close()


# --- write_page: scrittura in una pagina esistente e round-trip con read_page ---
def test_write_page_updates_page_content(pm: PageManager) -> None:
    # Scrivere cambia il contenuto della pagina.
    pm.allocate_page()
    pm.write_page(0, b"A" * PAGE_SIZE)
    assert pm.read_page(0) == b"A" * PAGE_SIZE


def test_write_page_overwrites_previous_content(pm: PageManager) -> None:
    # Una nuova scrittura sostituisce completamente la precedente.
    pm.allocate_page()
    pm.write_page(0, b"A" * PAGE_SIZE)
    pm.write_page(0, b"B" * PAGE_SIZE)
    assert pm.read_page(0) == b"B" * PAGE_SIZE


def test_write_page_does_not_change_num_pages(pm: PageManager) -> None:
    # Sovrascrivere una pagina non fa crescere il file.
    pm.allocate_page()
    pm.write_page(0, b"A" * PAGE_SIZE)
    assert pm.num_pages() == 1


def test_write_page_rejects_wrong_length(pm: PageManager) -> None:
    # Dati più corti o più lunghi di PAGE_SIZE sono rifiutati.
    pm.allocate_page()
    with pytest.raises(InvalidPageSizeError):
        pm.write_page(0, b"short")
    with pytest.raises(InvalidPageSizeError):
        pm.write_page(0, bytes(PAGE_SIZE + 1))


def test_write_page_rejects_unallocated_page(pm: PageManager) -> None:
    # Scrivere su una pagina inesistente solleva PageNotAllocatedError.
    pm.allocate_page()
    with pytest.raises(PageNotAllocatedError):
        pm.write_page(1, bytes(PAGE_SIZE))


def test_write_page_rejects_negative_page_id(pm: PageManager) -> None:
    # Un id negativo solleva PageNotAllocatedError.
    pm.allocate_page()
    with pytest.raises(PageNotAllocatedError):
        pm.write_page(-1, bytes(PAGE_SIZE))


def test_write_page_does_not_spill_into_next_page(pm: PageManager) -> None:
    # Scrivere una pagina non sfora nella pagina successiva.
    pm.allocate_page()
    pm.allocate_page()
    pm.write_page(0, b"A" * PAGE_SIZE)
    assert pm.read_page(1) == bytes(PAGE_SIZE)


def test_write_page_persists_across_reopen(tmp_path: Path) -> None:
    # I dati scritti sopravvivono alla chiusura e riapertura del file.
    path = tmp_path / "db.bin"
    first = PageManager(path)
    first.allocate_page()
    first.write_page(0, b"X" * PAGE_SIZE)
    first.close()

    second = PageManager(path)
    try:
        assert second.read_page(0) == b"X" * PAGE_SIZE
    finally:
        second.close()


# PAGE_SIZE è fissa per progetto: l'input minimo di questo test è 4096 byte e
# non è riducibile, quindi sopprimiamo il health check "large_base_example".
@given(st.binary(min_size=PAGE_SIZE, max_size=PAGE_SIZE))
@settings(suppress_health_check=[HealthCheck.large_base_example])
def test_write_read_round_trip(data: bytes) -> None:
    # Proprietà: scrivere e poi rileggere restituisce esattamente gli stessi byte.
    with tempfile.TemporaryDirectory() as tmp:
        manager = PageManager(Path(tmp) / "db.bin")
        try:
            manager.allocate_page()
            manager.write_page(0, data)
            assert manager.read_page(0) == data
        finally:
            manager.close()
