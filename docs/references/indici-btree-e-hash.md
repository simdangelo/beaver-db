# Indici: B+Tree e hash

> Distillato da: Pavlo, *Database System*, lezioni 07 (Hash Tables) e 08
> (B+Tree); Nasser, *Fundamentals of Database Engineering*, lezione 04.
> Verificato il 2026-09-10. Contenuto approssimato per scopo didattico.

## B+Tree: struttura

- **Un nodo = una pagina** del database (e quindi del buffer pool). Per
  beaver-db: un nodo = 4096 byte.
- Un nodo è un **array di coppie chiave/valore**. Il layout più comune è
  *separated storage*: array delle chiavi + array dei valori, con lo stesso
  offset che corrisponde nei due array. Si sposa bene con il nostro stile
  byte-esplicito (`struct` + offset calcolati).
- **Nodi interni**: solo chiavi-guida (*guideposts*) e puntatori ai figli.
  K chiavi → K+1 figli. I record ID vivono SOLO nelle foglie: in un nodo
  interno un record potrebbe non esistere più, e la chiave resta lì solo
  come semaforo direzionale.
- **Foglie**: chiavi + record ID (o i dati della tupla) + **sibling
  pointers** (page ID del precedente e del successivo allo stesso livello).
  Le foglie formano una lista doppiamente linkata: è ciò che rende i range
  scan possibili senza risalire l'albero.
- I puntatori vanno **solo in giù e di lato, mai in su**.
- **Invariante half-full**: ogni nodo tranne la radice deve essere almeno
  mezzo pieno. La soglia è "tweakable" — vedi la delete pigra sotto.
- **Ricerca dentro il nodo**: binary search sugli array ordinati (lo
  standard). Per noi, anche la scansione lineare va benissimo.

## Insert e split

Si trova la foglia giusta; se c'è spazio, insert ordinato e basta. Se è
piena: **split a metà** e la chiave di mezzo **sale (copy-up)** al parent
come nuova guida, con il nuovo puntatore alla foglia nata dallo split. La
cascata è ricorsiva: se il parent trabocca, si splitta anche lui, fino alla
radice eventualmente.

## Delete: versione completa e versione pigra

Versione completa (se mai la implementeremo): se la foglia resta almeno
mezza piena, basta; altrimenti prima **redistribution** (rubare una chiave
al sibling via sibling pointers, aggiustando la guida nel parent), poi
**merge** (fondersi col sibling, togliere la guida dal parent; ricorsivo
verso l'alto).

Versione pigra, **supportata dalle stesse note**: alcuni sistemi violano
volontariamente l'invariante half-full per evitare merge prematuri —
il corso lo attribuisce a PostgreSQL, che chiamerebbe il suo B+Tree
"non-balanced" (NB-tree). Una chiave cancellata può anche restare nei nodi
interni come semplice semaforo. Conseguenza per beaver-db: la decisione
"search/insert/split obbligatori, delete/merge opzionali" è pienamente
coerente coi corsi. Le foglie possono andare sparse.

## Perché B+Tree è il default e hash no

Le tabelle hash supportano **solo uguaglianza** e servono la chiave intera.
Il B+Tree, con le foglie ordinate e linkate, supporta: match esatto,
ricerca per prefisso, per suffisso e range scan. Per le point query pure
l'hash vince (O(1) vs O(log n)) — è esattamente la divisione di ruolo
tra feature 7 e 8 della roadmap.

## Tabelle hash su disco

Panoramica degli schemi (dal più semplice al più strutturato):

- **Linear probing**: un grande array di slot, collisione → slot successivo
  (con wrap-around). Il più semplice e veloce; la delete rompe le catene, e
  la soluzione corretta sono i **tombstone** (riutilizzabili per nuove
  chiavi).
- **Cuckoo**: più funzioni hash, lookup e delete O(1) garantiti, insert
  costose (catene di evizione, resize con raddoppio e rehash totale).
- **Chained hashing**: bucket + **overflow pages** (tabella hash a due
  livelli). Il bucket è grande quanto una pagina (PostgreSQL 8KB, MySQL
  16KB) — supporto diretto al nostro "bucket = pagina".
- **Extendible hashing** (la scelta di beaver-db): una **directory** con
  **global depth** (quanti bit dell'hash guardare) e ogni bucket con la sua
  **local depth**. Su overflow: global depth +1 → la directory **raddoppia**;
  il bucket pieno **si splitta** e la sua local depth +1. Si ristruttura
  solo il bucket interessato, **senza rehash completo**. Usato da GDBM e
  AsterixDB.
- **Linear hashing**: split incrementale guidato da un **puntatore** al
  prossimo bucket da splittare — si splitta il bucket *puntato*, non quello
  che ha traboccato (il punto controintuitivo). Usato da PostgreSQL; non
  supporta lo shrinking.

Per il modulo 10 la meccanica necessaria è tutta qui: directory + global/
local depth + raddoppio + split del solo bucket pieno.

## Il "pointer paradox" (Nasser)

Gli indici secondari su un sistema heap (PostgreSQL) memorizzano il **RID
fisico**: lookup veloce ma invalidato se la riga si sposta. Su un sistema
clustered (InnoDB) memorizzano la **primary key**: sopravvive agli split ma
richiede una seconda traversata. beaver-db è un heap system → le foglie dei
suoi indici secondari conterranno **Record ID**. Ottimo materiale per
un ADR al modulo 9.

## Dettagli proporzionati (Nasser)

- **Fan-out**: con fan-out 100, tre livelli coprono ~100³ = un milione di
  pagine → albero basso, 3–4 letture per trovare qualunque record.
- **Fill factor**: lasciare spazio vuoto nelle pagine riduce gli split
  prematuri; gli insert in ordine sparso di chiavi (UUID) generano split
  "nasty" (dannosi) e frammentazione, le chiavi sequenziali no.
- Le foglie sono **doppiamente** linkate (scansione in entrambe le direzioni).

## Ottimizzazioni che IGNORIAMO di proposito

SIMD e interpolation search nella ricerca in-nodo; pointer swizzling;
Bε-tree e mod log; prefix compression/dedup/suffix truncation nei nodi;
Bloom filter davanti alle catene di bucket; shrinking in linear hashing;
cuckoo, Robin Hood, Hopscotch, Swiss tables; gestione di chiavi duplicate
via overflow leaves (le note dicono: approccio inferiore e raro). Il bulk
loading (presort + costruzione bottom-up) è un eventuale bonus futuro, non
un prerequisito.
