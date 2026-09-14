# Product Roadmap — beaver-db

Questo documento è il piano delle **feature di prodotto**: cosa beaver-db
deve saper fare, ordinato per dipendenze. È distinto dal **roadmap di
apprendimento** — i moduli didattici con il loro ordine fisso — che sta in
[`../AGENTS.md`](../AGENTS.md) e non è questo documento: qui si parla di
capacità del prodotto, lì di percorso di apprendimento. I due piani coprono
lo stesso territorio da due angolazioni diverse; quando una feature viene
costruita, si aggiorna lo stato qui e il journal racconta come.

**Stati**: `planned` → `in progress` → `done`

---

## 1. Persistenza delle tuple via API Python — `planned`

**Goal**: inserire, leggere e cancellare tuple da codice Python, con i dati
che sopravvivono al riavvio del processo: da qui in poi "il database" è un
file, non la memoria.

**Dependencies**: moduli di apprendimento page-manager, slotted-page,
buffer-pool, heap-file (ordine in [`../AGENTS.md`](../AGENTS.md)).

**Design decisions (made)**:

- Pagine a dimensione fissa di 4096 byte; la pagina è l'unica unità di I/O.
- Serializzazione a byte espliciti con `struct`; niente pickle/sqlite3/ORM.
- Delete logico tramite tombstone nella slotted page.

**Design questions open**: formato esatto dell'header di pagina e della slot
directory (wiki+ADR nel modulo slotted-page); quando fare compaction.

## 2. Tabelle con schema e catalog persistente — `planned`

**Goal**: creare ed eliminare tabelle con colonne tipate (`CREATE TABLE` /
`DROP TABLE` prima via API, poi via SQL); gli schemi sono persistenti e
l'insert li rispetta.

**Dependencies**: feature 1.

**Design decisions (made)**:

- Il catalog è un metadato persistito con le stesse strutture del DB
  (dogfooding), non un file json separato.

**Design questions open**: set esatto di tipi primitivi (almeno interi e
stringhe); dove vive fisicamente il catalogo (tabella di sistema vs file
dedicato) — wiki+ADR nel modulo catalog.

## 3. SQL minimo: INSERT e SELECT full scan — `planned`

**Goal**: primo SQL end-to-end: `INSERT INTO` e `SELECT` (con proiezione di
colonne, senza predicati) eseguiti da parser → AST → execution engine.

**Dependencies**: feature 2; moduli sql-parser ed execution-engine.

**Design decisions (made)**:

- Parser scritto a mano (tokenizer + recursive descent), niente generatori
  di parser: la grammatica è piccola e va scritta per iscritto prima di
  iniziare.
- Executor in stile Volcano: operatori iterator componibili.

**Design questions open**: forma esatta dell'AST; gestione degli errori di
parsing (eccezioni tipizzate vs codici).

## 4. SELECT con WHERE — `planned`

**Goal**: filtrare le righe con predicati semplici su una colonna
(`=`, `!=`, `<`, `<=`, `>`, `>=`), valutati con full scan.

**Dependencies**: feature 3.

**Design decisions (made)**:

- Niente cost-based optimizer: il piano è sempre seq scan in questa fase;
  la scelta indice-vs-scan arriverà con la feature 7 come regola statica.

**Design questions open**: composizione di predicati con `AND`/`OR` (sì/no,
e con quale precedenza); quali tipi sono confrontabili tra loro.

## 5. UPDATE e DELETE con WHERE — `planned`

**Goal**: completare il ciclo CRUD in SQL: modificare e cancellare le righe
che soddisfano un predicato.

**Dependencies**: feature 4.

**Design decisions (made)**:

- La delete resta logica (tombstone), coerente con la feature 1.

**Design questions open**: update che cambia la dimensione del record
(in-place se ci sta, altrimenti delete+insert); cosa succede ai Record ID
dopo una delete.

## 6. REPL interattiva — `planned`

**Goal**: usare beaver-db da terminale: si scrive SQL, si vedono le righe.
È la milestone "sembra un database" per le demo.

**Dependencies**: feature 3 (in linea di principio anche 4 e 5, ma una REPL
utile esiste già con INSERT/SELECT).

**Design decisions (made)**:

- La REPL è un guscio sottile sopra l'API: nessun protocollo di rete, nessun
  processo separato.

**Design questions open**: comandi meta (`.tables`, `.schema`) e formatting
delle righe.

## 7. Indici secondari B+Tree — `planned`

**Goal**: `CREATE INDEX` / `DROP INDEX` e point/range lookup via B+Tree;
l'executor sceglie index scan vs seq scan con una regola statica.

**Dependencies**: feature 5 (le scritture devono mantenere l'indice); modulo
btree-index.

**Design decisions (made)**:

- Il B+Tree vive sulle stesse pagine del buffer pool, non è una struttura
  in memoria separata.
- Search/insert/split obbligatori; delete e merge dei nodi opzionali (si
  decide con wiki+ADR nel modulo btree-index).

**Design questions open**: come gestire la delete di una chiave indicizzata
quando il tree non supporta delete; indice su più colonne (quasi certamente
no, v1 monocolonna).

## 8. Indici hash — `planned` *(opzionale)*

**Goal**: un secondo tipo di indice, veloce sulle point query
(`WHERE id = 5`), alternativo al B+Tree; l'executor lo preferisce per le
ugaglianze.

**Dependencies**: feature 7 (stessa meccanica di `CREATE INDEX` e della
scelta del piano); modulo di apprendimento hash-index.

**Design decisions (made)**:

- Schema disk-oriented: extendible hashing — bucket su pagine + directory
  che raddoppia — non open addressing da RAM adattato al disco.

**Design questions open**: extendible vs linear hashing; *se* implementarlo
si decide al termine del modulo btree-index, in base a tempo e interesse.

## 9. Durabilità al crash: WAL — `planned` *(stretch)*

**Goal**: un write-ahead log minimale con redo al riavvio: dopo un crash,
le transazioni confermate sopravvivono.

**Dependencies**: feature 7 (e 8, se implementata); tocco finale a sistema
completo.

**Design decisions (made)**:

- Nessuna concorrenza: il WAL è pensato per transazioni una alla volta
  (single-writer), redo semplice senza undo.

**Design questions open**: granularità del log (pagina intera vs record);
politica di checkpoint; se il journaling arriva anche alle operazioni del
catalogo.

---

## Deferred (fuori scope, con il perché)

| Feature | Perché rimandata | Quando potrebbe tornare |
|---|---|---|
| Join (anche solo nested loop) | Zero valore per storage/buffer/indice: è tutto sull'executor | Dopo la feature 3, come estensione dell'executor |
| Aggregazioni (COUNT, GROUP BY) | Stesso motivo del join | Estensione naturale dell'executor |
| Subquery | Complica parser ed executor insieme | Dopo il WHERE semplice, se serve |
| Transazioni ACID (lock manager, 2PL, MVCC) | Sistema single-threaded per scelta; è un sottosistema a sé stante | Eventuale v2; nel frattempo si studia su Petrov |
| Query optimizer cost-based | Non didattico a questo livello; la regola statica della feature 7 basta | Mai in questo progetto |
| Rete / protocollo client-server | Il target è libreria embedded + REPL | Se un giorno si vuole un "vero" server |
| Concurrent multi-client | Segue dalla single-threadedness | Mai in v1 |

## Ordering rationale

La persistenza (1) è la fondazione: senza byte su disco non c'è database.
Lo schema (2) rende le tuple significative e dà al catalog il ruolo che ha in
un DBMS vero. L'SQL (3–4) chiude il giro parser→executor e rende il sistema
riconoscibile come database; UPDATE/DELETE (5) completa il CRUD prima che
arrivino le complessità degli indici. La REPL (6) è sottile e non blocca
niente: sta dopo l'SQL minimo perché ha senso fare demo di SQL, non di
comandi diretti.
Gli indici (7) arrivano quando c'è qualcosa da accelerare — insert e query
già funzionanti — e sono il cuore didattico della seconda metà. L'indice
hash (8) è opzionale: è la controparte del B+Tree per le point query e
insegna l'hashing disk-oriented; se farlo si decide al termine del modulo
btree-index. Il WAL (9) è stretch perché tocca tutti i layer e si affronta
solo a sistema completo. Le due code (8 e 9) sono indipendenti tra loro: si
può anche fermarsi al B+Tree.
Le feature rimandate sono in tabella Deferred: il "perché no" è scritto, così
la domanda non torna ciclicamente.
