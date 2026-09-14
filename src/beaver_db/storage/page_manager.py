from pathlib import Path
from typing import BinaryIO

from beaver_db.exceptions import CorruptFileError, InvalidPageSizeError, PageNotAllocatedError

PAGE_SIZE = 4096


def page_offset(page_id: int) -> int:
    return page_id * PAGE_SIZE


def hex_dump(data: bytes | bytearray) -> str:
    lines = []

    for offset in range(0, len(data), 16):
        chunk = data[offset : offset + 16]

        hex_part = " ".join(f"{byte:02x}" for byte in chunk[:8])
        hex_part += "  "
        hex_part += " ".join(f"{byte:02x}" for byte in chunk[8:])

        # Mantiene allineata la colonna ASCII anche per l'ultima riga
        hex_part = f"{hex_part:<48}"

        ascii_part = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in chunk)

        lines.append(f"{offset:08x}  {hex_part}  |{ascii_part:<16}|")

    return "\n".join(lines)


class PageManager:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        mode = "r+b" if self._path.exists() else "w+b"
        file_size = self._file_size()
        if file_size % PAGE_SIZE != 0:
            raise CorruptFileError(
                f"file size {file_size} is not a multiple of PAGE_SIZE ({PAGE_SIZE})"
            )
        self._file: BinaryIO = open(self._path, mode)  # noqa: SIM115

    def _file_size(self) -> int:
        # Option A chiede al filesystem: "quanto è grande questo file su disco?".
        # Vede solo i byte già flushati. Se write_page scrive tramite l'handle senza
        # flush, num_pages() può restare indietro di una pagina.
        if not self._path.exists():
            return 0
        return self._path.stat().st_size

        # Option B (alternativa): chiede all'handle aperto qual è la sua fine logica.
        # Il seek fa anche flush, quindi include i byte scritti ma non ancora persistiti.
        # Non è usabile qui: __init__ chiama _file_size() prima di aprire l'handle.
        # from io import SEEK_END
        # self._file.seek(0, SEEK_END)
        # return self._file.tell()

    def num_pages(self) -> int:
        return self._file_size() // PAGE_SIZE

    def allocate_page(self) -> int:
        new_page_id = self.num_pages()
        self._file.seek(page_offset(new_page_id))
        page = bytes(PAGE_SIZE)
        written_bytes = self._file.write(page)
        if written_bytes != len(page):
            raise OSError(f"Written bytes should be {len(page)}, but it's {written_bytes}")
        self._file.flush()  # questo serve altrimenti num_pages diventa inattendibile
        return new_page_id

    def read_page(self, page_id: int) -> bytearray:
        count = self.num_pages()
        if page_id < 0 or page_id > count - 1:
            raise PageNotAllocatedError(f"page {page_id} is not allocated (num_pages={count})")
        self._file.seek(page_offset(page_id))
        read_bytes = self._file.read(PAGE_SIZE)
        return bytearray(read_bytes)

    def write_page(self, page_id: int, data: bytes | bytearray) -> None:
        count = self.num_pages()
        if page_id < 0 or page_id > count - 1:
            raise PageNotAllocatedError(f"page {page_id} is not allocated (num_pages={count})")
        if len(data) != PAGE_SIZE:
            raise InvalidPageSizeError(f"data length {len(data)} != PAGE_SIZE ({PAGE_SIZE}")

        self._file.seek(page_offset(page_id))
        written_bytes = self._file.write(data)
        if written_bytes != len(data):
            raise OSError(f"Written bytes should be {len(data)}, but it's {written_bytes}")
        self._file.flush()

    def close(self) -> None:
        self._file.close()
