# 02 — Slotted page: record a lunghezza variabile dentro una pagina

## Che modulo è e dove si colloca

Il modulo 1 ci ha dato contenitori identici da 4096 byte, ma sapeva muoverli
solo come blocchi opachi. Il modulo 2 costruisce **dentro** la pagina la
struttura che ospita record a lunghezza variabile: header, slot directory,
tombstone per la cancellazione e compaction. È il primo vero access method e
poggia interamente sul page manager. Il concetto generale è nella wiki
[`../wiki/slotted-page.md`](../wiki/slotted-page.md).

## Le decisioni prese

**Il formato della pagina** è fissato nell'ADR
[`../adr/0002-formato-slotted-page.md`](../adr/0002-formato-slotted-page.md):
header di 4 byte (`num_slots`, `data_start`) e slot di 4 byte (`offset`,
`length`), interi senza segno da 2 byte in little-endian, formato `"<HH"`.
`data_start == 0` segnala una pagina non formattata; `offset == 0` è un record
libero (tombstone). La lunghezza sta nello slot, quindi il record è un **blob di
byte grezzo** senza header di tupla: bitmap dei NULL e tipi di colonna arriveranno
col modulo catalog.

**Compaction esplicita e pigra** (stile PostgreSQL): non automatica sugli
insert; `free_space()` misura solo lo spazio contiguo, quindi un insert può
fallire con dei buchi finché non si chiama `compact()`.

**La tassonomia di errori si allarga**: a `InvalidPageSizeError` si aggiungono
`SlotNotAllocatedError` (slot libero o fuori range) e `PageFullError` (la pagina
non ha spazio contiguo sufficiente).

**Chiarimento architetturale sui layer**: la slotted page lavora su pagine
**in memoria** e non fa I/O; è il page manager a toccare il disco. La regola è
stata resa esplicita in AGENTS.md §5 e raccontata nella wiki.

## Le modifiche al codice

`src/beaver_db/storage/slotted_page.py` — la classe `SlottedPage`:

- costanti `HEADER_SIZE`, `SLOT_SIZE`, `_HEADER_FORMAT`, `_SLOT_FORMAT`;
- `__init__`: valida la dimensione del buffer e formatta la pagina se nuova;
- helper `_read_header`/`_write_header` e `_read_slot`/`_write_slot` (l'offset
  dell'header e quello degli slot stanno in un posto solo);
- `num_slots`, `free_space`;
- `read`: valida lo slot, solleva se libero, restituisce una **copia** (`bytes`)
  del record;
- `insert`: cerca uno slot libero da riusare o ne aggiunge uno, controlla lo
  spazio, scrive il record dalla fine verso l'inizio, aggiorna slot e header;
- `delete`: tombstone (marca lo slot libero senza toccare i byte);
- `compact`: copia fuori i record vivi e li ripacca dalla fine, aggiornando gli
  offset; i numeri di slot non cambiano.

`src/beaver_db/exceptions.py` — aggiunte `SlotNotAllocatedError` e `PageFullError`.

`tests/storage/test_slotted_page.py` — **42 test**, di cui tre property-based:
coprono header, lettura, inserimento (base, riuso, pagina piena, riempimento
esatto), cancellazione, compaction (incluso il caso di frammentazione) e
un'integrazione col page manager.

`docs/wiki/slotted-page.md` — il concetto, arricchito col **formato concreto in
byte** e con i **disegni della pagina passo per passo** (formattazione,
inserimento, cancellazione, compaction).

`docs/knowledge/struct-e-buffer.md` — esteso con la numerazione a più byte e
l'ordine dei byte, e con la distinzione `struct` (campi a formato fisso) vs
slicing (payload a lunghezza variabile).

## Le insidie incontrate

**`insert` non aggiornava l'header.** Scriveva record e slot ma non riscriveva
`num_slots`/`data_start`. Conseguenza: `free_space()` non calava e il prossimo
insert ripartiva dallo stesso `data_start`, **sovrascrivendo il record appena
inserito**; lo slot nuovo non contava, quindi `read` su di esso falliva. Risolto
con `_write_header(new_num_slots, data_start - length)`, dove
`new_num_slots = max(old_num_slots, slot_id + 1)` copre sia il riuso sia lo slot
nuovo.

**Off-by-one nel range di `_read_slot`.** La condizione era `slot_id >
num_slots()`: avrebbe accettato `slot_id == num_slots`. Corretta in `>=`.
Mancavano inoltre la lettura dei campi e il `return`.

**`_write_slot` usava il letterale `"<HH"`** invece di `_SLOT_FORMAT`, e senza
l'annotazione di `slot_id`.

**La prima `compact` era rotta.** Indicizzava `survived_tuple[i]` con un `i` non
più definito, usava uno slice invertito (`PAGE_SIZE : PAGE_SIZE - length`, che è
vuoto), non copiava i record prima di spostarli (rischio di calpestare dati vivi)
e non aggiornava né gli slot né l'header. Riscritta con il **copia-fuori prima di
scrivere** e un cursore che scende da `PAGE_SIZE`.

**Leggere un record non è un lavoro da `struct`.** Il payload ha lunghezza nota
solo a runtime e non ha formato: si legge con lo **slicing**, non con `struct`
(che serve ai campi a formato fisso). Chiarito nella wiki di `struct`.

**Il record vuoto.** Un insert di `b""` è lecito e si rilegge come `b""`:
comportamento documentato da un test, non un caso da nascondere.

**Piccole cose di forma**: mancavano le due righe vuote tra le classi in
`exceptions.py` (`E302`), `compact` era senza `-> None`, e qualche messaggio
d'errore era in inglese sgrammaticato.

**I disegni della wiki.** La prima versione rappresentava la pagina come una
griglia uniforme di parole da 4 byte, che faceva sembrare lo spazio libero
diviso in sezioni. Ridisegnata a **scatole di dimensione reale** (header, slot,
spazio libero come blocco unico, dati in coda), con le celle dei dati
etichettate come `tupla 0`, `tupla 1` e separate visivamente.

## Le verifiche fatte

- `uv run pytest` → **81 passed** (42 in `tests/storage/test_slotted_page.py`,
  38 in `tests/storage/test_page_manager.py`, 1 smoke test).
- `uv run ruff check .` → *All checks passed!*
- `uv run ruff format --check .` → tutti i file formattati.
- `uv run basedpyright` → **0 errori**.

Il test di compaction più prezioso è quello di **frammentazione**: tre record da
100 byte, cancellazione di quello centrale, un record grande non entra
(`PageFullError`), `compact()`, e ora entra. È il caso che distingue una
compaction vera da una finta.

## Cosa è rimasto aperto

- **Nessun header di tupla.** Il record è un blob: niente bitmap dei NULL né
  tipi di colonna. Arriveranno col modulo catalog.
- **Compaction solo esplicita.** `free_space()` misura lo spazio contiguo; non
  esiste una nozione di "spazio totale recuperabile" oltre ai buchi. Un
  auto-compact resta un'opzione da valutare.
- **Il modulo 3 (buffer pool)** è il prossimo: la cache di pagine tra access
  method e page manager, con pin/unpin, dirty flag, flush ed eviction.
