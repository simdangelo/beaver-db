# File binari in Python: leggere, scrivere e gestire i byte

Lavorare con un database significa lavorare con file che non sono testo:
sono sequenze di **byte**. Python offre due livelli di API per toccarli —
l'oggetto file restituito da `open` e i metodi di comodo di `pathlib.Path` —
e scegliere quello giusto, sapendo come ciascuno fallisce, evita un'intera
classe di bug. Questa pagina raccoglie le scelte e le trappole incontrate
scrivendo il page manager.

## Un file binario è una sequenza di byte, non di righe

Un file di database si apre sempre in **modalità binaria** (`"rb"`, `"wb"`,
`"r+b"`, `"w+b"`, `"a+b"`): in modalità testo Python traduce i fine riga e
decodifica i byte, corrompendo dati che per lui non hanno significato. In
binario non c'è encoding, non ci sono righe: solo byte.

Le modalità più usate per un database:

| Modalità | Cosa fa |
|---|---|
| `"w+b"` | crea azzerando il contenuto, poi leggere/scrivere |
| `"r+b"` | apre un file esistente per leggere/scrivere, **non** tronca |
| `"a+b"` | come `r+b`, ma le scritture vanno sempre in coda |

La differenza critica è che `"w+b"` **distrugge** un file esistente. Per
questo un database controlla prima se il file esiste e sceglie la modalità:
aprirne uno nuovo con `"r+b"` fallirebbe, aprirne uno esistente con `"w+b"`
lo svuoterebbe.

## Due livelli di API: lo stream e il Path

La stessa azione — scrivere byte su un file — si fa in due modi, e la scelta
non è stilistica.

Lo **stream** è l'oggetto file restituito da `open`. Vive finché non lo
chiudi, ha una **posizione** interna che sposti con `seek`, e offre
`read`/`write`/`tell`/`flush`. Serve quando devi: controllare *dove* scrivi
(un offset preciso), fare più operazioni sullo stesso file, tenerlo aperto
tra una scrittura e l'altra.

I **metodi di comodo di Path** (`read_bytes`, `write_bytes`) fanno tutto in
un colpo: aprono, leggono o scrivono l'intero contenuto, chiudono. Sono
perfetti per *creare* un file al volo, per esempio in un test. Attenzione
però: `write_bytes` apre in `"wb"` e quindi **tronca**, e non ti dà alcun
handle da riusare né un offset da scegliere.

La regola pratica: nel codice del database si usa lo **stream** (serve il
controllo di posizione); nei test, per preparare un file, va benissimo
**Path**.

## Leggere: `read` contro `readinto`

Due modi per portare byte dal file alla memoria:

- **`read(n)`** restituisce un `bytes` (immutabile) di al più `n` byte.
- **`readinto(buffer)`** riempie un buffer *già esistente* e restituisce
  quanti byte ha scritto, **senza una copia in più**.

Se devi modificare la pagina dopo averla letta, `bytearray` è il buffer
naturale, e `readinto` lo riempie direttamente. Un dettaglio che sorprende:
leggere **oltre la fine del file non è un errore** — `read` restituisce
`b""` e `readinto` restituisce `0`, lasciando il buffer di zeri. Per questo
distinguere "pagina vuota" da "pagina inesistente" richiede un controllo
esplicito del *range*, non del risultato della lettura (il concetto di
pagina è in [`page-manager.md`](../wiki/page-manager.md)).

## `bytes` e `bytearray` non sono la stessa cosa

`bytes` è **immutabile**, `bytearray` è **mutabile**. Una pagina che leggerai
e modificherai è un `bytearray`; un contenuto che passi e non tocchi può
essere `bytes`. `file.write` accetta qualunque oggetto "bytes-like"
(`bytes`, `bytearray`, `memoryview`), quindi non serve convertire in un
senso per scrivere.

Conseguenza per i type hint: `bytearray` **non** è un sottotipo di `bytes`.
Se una funzione restituisce `bytearray` e un'altra accetta `bytes`, passare
il primo al secondo è un errore di tipo. Per un round-trip pulito conviene
dichiarare l'input come `bytes | bytearray`.

## Scrivere: il valore di ritorno di `write` non è decorativo

`file.write(data)` restituisce **quanti byte ha scritto**. Il contratto
dell'API ammette che siano **meno** di `len(data)` (una *short write*): su un
file regolare succede di rado, ma ignorare il valore di ritorno significa
non accorgersi di una pagina scritta solo a metà. Il controllo è:

```python
written = f.write(data)
if written != len(data):
    raise OSError(f"short write: {written} of {len(data)} bytes")
```

Lo stesso vale in lettura: se leggi una pagina e ottieni meno di `PAGE_SIZE`
byte, il file è troncato o corrotto.

## Quando qualcosa va storto: tre categorie di errore

Non tutti i fallimenti sono uguali, e distinguerli rende il codice più chiaro
e i test più espliciti. Tre categorie:

- **Errore di chi chiama**: un argomento di forma sbagliata — un page ID
  fuori range, una lunghezza di dati diversa da quella attesa. È un bug del
  chiamante, non del file: si segnala con un'eccezione **nominata**
  (`PageNotAllocatedError`, `InvalidPageSizeError`) o con `ValueError`.
- **File corrotto**: lo stato su disco è incoerente — per esempio una
  dimensione che non è un multiplo della pagina. Qui l'errore è del *dato*:
  `CorruptFileError`.
- **Fallimento di I/O**: una lettura o scrittura corta, un disco pieno. È il
  livello del sistema operativo: `OSError`.

Usare eccezioni **nominate** invece di un generico `Exception` permette ai
test di scrivere `pytest.raises(CorruptFileError)` e a chi legge di capire
subito *quale* contratto è stato violato. La presenza di una eccezione
dedicata è essa stessa documentazione.

## Le insidie

**Aprire in modalità testo.** `open(file, "r")` traduce i fine riga e
corrompe i byte: per un file di pagine si usa sempre `"rb"`/`"r+b"`/`"w+b"`.

**Credere che `write` significhi "salvato".** I byte finiscono in un buffer,
non sul disco: quando e perché è il tema di
[`buffering-e-flush.md`](../wiki/buffering-e-flush.md).

**Ignorare il valore di ritorno di `read`/`write`.** Una short write o una
lettura corta passano inosservate e lasciano dati incoerenti.

**Usare `Path.write_bytes` come operazione sui dati.** Tronca il file:
va bene per preparare una fixture, è un disastro per aggiornare un database
esistente.

**Confondere "fine del file" con "errore".** `read` oltre EOF restituisce
zero byte in silenzio; sta a te decidere che pagina non esiste.

**Scrivere più byte di quelli previsti.** A un offset fisso, un blocco più
lungo del previsto **trabocca nella zona successiva** e la corrompe: la
verifica della lunghezza non è cosmetica.
