# 0003 — Buffer pool: LRU e API

- **Status**: accepted
- **Data**: 2026-09-12

## Context

Il **buffer pool** è la cache di pagine tra gli access method e il page manager
(il concetto è nella wiki [`../wiki/buffer-pool.md`](../wiki/buffer-pool.md)).
La politica di eviction era una scelta rimandata esplicitamente a questo modulo
(AGENTS.md §3). Serve fissare: politica di rimpiazzo, capacità, API, strutture
dati, gestione degli errori e collocazione del codice.

## Decision

- **Politica di rimpiazzo: LRU** (Least Recently Used). Si evince la pagina
  usata meno di recente, tra quelle con pin count `0`.
- **Collocazione**: `src/beaver_db/buffer/buffer_pool.py`, classe
  `BufferPoolManager`.
- **Costruttore**: `BufferPoolManager(page_manager, capacity)`. La capacità
  (numero di frame) è il parametro didattico che rende testabili le eviction.
- **Frame**: `capacity` frame, ognuno con un buffer (`bytearray` da `PAGE_SIZE`),
  `page_id`, `pin_count`, `dirty` e un marcatore di recenza (`last_used`, un
  contatore che cresce a ogni accesso).
- **Page table**: una mappa `page_id → frame` (riferimento diretto al frame).
- **API**:
  - `fetch_page(page_id) -> bytearray`: hit → pinna e restituisce; miss → carica
    in un frame (evict se serve), pinna e restituisce.
  - `unpin_page(page_id, dirty: bool) -> None`: decrementa il pin; se `dirty`,
    marca la pagina sporca.
  - `new_page() -> tuple[int, bytearray]`: alloca una pagina nuova tramite il page
    manager e la restituisce pinnata (id e buffer).
  - `flush_page(page_id) -> None` e `flush_all() -> None`: riscrivono su disco
    le pagine sporche.
- **Errori**: una pagina non allocata fa sollevare `PageNotAllocatedError` al
  page manager; nessun frame evincibile (tutti pinnati) solleva una nuova
  `BufferPoolFullError`.
- **Solo il buffer pool tocca il disco** (sopra il page manager): gli access
  method ricevono pagine dal pool.

## Alternatives considered

- **Clock** invece di LRU: approssimazione più economica (reference bit +
  lancetta), tipica dei sistemi reali, ma con più sottigliezza implementativa.
  Rimandata come seconda iterazione: prima LRU, che è più didattica e più
  semplice da testare.
- **Nessuna cache** (access method che chiamano direttamente il page manager):
  scartata, annullerebbe il modulo.
- **`mmap`**: scartata; il sistema operativo non conosce le transazioni e non
  controlla l'ordine di scrittura (vedi la wiki).

## Consequences

- Ogni uso di una pagina richiede **pin** prima e **unpin** dopo; le pagine
  pinnate non si evincono.
- LRU aggiorna la recenza a ogni `fetch` (una scrittura per hit) e l'eviction
  cerca il frame meno recente tra quelli con pin count `0`.
- Una vittima **sporca** viene riscritta su disco prima di essere riusata.
- Se tutti i frame sono pinnati e serve una pagina nuova, `fetch_page` solleva
  `BufferPoolFullError`.
- I test usano un `PageManager` reale su `tmp_path`; per verificare hit/miss si
  può avvolgere il page manager in un contatore di chiamate.
