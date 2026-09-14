# Cosa i corsi contengono e NOI ignoriamo

Regola del progetto: i corsi sono più grandi di beaver-db. Questo file
registra cosa esiste nelle fonti e perché non lo adottiamo, così la domanda
non torna ciclicamente a ogni modulo. La metrica del progetto è la
**comprensione dei concetti**, non le performance (AGENTS.md): tutto ciò
che segue serve a rendere un DBMS più veloce o più grande, non a spiegare
un concetto in più.

## Storage models e compressione (Pavlo, lezione 05)

Colonnare/DSM, PAX, layout Parquet, compressione (RLE, bit-packing,
delta, dictionary, bitmap): tutto guidato da riduzione di I/O, cache
locality e rapporti di compressione per carichi OLAP — mentre il nostro
target è didattico e single-user.

**Verdetto**: da non adottare. Unico takeaway, già assimilato: il corso
specifica che il **row store (NSM)** è la disposizione giusta per
accessi stile OLTP "una entità alla volta" — che è esattamente il profilo
di beaver-db, e conferma la strada slotted page + heap. La menzione in
una wiki futura ("perché siamo un row store") è il massimo dell'uso che
se ne fa.

## Partitioning (Nasser, lezione 06)

Range/list/hash partitioning, pruning, sharding multi-server, archiviazione
a livelli: presuppone un query optimizer capace di scegliere le partizioni
e dataset da milioni di righe. **Skip totale.**

Attenzione alla disambiguazione: **"hash partitioning" = distribuire i dati
di una tabella su più tabelle fisiche**; non c'entra nulla con l'**indice
hash** (access method della feature 8). Semplice omonimia.

## Concurrency control (Nasser, lezione 08)

Lock condivisi/esclusivi, deadlock, 2PL, MVCC, `SELECT FOR UPDATE`:
tutto presuppone connessioni concorrenti che beaver-db non ha
(single-node, single-process, single-threaded). **Skip totale.**

Unico nugget: un engine single-threaded esegue le transazioni sequenzialmente
e quindi è serializzabile per costruzione — una frase, zero lavoro.

## Ottimizzazioni degli indici (Pavlo 07/08, Nasser 04)

Elenco completo in `indici-btree-e-hash.md`: SIMD, pointer swizzling,
Bε-tree, prefix compression, Bloom filters, cuckoo/Robin Hood, bulk loading.
Queste sono "il secondo step" di sistemi reali; per noi rumore e complessità
implementativa a costo zero didattico.

## Perché questo non è "tagliare troppo"

Le scelte dentro `pagine-e-storage.md` e `indici-btree-e-hash.md` coprono
tutto ciò che serve alle feature di prodotto della roadmap. Questo file
documenta solo ciò che resterebbe a bordo inutilizzato; se un giorno una
feature la riattiva (es. join → executor, vedi Deferred in ROADMAP.md),
la si riprende da qui e si discute, non la si importa a sorpresa.
