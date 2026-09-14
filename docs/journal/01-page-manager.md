# 01 — Page manager: il database impara a leggere il disco

## Che modulo è e dove si colloca

Il **page manager** è il primo modulo del learning roadmap, il più basso di
tutti: sotto non c'è nulla. Il suo obiettivo è dare al database un modo di
parlare col disco in unità fisse — **pagine da 4096 byte** — con una mappa
`page_id → offset` e operazioni di lettura, scrittura e allocazione. Tutto
ciò che verrà dopo (slotted page, buffer pool, heap file, indici) poggerà su
questo strato. Il concetto generale è nella wiki
[`../wiki/page-manager.md`](../wiki/page-manager.md); qui raccontiamo cosa
abbiamo costruito e cosa è andato storto lungo la strada.

## Le decisioni prese

**Come leggere la dimensione del file.** `num_pages()` deve sapere quante
pagine contiene il file. La dimensione si può leggere dal filesystem
(`Path.stat().st_size`, "opzione A") o dalla posizione dell'handle aperto
(`seek`/`tell`, "opzione B"). Abbiamo scelto la A, con l'obbligo di fare
`flush` dopo ogni scrittura, altrimenti la dimensione vista dal filesystem
resta indietro. La decisione, con le alternative, è nell'ADR
[`../adr/0001-dimensione-file-e-flush.md`](../adr/0001-dimensione-file-e-flush.md).
Scoperta collaterale: la validazione della dimensione avviene in `__init__`
**prima** di aprire il file, quindi l'opzione B è di fatto esclusa — in quel
momento l'handle non esiste.

**Validare il file all'apertura.** Se la dimensione non è un multiplo di
`PAGE_SIZE`, il file è corrotto e `__init__` solleva `CorruptFileError`
*prima* di aprire l'handle, così non resta nessun file aperto a metà.

**Una tassonomia di errori.** Abbiamo creato `src/beaver_db/exceptions.py`
con tre eccezioni nominate, distinte per causa: `CorruptFileError` (il dato
su disco è incoerente), `PageNotAllocatedError` (chi chiama ha chiesto una
pagina che non esiste), `InvalidPageSizeError` (chi chiama ha passato dati
di lunghezza sbagliata). Il criterio è nel
[`../knowledge/file-binari-in-python.md`](../knowledge/file-binari-in-python.md).

**La lingua dei commenti.** Durante il modulo l'autore ha preferito scrivere
commenti in italiano; AGENTS.md §7 è stato aggiornato per ammettere sia
italiano sia inglese nel codice (la documentazione resta in italiano).

## Le modifiche al codice

`src/beaver_db/storage/page_manager.py` — il cuore del modulo:

- `PAGE_SIZE` e la funzione pura `page_offset(page_id)`, la moltiplicazione
  che è tutto l'indirizzamento del database.
- `hex_dump(data)`: rende i byte leggibili a gruppi di 16, con offset e
  colonna ASCII (`.` per i non stampabili).
- `PageManager.__init__`: sceglie la modalità (`"r+b"` se il file esiste,
  `"w+b"` se va creato) e valida la dimensione.
- `_file_size()`: legge la dimensione dal filesystem (opzione A). L'helper è
  condiviso tra la validazione in `__init__` e `num_pages()`.
- `num_pages()`: `_file_size() // PAGE_SIZE`.
- `allocate_page()`: calcola il prossimo id, scrive una pagina di zeri in
  coda, controlla i byte scritti, fa `flush`, restituisce l'id.
- `read_page(page_id)`: valida il range, si posiziona, legge `PAGE_SIZE`
  byte, restituisce un `bytearray`.
- `write_page(page_id, data)`: valida range e lunghezza, si posiziona,
  scrive, controlla i byte scritti, fa `flush`.
- `close()`.

`src/beaver_db/exceptions.py` — le tre eccezioni nominate.

`tests/storage/test_page_manager.py` — 38 test: `page_offset` (4),
`num_pages` (4), `allocate_page` (6), `read_page` (8), `write_page` (9),
`hex_dump` (7), inclusi cinque test property-based con Hypothesis. Le
convenzioni e le trappole di testing sono in
[`../knowledge/testing-con-pytest-e-hypothesis.md`](../knowledge/testing-con-pytest-e-hypothesis.md).

`docs/wiki/page-manager.md` e `docs/wiki/buffering-e-flush.md` — i concetti
del progetto; `docs/knowledge/file-binari-in-python.md` e
`docs/knowledge/testing-con-pytest-e-hypothesis.md` — la conoscenza generale
riutilizzabile.

`docs/adr/0001-dimensione-file-e-flush.md` — la decisione su dimensione e
flush.

## Le insidie incontrate

**Un file nuovo faceva fallire l'apertura.** `__init__` chiamava
`_file_size()` prima di creare il file; su un file inesistente
`Path.stat()` solleva `FileNotFoundError`. Il bug si vedeva solo sul caso
"database nuovo": il test su un file pre-esistente passava, dando falsa
sicurezza. Risolto facendo restituire `0` a `_file_size()` quando il path
non esiste. Lezione: **il caso "vuoto/nuovo" va testato esplicitamente.**

**Un test che non girava.** `allocate_page_writes_a_zero_filled_page` era
scritta senza il prefisso `test_` (e con un parametro `tmp` invece di
`tmp_path`). pytest non l'ha collezionata: nessun errore, semplicemente il
test della pagina di zeri non è mai stato eseguito. Ce ne siamo accorti
contando i test raccolti. Lezione: un test che non parte è peggio di nessun
test, perché dà falsa sicurezza.

**Hypothesis rifiutava `tmp_path`.** Il property test che alloca N pagine
usava la fixture `tmp_path` con `@given`: Hypothesis ferma il test perché le
fixture function-scoped **non vengono ricreate** tra un input e l'altro, e il
file si accumulerebbe. Risolto creando la directory temporanea **dentro** il
test con `tempfile.TemporaryDirectory()`, così ogni esempio parte pulito.

**Un health check che era un falso positivo.**
`test_write_read_round_trip` genera pagine intere
(`st.binary(min_size=PAGE_SIZE, ...)`) e faceva scattare
`large_base_example`, perché Hypothesis considera "enorme" l'input minimo
di 4096 byte. Ma 4096 è **fisso per progetto**: soppresso con
`@settings(suppress_health_check=[...])` e un commento che spiega il perché.

**Il valore di ritorno di `write` non è decorativo.** Abbiamo aggiunto il
controllo `written == len(data)`: senza, una *short write* lascerebbe una
pagina scritta a metà senza accorgersene.

**Scrivere più di una pagina trabocca.** Nel `write_page` il controllo di
lunghezza è critico, non cosmetico: dati più lunghi di `PAGE_SIZE` a un
offset fisso invadono la pagina successiva e la corrompono.

**Un metodo duplicava una funzione.** Era comparso un metodo
`PageManager.page_offset` identico alla funzione di modulo `page_offset`;
rimosso per non avere due copie della stessa matematica.

**`int(file_size / PAGE_SIZE)` invece di `//`.** Nella prima bozza della
validazione la dimensione veniva divisa con `/` e riconvertita con `int()`.
Con un controllo che garantisce già la divisibilità esatta, la divisione
intera `//` è la scelta corretta e non introduce float.

**`data: bytes` era troppo stretto.** `read_page` restituisce `bytearray`,
che non è un sottotipo di `bytes`: il round-trip `write_page(0, read_page(0))`
sarebbe stato segnalato dal type checker. Corretto in `bytes | bytearray`.

**Il dump esadecimale: formato e allineamento.** Nel primo giro il golden
test dava per scontato un input di 16 byte mentre ne passava 6, e la larghezza
di riempimento della colonna esadecimale era `47` invece di `48`: sulle righe
corte la barra finiva una colonna più a sinistra. Corretti entrambi, e
riempita anche la colonna ASCII per allineare la barra di chiusura.

## Le verifiche fatte

Tutto il modulo è passato attraverso la batteria di verifica del progetto:

- `uv run pytest` → **39 passed** (38 in `tests/storage` + 1 smoke test).
- `uv run ruff check .` → *All checks passed!*
- `uv run ruff format --check .` → tutti i file formattati.
- `uv run basedpyright` → **0 errori**.

Il caso "test non raccolto" è la dimostrazione che il conteggio dei test
raccolti è parte della verifica: un test in meno non produce un fallimento,
produce silenzio.

## Cosa è rimasto aperto

- **`struct` non è stato usato in questo strato.** AGENTS.md lo cita, ma a
  livello di pagina grezza non serve: le pagine sono byte e la dimensione si
  ricava dal file. `struct` diventa essenziale nel modulo slotted-page, dove
  la pagina avrà campi a larghezza fissa (header, slot).
- **Il blocco "opzione B" commentato** dentro `_file_size()` va rimosso prima
  di un commit: il confronto A/B è ormai documentato nell'ADR e nella wiki.
- **Controllo di lettura corta** in `read_page`: oggi assente, opzionale
  (il range valido garantisce la lettura completa sul file regolare).
- **Il modulo 2 (slotted-page)** è il prossimo: gestire record a lunghezza
  variabile dentro una pagina, con slot directory, tombstone e compaction.
