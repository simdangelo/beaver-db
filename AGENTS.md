# AGENTS.md — beaver-db

Questo file è il contratto tra l'autore del progetto e l'agente: dice cosa si
sta costruendo, come si lavora, quali scelte sono fisse e quali confini non si
oltrepassano. Si applica a ogni sessione di lavoro sul progetto.

> **Regola suprema**: se l'utente chiede qualcosa in conflitto con questo
> file, vince l'utente. Questo file è la base del lavoro, non una gabbia.

## 1. Project Overview

**beaver-db** è un DBMS relazionale didattico costruito from scratch in
Python: pagine su disco, buffer pool, B+Tree, un sottoinsieme di SQL e un
execution engine in stile Volcano.

- **Obiettivo**: capire come funziona un DBMS *dall'interno*. L'autore è un
  engineer junior che vuole diventare mid; la metrica di successo è la
  comprensione dei concetti, non il prodotto finito.
- **Livello di ambizione**: progetto di apprendimento. NON è production-ready:
  niente performance, niente concorrenza, niente rete, niente ottimizzazioni.
  Le approssimazioni didattiche sono ammesse e volute quando chiariscono il
  concetto: non si costruisce il miglior database del mondo.
- **Vincoli strutturali**: single-node, single-process, single-threaded;
  libreria embedded con REPL sopra.
- **Chi scrive cosa**: il codice lo scrive l'utente (vedi sotto). L'agente
  scrive wiki e review, e scrive codice solo come sblocco esplicito.
- **Fonti di riferimento**: corso CMU 15-445 di Andy Pavlo (e BusTub),
  *Database Internals* di Alex Petrov, SimpleDB di Edward Sciore. In locale
  sono consultabili anche due corsi salvati come appunti markdown: il corso
  *Database System* di Andy Pavlo e *Fundamentals of Database Engineering* di
  Hussein Nasser, nei path qui sotto. Servono a chiarire dubbi, verificare
  le assunzioni del progetto e suggerire miglioramenti — ma i concetti si
  adottano solo se **proporzionati** a beaver-db: niente integrazioni spinte
  solo perché presenti nei corsi. Se una fonte suggerisce cambiamenti
  importanti a architettura o roadmap, prima se ne discute con l'utente. Il
  distillato verificato di entrambe le fonti sta in `docs/references/`: è il
  primo posto da consultare; le fonti intere servono solo per citazioni o
  approfondimenti.

  ```
  /home/mrbeaver/Documents/simonedangelo-blog/content/Courses & Playlists/Database System (by Andy Pavlo)
  /home/mrbeaver/Documents/simonedangelo-blog/content/Courses & Playlists/Fundamentals of Database Engineering (by Hussein Nasser)
  ```

## 2. Learning Workflow

Il progetto serve a imparare facendo. Ogni modulo segue questo loop, e
l'agente deve rispettarlo:

```
1. WIKI       → l'agente scrive una guida sul CONCETTO (teoria, trade-off, insidie)
2. IMPLEMENTA → l'utente scrive il codice da solo, applicando la wiki
3. REVIEW     → l'agente recensisce il codice e dice cosa sistemare e perché
4. ITERA      → l'utente corregge (1-2 giri)
5. SBLOCCO    → se l'utente è bloccato, l'agente scrive lui il codice
```

Regole non negoziabili:

- **Il codice lo scrive l'utente**, di norma. L'agente scrive la
  documentazione; il codice applicativo lo scrive l'agente solo come passo di
  SBLOCCO esplicito. Lo sblocco è normale, non un fallimento.
- **La wiki viene prima del codice.** Non si implementa un concetto senza che
  la wiki lo abbia insegnato.
- **Ogni scelta architetturale non banale diventa un ADR**, oltre alla wiki
  che insegna il concetto generale.
- La documentazione segue il pacchetto `docs/how-to/`: wiki in `docs/wiki/`,
  storia in `docs/journal/`, decisioni in `docs/adr/`, spec e piani in
  `docs/superpowers/`.

## 3. Learning Roadmap (ordine fisso)

I moduli di apprendimento, in ordine. **L'ordine non si riordina, non si
accorpa e non si salta** senza proporlo esplicitamente all'utente. Le feature
di prodotto (un altro piano, con un'altra angolazione) stanno invece in
`docs/ROADMAP.md`.

1. **page-manager** — file binari a pagine fisse (4096 byte): page ID →
   offset, read/write con `struct`/`bytearray`, dump esadecimale ispezionabile.
2. **slotted-page** — record a lunghezza variabile dentro una pagina: slot
   directory, tombstone per il delete, compaction.
3. **buffer-pool** — cache di pagine in RAM: pin/unpin, dirty flag, flush,
   eviction (partendo da LRU; Clock da valutare in alternativa).
4. **heap-file** — una tabella sopra le pagine: insert, scan sequenziale,
   delete logica, Record ID.
5. **catalog** — metadati degli schema (tabelle, colonne, tipi), persistiti
   con le stesse strutture del DB (dogfooding), non con json "di comodo".
6. **direct-api** — end-to-end senza SQL: create/drop table, insert, scan,
   delete via API Python + REPL minimale. Prima milestone "sembra un database".
7. **sql-parser** — tokenizer scritto a mano + recursive descent parser su un
   sottoinsieme SQL fisso e scritto prima di iniziare; output: AST.
8. **execution-engine** — operatori in stile Volcano/iterator: SeqScan,
   Filter, Project, Insert, Update, Delete.
9. **btree-index** — B+Tree sulle stesse pagine: search/insert/split; delete
   e merge opzionali; IndexScan nell'executor.
10. **hash-index** *(opzionale)* — indice hash persistito sulle stesse
    pagine: extendible hashing, bucket su pagine + directory che raddoppia,
    split e overflow. La controparte del B+Tree per le point query.
11. **wal** *(stretch)* — write-ahead log minimale con redo al riavvio.

**Nota sui moduli finali**: i moduli 10 e 11 sono indipendenti tra loro e
facoltativi — il percorso minimo termina al modulo 9. Arrivati al termine
del modulo 9 si decide *se* farli e *in quale ordine*: l'agente propone,
l'utente decide, e la scelta (con il suo perché) finisce nel journal.

Scelte rimandate al modulo in cui servono (da decidere con wiki+ADR, non
assunte in anticipo):

- Politica di eviction definitiva (LRU vs Clock) → modulo buffer-pool.
- Organizzazione interna del heap file (page directory vs linked list) →
  modulo heap-file.
- Set di tipi supportati e formato binario delle tuple → moduli
  slotted-page e catalog.
- Grammatica SQL esatta (operatori ammessi nel WHERE, AND/OR) → modulo
  sql-parser: la grammatica va scritta per iscritto prima di implementarla.
- B+Tree con o senza delete/merge dei nodi → modulo btree-index.
- Se fare l'indice hash e con quale schema (extendible vs linear hashing) →
  si decide al termine del modulo btree-index.

## 4. Fixed Technology Choices

Scelte tecniche non negoziabili a metà progetto, con i comandi esatti:

```bash
# Correct
uv sync                        # setup ambiente e dipendenze
uv run pytest                  # tutti i test
uv run pytest tests/storage    # test di un solo modulo
uv run ruff check .            # lint
uv run ruff check --fix .      # auto-fix dei problemi di lint
uv run ruff format .           # format
uv run basedpyright            # type check
uv add --dev <pacchetto>       # aggiungere una dipendenza di sviluppo
uv run python -m beaver_db     # la REPL (quando esisterà)

# Never
pip install ...                # mai pip diretto: si passa sempre da uv
python script.py               # mai python nudo: sempre uv run
mypy, pyright                  # il type checker del progetto è basedpyright
```

- **Python 3.14** (`requires-python = ">=3.14"`).
- **Il core del DBMS usa solo la stdlib**: `struct`, `bytearray`, `mmap`,
  file I/O. Nessuna dipendenza di runtime.
- **Dipendenze dev ammesse**: `pytest`, `hypothesis`, `ruff`, `basedpyright`.
  Altre si
  aggiungono solo con l'accordo dell'utente.
- **Mai librerie che nascondono la persistenza**: niente `pickle`, niente
  `sqlite3`, niente ORM, niente pandas. I byte su disco si scrivono a mano.

## 5. Architecture

I layer, dall'alto in basso. **Le dipendenze vanno solo verso il basso**:
un layer parla solo con il layer immediatamente sottostante, mai con quelli
più in fondo, mai con quelli sopra.

```
REPL / API Python            interfaccia
        ↓
Parser SQL → AST             (dal modulo 7)
        ↓
Execution engine (Volcano)   operatori iterator che si compongono
        ↓
Access methods               heap file, B+Tree
        ↓
Buffer pool                  cache di pagine, eviction, flush
        ↓
Page manager                 pagine fisse → disco
```

Regole che non si rompono:

- L'unica unità di I/O verso il disco è la **pagina** (4096 byte fissi).
- Il formato su disco è sempre **byte espliciti**: campi impacchettati con
  `struct`, offset calcolati a mano. Mai serializzare oggetti Python.
- **Sopra il page manager, l'unico componente che tocca il disco è il buffer
  pool**: tutto il resto chiede pagine a lui. Il page manager non fa eccezione
  a questa regola, perché *è* il livello del disco.
- Gli access method (slotted page, heap file) lavorano su pagine **in memoria**
  (una `bytearray` da `PAGE_SIZE`) e non fanno I/O: ricevono una pagina, la
  modificano in posto e la restituiscono. La persistenza è di un altro livello.
- Gli operatori dell'executor seguono il **modello Volcano**: ogni operatore
  espone un iteratore (`__iter__`/`__next__` in Python) e tira le tuple da
  quello del figlio.
- Il formato dei file su disco non ha migrazioni: cambiare il formato di una
  pagina invalida i file esistenti, e in sviluppo si ricreano (rimuovendo i
  file di dati, che non contengono nulla di prezioso).

## 6. Project Structure

```
beaver-db/
├── README.md              # vetrina GitHub (in inglese)
├── AGENTS.md              # questo file
├── pyproject.toml         # dipendenze e configurazione (uv, ruff, pytest)
├── src/beaver_db/         # il DBMS, layout src
│   ├── storage/           # page manager, slotted page
│   ├── buffer/            # buffer pool manager
│   ├── access/            # heap file, btree, hash (se il modulo 10 verrà fatto)
│   ├── catalog/           # metadati degli schema
│   ├── executor/          # operatori Volcano
│   ├── parser/            # tokenizer, parser, AST
│   └── repl.py            # la REPL
├── tests/                 # speculare a src/beaver_db/
└── docs/
    ├── ROADMAP.md         # piano delle feature di prodotto
    ├── wiki/              # concetti del progetto (i moduli del roadmap)
    ├── knowledge/         # conoscenza generale (Python, testing), non specifica del progetto
    ├── journal/           # storia del progetto, modulo per modulo
    ├── adr/               # decisioni architetturali
    ├── references/        # distillato delle fonti (corsi), per consultazione rapida
    ├── superpowers/       # specs e plans (artefatti di lavoro)
    └── how-to/            # le regole per scrivere i documenti
```

La struttura interna di `src/beaver_db/` cresce con i moduli del learning
roadmap; i layer qui sopra sono la forma da rispettare quando si tocca il
codice.

## 7. Code Conventions

- Identificatori nel codice in **inglese**; i **commenti** possono essere in
  italiano o in inglese, scegliendo la lingua che rende più chiaro il *perché*;
  la documentazione di progetto (wiki, journal, ADR, ROADMAP) in **italiano**.
- Type hints ovunque, verificati con `basedpyright`; niente `Any` senza motivazione.
- `snake_case` per moduli, funzioni e variabili; `PascalCase` per le classi;
  MAIUSCOLO per le costanti.
- I numeri magici (offset, dimensioni, marker sui dischi) sono costanti
  nominate a livello di modulo, mai letterali sparsi nel codice.
- Docstring brevi dove una scelta non è ovvia (dicono il *perché*, non il
  *cosa*); niente commenti che riscrivono il codice.
- Import assoluti; niente star import.
- Ogni funzione pubblica ha un test; gli invarianti hanno test property-based
  (vedi Testing).

## 8. Testing

- Framework: **pytest**, property-based con **hypothesis** per gli invarianti.
- I test stanno in `tests/` e rispecchiano la struttura di `src/beaver_db/`.
- Ogni modulo del learning roadmap porta i suoi test, e gli invarianti da
  coprire sono parte della wiki del modulo. Minimi per struttura:
  - **slotted-page**: roundtrip serialize/deserialize bit per bit; slot
    directory consistente dopo N operazioni insert/delete/update generate.
  - **buffer-pool**: mai più pagine in memoria della capacity; dopo il flush
    i byte su disco sono identici ai byte in memoria.
  - **heap-file**: una scan restituisce esattamente le tuple inserite meno
    quelle cancellate, con i loro Record ID.
  - **btree**: ogni chiave inserita viene trovata; lo scan è ordinato;
    dopo N insert l'albero resta bilanciato.
- Un lavoro è finito solo quando passa tutta la verifica:

```bash
uv run pytest && uv run ruff check . && uv run basedpyright
```

## 9. Boundaries

Regole assolute, valide in ogni sessione:

- **MAI** scrivere codice applicativo al posto dell'utente, tranne come passo
  di SBLOCCO esplicito (l'utente lo chiede, o è chiaramente bloccato dopo
  iterazioni senza progresso).
- **MAI** implementare un modulo senza la sua wiki, né una scelta non banale
  senza il suo ADR.
- **MAI** riordinare, accorpare o saltare i moduli del learning roadmap
  senza proporlo esplicitamente all'utente.
- **MAI** eseguire comandi git (commit, push, branch, ecc.) senza permesso
  esplicito nella sessione.
- **MAI** cancellare file o cartelle con `rm` o equivalenti.
- **MAI** introdurre dipendenze di runtime o librerie che nascondono la
  persistenza (`pickle`, `sqlite3`, ORM).
- **MAI** committare segreti o credenziali.
- **MAI** modificare i file in `docs/how-to/`: sono le regole del metodo, non
  documenti del progetto.
