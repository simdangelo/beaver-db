# 0002 — Formato della slotted page

- **Status**: accepted
- **Data**: 2026-09-12

## Context

Il modulo 2 deve ospitare record a **lunghezza variabile** nelle pagine fisse
da 4096 byte del page manager. Le fonti (Pavlo, lezioni 03 e 04) danno il
layout e le opzioni, ma lasciano **esplicitamente** il formato binario
concreto all'implementazione (*"What's described here isn't exactly how every
system implements it"*):

- layout: header in testa, slot array che cresce **dall'inizio verso la
  fine**, dati che crescono **dalla fine verso l'inizio**; la pagina è piena
  quando i due fronti si incontrano;
- slot: offset a lunghezza fissa (*"you might also store tuple size in the
  slot entry if desired"*), altrimenti la lunghezza sta nell'header di tupla;
- cancellazione: lo slot *"points to nothing (or marks the space as free)"*;
- compaction: due opzioni entrambe valide (lasciare le tuple, o farle scorrere
  aggiornando gli slot); PostgreSQL non compatta all'insert, SQL Server sì.

Il formato va fissato **ora** perché cambiarlo invalida i file esistenti.

## Decision

Tutto **little-endian**, campi impacchettati con `struct` (coerente con l'ADR
0001).

**Header di pagina — 4 byte in testa alla pagina:**

| Campo | Tipo | Significato |
|---|---|---|
| `num_slots` | uint16 | numero di slot allocati, **tombstone inclusi** |
| `data_start` | uint16 | offset del primo byte dei dati; lo spazio libero sta fra la fine dello slot array e `data_start` |

`data_start == 0` indica una pagina **non formattata**: una pagina appena
allocata è tutta zeri e va inizializzata a `num_slots=0`, `data_start=PAGE_SIZE`.

**Slot — 4 byte ciascuno, subito dopo l'header:**

| Campo | Tipo | Significato |
|---|---|---|
| `offset` | uint16 | dove inizia il record nella pagina; **`0` = slot libero** (tombstone) |
| `length` | uint16 | lunghezza del record in byte |

Lo slot numero `k` comincia a `HEADER_SIZE + k * SLOT_SIZE`.

**Record**: per ora un **blob di byte grezzo**, senza header di tupla. La
lunghezza sta nello slot; bitmap dei NULL e tipi di colonna arriveranno col
modulo catalog (AGENTS.md rimanda lì il formato delle tuple).

**Operazioni:**

- `insert(record)`: se esiste uno slot libero lo riusa, altrimenti ne aggiunge
  uno. Serve spazio per `len(record)` più `SLOT_SIZE` se lo slot è nuovo. Se
  lo spazio contiguo non basta, la pagina è piena → errore (deciderà il futuro
  heap file).
- `read(slot)`: solleva se lo slot è libero; altrimenti legge `length` byte.
- `delete(slot)`: tombstone (`offset=0`, `length=0`); lo spazio è recuperabile
  solo con la compaction.
- `compact()`: **esplicita e pigra** (stile PostgreSQL). Ripacca i record vivi
  verso la fine aggiornando gli offset; i numeri di slot non cambiano.
- `free_space()`: `data_start - (HEADER_SIZE + num_slots * SLOT_SIZE)`, cioè
  lo spazio **contiguo** disponibile.

## Alternatives considered

- **Lunghezza solo nell'header di tupla** (stile Pavlo 04): standard, ma
  obbliga a leggere l'header di ogni tupla per la contabilità di spazio e per
  la compaction. Rimandata al modulo catalog, quando ci sarà un vero header di
  tupla.
- **Tombstone con flag dedicato** invece di `offset=0`: più esplicito, ma un
  byte in più per slot; `offset=0` è già impossibile per un record valido,
  perché l'header occupa l'inizio della pagina.
- **Compaction automatica all'insert** (stile SQL Server): meno frammentazione,
  ma insert più costoso e meno prevedibile; preferiamo tenerla esplicita e
  pigra.
- **Header più ricco** (checksum, versione, LSN): rimandato; prenderemo solo i
  campi che useremo davvero, nei moduli buffer-pool e WAL.

## Consequences

- Una pagina appena allocata va **formattata** prima dell'uso; `data_start=0`
  segnala lo stato "da formattare".
- `free_space()` misura solo lo spazio contiguo: un insert può fallire pur
  essendoci buchi, finché non si chiama `compact()`.
- I **numeri di slot restano stabili**: il Record ID `(page_id, slot)`
  sopravvive a delete, riuso dello slot e compaction.
- Cambiare questo formato invalida i file esistenti (in sviluppo si ricreano).
