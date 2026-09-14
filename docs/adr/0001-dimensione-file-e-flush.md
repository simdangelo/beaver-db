# 0001 — Dimensione del file e flush nel page manager

- **Status**: accepted
- **Data**: 2026-09-12

## Context

`PageManager.num_pages()` deve sapere quante pagine contiene il file. La
dimensione si può leggere in due modi: dal filesystem, con
`Path.stat().st_size`, oppure dall'handle aperto, spostandosi alla fine con
`seek`/`tell`. Poiché Python **bufferizza** le scritture, le due letture
possono discordare finché non si fa `flush` (il concetto è nella wiki
[`../wiki/buffering-e-flush.md`](../wiki/buffering-e-flush.md)). La scelta non
è neutra: un `num_pages()` "in ritardo" può far riallocare una pagina già
esistente, sovrascrivendo dati.

## Decision

Usiamo l'**opzione A**: `self._path.stat().st_size // PAGE_SIZE`.

Conseguenza operativa esplicita: ogni scrittura di pagina deve fare `flush`
prima che `num_pages()` sia attendibile. In pratica `allocate_page` e
`write_page` chiameranno `self._file.flush()` dopo aver scritto.

## Alternatives considered

- **Opzione B — handle `seek(0, SEEK_END)` + `tell()`**: legge la dimensione
  logica del file object, che include i byte ancora nel buffer del processo
  (e il `seek` fa flush). Non richiede un flush esplicito, ma lega la misura
  allo stato dell'handle e richiede di importare `SEEK_END`.
- **Opzione C — contatore in memoria**: `PageManager` tiene il numero di
  pagine in un campo, inizializzato dal file all'apertura e incrementato in
  `allocate_page`. È ciò che fanno i DBMS veri (spesso lo persistono in un
  header) ed è la soluzione più robusta al buffering, ma introduce stato da
  mantenere coerente.

## Consequences

- Le scritture di pagina **devono** fare `flush`; dimenticarlo reintroduce il
  bug della doppia allocazione.
- La dimensione viene controllata in `__init__` **prima di aprire** il file,
  così un file corrotto viene rifiutato senza lasciare handle aperti. Poiché
  in quel momento non esiste ancora un handle, l'**opzione B è di fatto
  esclusa** per `_file_size()`: non c'è nulla su cui fare `seek`/`tell`. B
  resta documentata solo come alternativa teorica.
- `stat` riflette i byte consegnati al sistema operativo e non richiede
  `fsync`: la durabilità al crash resta una questione separata (modulo WAL).
- Se in futuro vorremo evitare il flush a ogni scrittura, si passerà
  all'opzione C con un nuovo ADR che supera questo (gli ADR sono
  near-immutabili).
