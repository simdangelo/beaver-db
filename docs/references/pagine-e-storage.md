# Pagine, file e storage

> Distillato da: Pavlo, *Database System*, lezioni 03 (Storage 1) e 04
> (Storage 2); Nasser, *Fundamentals of Database Engineering*, lezione 03.
> Verificato il 2026-09-10. Contenuto approssimato per scopo didattico.

## I tre tipi di "pagina"

Il termine "pagina" indica tre cose diverse; non confonderle mai:

1. **Hardware page** (~4KB): il blocco più piccolo su cui l'hardware
   garantisce **scritture atomiche** — o il blocco intero arriva su disco,
   o non arriva niente. È il motivo profondo per cui 4096 byte è una
   dimensione così diffusa.
2. **OS page** (4KB su Linux di default): l'unità con cui il sistema
   operativo gestisce la memoria.
3. **Database page** (da 512B fino a 64KB): l'unità di I/O scelta dal DBMS.
   Questa la scegliamo noi — e per beaver-db è 4096.

Dimensioni di pagina nei sistemi reali (default):

| DBMS | Pagina |
|---|---|
| PostgreSQL | 8KB |
| SQL Server | 8KB |
| MySQL/InnoDB | 16KB |
| DB2 | fino a 64KB |
| SQLite | 4096B di default (le note di Pavlo dicono 512B: citano il minimo storico/configurabile; il default attuale è 4096) |

Trade-off della dimensione (entrambi i corsi): pagina grande = più righe
per I/O ma più spreco quando serve una riga sola e scritture più care;
pagina piccola = meno spreco ma più I/O. "There is no free lunch."

## Indirizzamento e storage manager

- Ogni pagina ha un **page ID** unico (tipicamente intero a 32 o 64 bit).
  La mappatura è la matematica che conosciamo: `offset = page_id × page_size`.
- Lo **storage manager** (o storage engine) è il componente che: gestisce i
  file del database, tiene traccia di quali pagine esistono, quanto spazio
  libero hanno (serve per gli insert), e mantiene la directory che mappa
  page ID → posizione fisica.

## Heap file

Definizione (Pavlo): *una collezione non ordinata di pagine in cui le tuple
stanno in ordine casuale*. Il modello relazionale non richiede ordini.

Operazioni richieste: creare/allocare pagine nuove, leggere una pagina,
scrivere una pagina, cancellare una pagina, iterare.

**Page directory**: la struttura che tiene traccia delle pagine. È
essenzialmente una mappa da page ID a pagine, e può memorizzare per ogni
pagina: numero di slot liberi, spazio libero, stato (in uso, cancellata).
Può stare in un file a sé, nell'header del file del database, o in una
posizione speciale (SQLite la mette nell'header del file). Regola
fondamentale: **qualsiasi aggiornamento della directory va scritto su
disco**, altrimenti non si sa più quali pagine esistono. Allocazione a
blocchi (es. un GB alla volta, directory aggiornata una volta sola) è un
trucco reale dei sistemi.

Nota: le note di Pavlo descrivono **solo** la page directory, non la
variante linked-list che appare nelle slide originali di 15-445. Per
beaver-db: la scelta directory vs linked list va fatta con wiki+ADR nel
modulo heap-file.

## Slotted page (modulo 2)

Layout, dall'alto in basso della pagina:

```
[ header di pagina ]  ← all'inizio
[ slot array       ]  ← cresce dall'inizio verso la fine
[ spazio libero    ]  ← in mezzo
[ dati delle tuple ]  ← cresce dalla fine verso l'inizio
```

La pagina è piena quando slot array e tuple si incontrano.

- Ogni **slot** è un offset a lunghezza fissa che punta all'inizio di una
  tupla (opzionalmente anche la sua dimensione).
- **Delete**: lo slot "punta al nulla" (o viene marcato libero). Nessun'altra
  parte del sistema deve sapere che qualcosa si è spostato: questa
  indirezione è il vantaggio chiave.
- **Compaction**: due scuole valide — lasciare le tuple dove sono (buchi in
  mezzo accettati) o farle scorrere aggiornando i soli offset negli slot.
  Fatto reale: PostgreSQL non compatta sugli insert, SQL Server sì.
- **Header di pagina** (campi comuni): dimensione pagina, checksum, versione
  del database, informazioni di visibilità transazionale, metadati di
  compressione, informazioni di schema, statistiche min/max.
- **Header di tupla**: bitmap dei NULL (il metodo più comune per gestire
  i NULL), informazioni di visibilità transazionale, dimensione.

## Record ID

Composizione tipica: **(file, pagina, slot)**. PostgreSQL lo chiama tuple
ID (6 byte), SQLite 8, SQL Server 8, Oracle 10. Due regole didatticamente
importanti:

- La maggior parte dei database **non memorizza il Record ID nei dati**: è
  sintetizzato dalla struttura (directory → pagina → slot → offset).
- Le applicazioni **non devono fidarsi della stabilità** del Record ID: la
  compaction può spostare le tuple.

## mmap: perché Pavlo dice "mai"

Il corso è categorico (*"Never use mmap for database storage"*): il sistema
operativo non sa nulla di SQL e gestisce le pagine per conto suo. I quattro
problemi critici:

1. **Transazioni**: l'OS può scrivere le pagine dirty in ordine sbagliato →
   corruzione dopo crash (mlock non impedisce la write-out dell'OS).
2. **Stalli**: un major page fault blocca il thread completamente.
3. **Errori**: gli errori hardware arrivano come SIGBUS, non come eccezioni
   gestibili.
4. **Contesa**: le strutture di eviction dell'OS vanno protette con mutex.

Casi reali: LMDB/MonetDB/PoloDB lo usano; MongoDB ha abbandonato mmap
passando a WiredTiger; RocksDB ha rimosso mmap ereditato da LevelDB. Per
beaver-db: il buffer pool lo scriviamo noi (modulo 3); mmap resta al massimo
un esperimento comparativo, mai architettura.

## Write amplification

Portare una pagina in memoria per una tupla significa portare ~20 tuple; se
una cambia, si riscrive la pagina intera. È il costo strutturale
dell'unità-di-I/O = pagina, e il motivo per cui il buffer pool esiste.

## Row store: la scelta confermata

Pavlo 05 dà un nome al nostro modello: **NSM (N-ary Storage Model)**, il row
store, la disposizione giusta per carichi OLTP stile "una entità alla volta".
Conferma che slotted page + heap è la strada coerente. Storage models
alternativi (colonnari, PAX) e compressione sono fuori scope:
vedi `fuori-scope.md`.

## Aggiunte utili da Nasser (lezione 03)

- La pagina è l'**unità atomica di I/O**: il database non legge mai singole
  righe.
- Esempio aritmetico pronto all'uso per esercizi: righe da 2.5KB in pagine
  da 8KB → ~3 righe per pagina; 1001 righe → ~334 pagine.
- PostgreSQL si affida molto alla **cache dell'OS** invece di un buffer pool
  proprietario: il nostro buffer pool didattico è quindi una semplificazione
  legittima di uno spettro reale di scelte.
- Row ID = indirizzo fisico (file, pagina, slot): gli indici secondari
  puntano lì (vedi `indici-btree-e-hash.md`, il "pointer paradox").
