# Durabilità e WAL

> Distillato da: Nasser, *Fundamentals of Database Engineering*, lezione 02
> (ACID), sezione Durability. Verificato il 2026-09-10. Contenuto
> approssimato per scopo didattico.

## Il problema della durabilità

La RAM è volatile; l'I/O su disco è lento ("millisecondi sono un'eternità").
E la trappola principale: il sistema operativo **cacha le scritture** — un
`write` che ritorna non significa che i dati siano fisicamente su disco.
Se il database dichiara una transazione commessa e poi il processo muore,
**il database ha mentito** al client.

`fsync` forza l'OS a scrivere fisicamente e ritorna solo quando i dati sono
davvero su disco: è il gesto che dà vera durabilità, ed è costoso (per
questo i sistemi reali lo aggirano con group commit, background writer,
compressione del log — tutte cose fuori scope per noi).

## Write-Ahead Log (WAL)

Il meccanismo di durabilità più comune. Le pagine di tabelle e indici sono
enormi da modificare direttamente per ogni transazione; invece:

- Il DBMS mantiene un **file di log separato e append-only** che registra
  **solo le modifiche** (pochi byte per transazione).
- **Ordine delle operazioni**: al commit si scrive l'entry di log e la si
  flussa **subito**; le pagine dati vere vengono aggiornate **dopo**,
  in modo asincrono o durante un checkpoint.
- Se il crash arriva prima che le pagine siano scritte: al riavvio si
  **ripete (redo) il WAL** e lo stato torna consistente. Il log contiene
  la storia completa delle modifiche commesse.
- L'append-only rende le scritture **sequenziali**, molto più veloci delle
  random (su HDD evita il seek; anche sulle SSD i pattern sequenziali
  restano più efficienti).

## Recovery è responsabilità del database

Al riavvio il DBMS rileva le transazioni incompiute (iniziate ma non
commesse) e le ripara. Nessuno lo fa per lui: il crash non negozia con
nessuno.

## Il trade-off di design che documenta il corso

- Scrivere le modifiche **incrementalmente** durante la transazione →
  commit veloce, rollback complicato.
- Scrivere tutto **alla commit** → commit lento, rollback banale (basta
  buttare lo stato in memoria).

Per beaver-db (modulo WAL, stretch): WAL minimale = **log-first + redo al
riavvio**; niente undo, niente checkpoint sofisticati, single-writer.

## Perché non serve concorrenza per il WAL

Un engine single-threaded esegue le transazioni **una alla volta**, quindi
è serializzabile per costruzione ("come se girassero in sequenza"). È la
frase riassuntiva utile quando qualcuno chiede "dove sono i lock?".

## Mitigazioni reali (contestualizzazione)

Redis AOF (log append-only con compaction), `innodb_flush_log_at_trx_commit`,
`synchronous_commit=off`: menu di durabilità-vs-prestazioni dei sistemi
reali. Utili come confronto in wiki/ADR, non da implementare.
