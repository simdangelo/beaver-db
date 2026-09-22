# 03 — Buffer pool: la cache che evita il disco

## Che modulo è e dove si colloca

Il page manager legge e scrive pagine intere, ma il disco è lentissimo. Il modulo
3 costruisce la **cache di pagine** tra gli access method e il page manager: il
**buffer pool**. Da qui in poi la slotted page non chiamerà più `read_page`
/`write_page`: riceverà una pagina dal pool, la modificherà in memoria e la
unpinnerà. Il concetto generale è nella wiki
[`../wiki/buffer-pool.md`](../wiki/buffer-pool.md).

## Le decisioni prese

Le decisioni sono nell'ADR
[`../adr/0003-buffer-pool-lru.md`](../adr/0003-buffer-pool-lru.md):

- **Politica di rimpiazzo: LRU** (era la scelta rimandata da AGENTS.md §3).
  Clock resta un'alternativa per una seconda iterazione.
- **Capacità configurabile** nel costruttore: è il parametro che rende testabili
  le eviction.
- **API**: `fetch_page`, `unpin_page`, `new_page`, `flush_page`, `flush_all`.
- **Page table** come mappa `page_id → Frame` (riferimento diretto, non indice).
- **Errori**: `BufferPoolFullError` (nessun frame evincibile) e
  `PageNotPinnedError` (pagina non nel pool o non pinnata).
- **Solo il buffer pool tocca il disco** sopra il page manager.

Due decisioni sono state raffinate durante l'implementazione: la page table mappa
direttamente al `Frame` (non a un indice — così il lookup non dipende dalla
posizione nella lista) e `new_page()` restituisce `tuple[int, bytearray]`, id e
buffer pinnato, per evitare un doppio pin.

## Le modifiche al codice

`src/beaver_db/buffer/buffer_pool.py` — il cuore del modulo:

- `Frame`: una dataclass con `page_id` (`None` = libero), `data`, `pin_count`,
  `dirty`, `last_used`.
- `BufferPoolManager.__init__`: crea `capacity` frame distinti con un buffer da
  `PAGE_SIZE` ciascuno, la page table e l'orologio globale.
- `fetch_page`: hit → pinna e aggiorna la recenza; miss → frame libero o eviction
  LRU, flush della vittima sporca, lettura della pagina, installazione e pin.
- `unpin_page(page_id, dirty)`: decrementa il pin; alza il dirty solo se richiesto
  (non lo azzera mai).
- `flush_page` / `flush_all`: riscrivono le pagine sporche e azzerano il flag.
- `new_page`: alloca una pagina nuova col page manager e la restituisce pinnata.

`src/beaver_db/exceptions.py` — aggiunte `BufferPoolFullError` e
`PageNotPinnedError`.

`tests/buffer/test_buffer_pool.py` — **18 test**, con un `CountingPageManager`
(sottoclasse che conta `read_page`/`write_page`) per verificare hit, miss e
write-back. Coprono fetch, pin/unpin, eviction LRU, dirty, flush e `new_page`,
più un'integrazione con la slotted page.

`docs/wiki/buffer-pool.md` e `docs/adr/0003-buffer-pool-lru.md` — il concetto e la
decisione.

## Le insidie incontrate

**`[Frame(...)] * capacity` crea lo stesso frame ripetuto.** In Python,
moltiplicare una lista con un oggetto dentro ripete il **riferimento**, non
l'oggetto: `capacity` frame che erano tutti lo stesso. Risolto con una
comprehension e un `bytearray(PAGE_SIZE)` distinto per ognuno.

**Il bug dello zero, in tre salse.** Lo stesso errore è comparso più volte:
- `if i and free_frame:` sul frame libero in posizione `0` → ramo saltato;
- `sorted(...)[-1]` per la vittima → sceglieva la pagina **più** recente invece
  della meno recente;
- `if frame.page_id and frame.dirty:` in `flush_all` → la **pagina 0** (id
  valido, ma falsy) non veniva mai flushatа.
La lezione: con `0` valido (indici, page id) il controllo giusto è `is not None`,
mai la verità dell'intero.

**L'eviction non riscriveva la vittima sporca.** Il ramo sostituiva il frame
senza controllare `dirty`: una pagina modificata veniva buttata via. Aggiunto il
flush condizionale prima di riusare il frame.

**LRU con il contatore sbagliato.** `last_used` era un contatore **per frame**
(`frame.last_used += 1`): non produce un ordinamento di recenza valido. Serve un
**orologio globale** (`self._clock`), aggiornato a ogni accesso.

**Leggere prima di avere un frame.** `read_page` era chiamato prima di sapere se
esisteva un frame, facendo I/O a vuoto quando il pool era pieno e tutto pinnato.
Spostato dopo la scelta (e dopo il flush della vittima).

**Errori di tipo `int | None`.** `page_id` di un frame è `int | None` (libero),
ma `write_page`/`pop` vogliono `int`. Risolto restringendo il tipo con un
`assert victim_page_id is not None` dopo aver filtrato i frame occupati.

**Importato un test nel codice di produzione.** Era comparso
`from tests.storage.test_slotted_page import page` (una fixture pytest) dentro
`src/`: dipendenza sbagliata, rimossa subito.

**Due test miei sbagliati.** I primi test di eviction fallivano: dimenticavo
l'unpin dopo il fetch, quindi la pagina restava **pinnata** e non evincibile.
Non era un bug del codice ma dei test — e la lezione è che il pin è reale: una
pagina pinnata non si butta fuori.

## Le verifiche fatte

- `uv run pytest` → **99 passed** (18 buffer pool, 42 slotted page, 38 page
  manager, 1 smoke test)
- `uv run ruff check .` → *All checks passed!*
- `uv run ruff format --check .` → tutti i file formattati
- `uv run basedpyright` → **0 errori**

Il test più prezioso è quello di **LRU**: con due frame, si riusa la pagina meno
recente e non quella appena usata, verificato contando le letture dal disco.

## Cosa è rimasto aperto

- **`new_page` su pool pieno**: se tutte le pagine sono pinnate, la pagina viene
  comunque allocata su disco prima che `fetch_page` fallisca, e resta lì. Per ora
  accettato.
- **Clock** come politica alternativa: rimandata a una eventuale seconda
  iterazione.
- **Nessun `close()` del pool**: oggi chi lo usa chiama `flush_all()` e chiude il
  page manager a mano. Un metodo di chiusura esplicito può servire più avanti.
- **Il modulo 4 (heap file)** è il prossimo: una tabella sopra le pagine, con
  insert, scan sequenziale e Record ID.
