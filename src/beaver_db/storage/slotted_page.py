import struct

from beaver_db.exceptions import InvalidPageSizeError, PageFullError, SlotNotAllocatedError
from beaver_db.storage.page_manager import PAGE_SIZE

HEADER_SIZE = 4
SLOT_SIZE = 4
_HEADER_FORMAT = "<HH"
_SLOT_FORMAT = "<HH"


class SlottedPage:
    def __init__(self, data: bytearray) -> None:
        if len(data) != PAGE_SIZE:
            raise InvalidPageSizeError(f"page buffer must be {PAGE_SIZE} bytes, got {len(data)}")
        self._data = data

        _, data_start = self._read_header()
        if data_start == 0:
            """
            Pagina nuova (tutta zeri): va formattata prima dell'uso.
            Formattare significa riscrivere l'header allo stato iniziale senza toccare
            i byte dei dati: i byte dei vecchi record restano nel buffer, ma sono fuori
            dalla zona usata e quindi ignorati
            """
            self._write_header(num_slots=0, data_start=PAGE_SIZE)

    def _read_header(self) -> tuple[int, int]:
        "Leggere l'header di una pagina è esattamente un unpack_from all'offset 0"
        return struct.unpack_from(_HEADER_FORMAT, self._data, 0)

    def _write_header(self, num_slots: int, data_start: int) -> None:
        struct.pack_into(_HEADER_FORMAT, self._data, 0, num_slots, data_start)

    def num_slots(self) -> int:
        num_slots, _ = self._read_header()
        return num_slots

    def free_space(self) -> int:
        _, data_start = self._read_header()
        return data_start - (HEADER_SIZE + self.num_slots() * SLOT_SIZE)

    def _read_slot(self, slot_id: int) -> tuple[int, int]:
        if slot_id < 0 or slot_id >= self.num_slots():
            raise SlotNotAllocatedError(f"slot {slot_id} is out of range")
        slot_offset = HEADER_SIZE + slot_id * SLOT_SIZE
        offset, length = struct.unpack_from(_SLOT_FORMAT, self._data, slot_offset)
        return offset, length

    def read(self, slot_id: int) -> bytes:
        offset, length = self._read_slot(slot_id)
        if offset == 0:
            raise SlotNotAllocatedError(f"slot {slot_id} is free")
        return bytes(self._data[offset : offset + length])

    def _write_slot(self, slot_id: int, offset: int, length: int) -> None:
        struct.pack_into(
            _SLOT_FORMAT, self._data, HEADER_SIZE + slot_id * SLOT_SIZE, offset, length
        )

    def insert(self, record: bytes) -> int:
        length = len(record)
        old_num_slots = self.num_slots()

        slot_id = None
        for candidate in range(old_num_slots):
            offset, _ = self._read_slot(candidate)
            if offset == 0:  # slot libero: tombstone
                slot_id = candidate
                if length > self.free_space():
                    # lo spazio per lo slot gia esiste, quindi devo controllare solo lo spazio per
                    # la tupla di bytes
                    raise PageFullError(
                        f"Free space: {self.free_space()}; requested free space: {len(record)}"
                    )
                break

        if slot_id is None:
            slot_id = old_num_slots
            if SLOT_SIZE + length > self.free_space():
                raise PageFullError(
                    f"Free space: {self.free_space()}; requested free space: {len(record)}"
                )

        _, data_start = self._read_header()
        # devo scrivere verso "l'indietro"
        self._data[data_start - length : data_start] = record

        self._write_slot(slot_id, data_start - length, length)

        # aggiorna header
        new_num_slots = max(old_num_slots, slot_id + 1)
        self._write_header(new_num_slots, data_start - length)
        return slot_id

    def delete(self, slot_id: int) -> None:
        offset, _ = self._read_slot(slot_id)
        if offset == 0:
            raise SlotNotAllocatedError(f"slot {slot_id} is already free")

        self._write_slot(slot_id, 0, 0)

    def compact(self) -> None:
        # copia fuori i record vivi
        live: list[tuple[int, bytes]] = []
        for slot_id in range(self.num_slots()):
            offset, _ = self._read_slot(slot_id)
            if offset != 0:
                live.append((slot_id, self.read(slot_id)))

        # spostai alla fine
        cursor = PAGE_SIZE
        for slot_id, record in live:
            cursor -= len(record)
            self._data[cursor : cursor + len(record)] = record
            self._write_slot(slot_id, cursor, len(record))

        # aggiorna l'header: il num slots non cambia, ma cambia solo il data_start
        self._write_header(self.num_slots(), cursor)
