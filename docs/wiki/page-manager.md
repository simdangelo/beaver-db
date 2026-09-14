# Il file a pagine fisse: come il database vede il disco

Un database deve sopravvivere al processo che lo usa. Quando il programma
termina, o il computer si spegne, i dati devono restare da qualche parte:
da questa esigenza nasce il disco, inteso nel senso più largo del termine —
un supporto fisico che conserva i byte anche a processo spento. In un
database didattico come questo il disco è un semplice file, ma il ragionamento
che stai per leggere vale identico per un'SSD da un terabyte. La domanda di
fondo è: *in che modo* il database scrive i suoi dati su quel supporto?

La risposta che questo modulo insegna è sorprendentemente semplice: il
database non vede il disco come una zuppa di byte da spargere qua e là, ma
come un file tagliato in pezzi tutti uguali, chiamati **pagine**. Ogni
operazione che un database compirà mai — una lettura, una query, una
transazione — alla fine si riduce a un'unica, banale azione: "portami la
pagina numero 5" oppure "scrivi la pagina numero 7". Tutto il resto è
complicazione costruita sopra questa fondazione. Questo modulo è quella
fondazione.

## Il disco come lo vede un database: un file di byte

La prima cosa da capire è che un file di database non è un documento di
testo: è un **file binario**, cioè un flusso di byte il cui significato lo
conosce solo il database stesso. Non contiene righe leggibili a occhio nudo
e non ha nulla a che fare con i file di configurazione che hai scritto fino
a oggi. È una sequenza grezza di numeri tra 0 e 255 — i byte, appunto — e
siamo noi, a strati, a decidere cosa significano.

È importante questa distinzione perché l'ho visto inciampare molti. A un
certo punto del percorso vorrai "leggere una tabella" e guarderai il file,
ma il file non contiene né tabelle né record: contiene solo byte. I record
appariranno nei moduli successivi (la slotted page prima, l'heap file dopo),
costruiti uno sopra l'altro. Il **page manager** — questo modulo — non sa
nulla di tabelle: sa solo che esiste un file, che il file è fatto di pagine,
e che una pagina si legge o si scrive per intero. Questa ignoranza è una
forza: ogni livello si occupa del suo problema e non deve conoscere gli
altri.

## Perché le pagine, e perché tutte di una stessa dimensione

Immagina un magazzino in cui ogni cassa è identica alle altre: stessa
larghezza, stessa altezza, stesso volume. Se so che le casse sono tutte di
dimensioni uguali e sono impilate in fila senza buchi, per raggiungere la
centesima cassa non devo cercarla: so che starà a "centesimo × larghezza di
una cassa" dall'inizio della fila. Il database ragiona esattamente così, e
questa è l'intuizione fondamentale di tutto il modulo.

Ma perché il database taglia il file in pagine invece di scrivere i dati
dove capita? I motivi sono tre e sono tutti profondi.

Il primo è l'**indirizzamento**: per leggere una cosa devi sapere *dove*
sta. Se i dati avessero lunghezze e posizioni qualunque, per trovare un
record dovresti consultare una tabella che ti dice "il record X sta
all'offset 12345", e quella tabella andrebbe a sua volta salvata da qualche
parte, e quella a sua volta... un rinvio all'infinito. Con pagine di
dimensione fissa il problema sparisce: un indirizzo è un numero di pagina, e
dalla pagina si arriva alla posizione nel file con una sola moltiplicazione.
Niente tabelle, niente ricerche, nessuna struttura che punta a un'altra
struttura.

Il secondo è l'**hardware**. Il sistema operativo organizza la memoria
principale in blocchi da 4096 byte chiamati anch'essi pagine, e i supporti
fisici trasferiscono i dati a blocchi (sul disco tradizionale si parla di
settori, sugli SSD moderni di blocchi da 4096 byte). Se il database lavora
con unità delle stesse dimensioni, il passaggio da e verso il disco avviene
in modo naturale, senza frammentare letture e scritture in pezzetti
inefficienti.

Il terzo è la **granularità**: quando il database scrive "la pagina 7", sa
di aver scritto esattamente 4096 byte, né più né meno. Questa certezza sarà
fondamentale nei moduli successivi, quando il buffer pool dovrà decidere
quali pagine tenere in memoria e quali riscriverle su disco, e quando il
log (se mai lo implementerai) dovrà registrare che cosa è cambiato.

Nota un dettaglio: le pagine non sono solo di dimensione fissa, sono anche
**tutte della stessa dimensione**. La dimensione fissa è ciò che rende
possibile la matematica dell'offset; l'uguaglianza delle dimensioni è ciò che
rende uniforme il magazzino. Se le casse fossero di misure diverse, la
moltiplicazione dell'esempio non funzionerebbe più e dovresti annotarti
dove inizia ogni cassa. Il vantaggio di lavorare con una sola misura è che
l'indirizzamento diventa aritmetica pura.

## L'indirizzo universale: il page ID e la matematica dell'offset

L'indirizzo di una pagina nel file è un numero intero chiamato **page ID**.
È il linguaggio con cui tutti i livelli superiori del database si riferiranno
ai dati: non parleranno di "byte 100000" ma di "pagina 24". Questo numero è
la prima di una serie di astrazioni — nei moduli futuri incontrerai il
Record ID, che indicherà un record specifico dentro una pagina — e vale la
pena di abituarsi subito all'idea: il database costruisce il suo *proprio*
spazio degli indirizzi, fatto di numeri di pagina, invece di usare gli
indirizzi di memoria del computer.

Il collegamento tra page ID e posizione nel file è la moltiplicazione:

```
pagina 0  → offset 0
pagina 1  → offset 4096
pagina 2  → offset 8192
pagina N  → offset N × 4096
```

In codice è un'unica, minuscola funzione:

```python
PAGE_SIZE = 4096


def page_offset(page_id: int) -> int:
    """Offset nel file del primo byte della pagina data."""
    return page_id * PAGE_SIZE
```

L'**offset** è il numero di byte dall'inizio del file a cui comincia una
certa zona; l'offset della pagina N è la sua prima posizione, e la pagina
occupa esattamente `PAGE_SIZE` byte da lì in poi, fino all'offset
`(N + 1) × PAGE_SIZE - 1` incluso.

Vale la pena fermarsi sul perché di quel `- 1`, perché è qui che nasce
l'errore di uno. Gli offset sono **0-based**: la pagina N parte dal byte
`N × PAGE_SIZE`, e da lì conta `PAGE_SIZE` byte, quindi indici da `0` a
`PAGE_SIZE - 1`. L'ultimo è dunque `N × PAGE_SIZE + (PAGE_SIZE - 1)`, che
semplificando diventa `(N + 1) × PAGE_SIZE - 1`. Il valore
`(N + 1) × PAGE_SIZE`, senza il `- 1`, **non è un byte della pagina N**: è il
primo byte della pagina N+1, cioè la sua fine *esclusa*. Confondere estremo
incluso ed estremo escluso è l'off-by-one per eccellenza; tenere a mente che
`(N + 1) × PAGE_SIZE - 1` è l'ultimo byte incluso della pagina N, mentre
`(N + 1) × PAGE_SIZE` è il primo byte della prossima pagina, è ciò che
tiene diritta la frontiera.

Questo è tutto l'indirizzamento del page
manager: un indirizzo, una moltiplicazione, una posizione. Quando più avanti
scriverai il tuo primo vero bug di "un byte in più o in meno", il sospetto
ricadrà quasi sempre proprio su questa frontiera — il punto esatto in cui
una pagina finisce e la successiva comincia.

## Leggere e scrivere una pagina: bytearray e struct

Per leggere una pagina si porta su in memoria un buffer di esattamente
`PAGE_SIZE` byte e lo si riempie con i byte del file a partire dall'offset
calcolato. "Buffer" qui significa semplicemente una zona di memoria
contigua; il tipo giusto in Python per questo lavoro è il **bytearray**, una
sequenza *mutabile* di byte. Il suo parente `bytes` è invece *immutabile*:
una volta creato non si modifica, e ogni cambiamento produce un nuovo
oggetto. Siccome una pagina la leggerai, la modificherai e la riscriverai,
serve la versione mutabile. `bytearray(PAGE_SIZE)` crea un buffer di 4096
byte inizializzati a zero: è già, di per sé, la rappresentazione di una
pagina vuota, concetto che ritroverai tra poco.

Ecco il gesto fondamentale del modulo, la lettura di una pagina:

```python
data = bytearray(PAGE_SIZE)
with open("database.bin", "rb") as f:
    f.seek(page_id * PAGE_SIZE)
    f.readinto(data)
```

Vale la pena smontarlo riga per riga, perché ogni pezzo nasconde un
concetto. `open(..., "rb")` apre il file in **modalità binaria**: leggerai
byte grezzi e il sistema operativo non tradurrà nulla. Aprire in modalità
testo (`"r"`) è un errore classico, perché in quella modalità il sistema
operativo traduce certi byte (i fine riga) e corromperebbe i dati: un file
di pagine si apre sempre con la `b`, in lettura (`"rb"`), scrittura (`"wb"`)
o entrambe (`"r+b"`). Il `with` è un *context manager*: garantisce che il
file venga chiuso alla fine del blocco anche se qualcosa va storto, senza
che tu debba ricordarti di chiamare `close`. `f.seek(offset)` sposta la
"testina" di lettura — la posizione da cui comincerà la prossima lettura —
al byte che ti interessa, `page_id * PAGE_SIZE`. Infine `f.readinto(data)`
legge i byte che seguono quella posizione e li **scrive dentro** il buffer
che gli passi, riempiendolo; il nome lo dice: legge "into", dentro, un
contenitore che esiste già. La differenza con `read()` è proprio questa:
`read()` restituisce un nuovo `bytes` immutabile, mentre `readinto` riempie
il `bytearray` che hai già. `readinto` restituisce anche quanti byte ha
effettivamente letto; qui lo ignoriamo dando per scontato che il file sia
lungo abbastanza, ma quel valore va sempre controllato (lo ritroverai nelle
insidie).

Finito il `with`, `data` è una **copia in memoria** dei 4096 byte della
pagina, indipendente dal file: le modifiche che farai al buffer non toccano
il disco finché non riscrivi la pagina. La scrittura è il gesto speculare,
`seek` più `write`:

```python
with open("database.bin", "r+b") as f:
    f.seek(page_id * PAGE_SIZE)
    f.write(data)
```

Qui `"r+b"` apre in lettura e scrittura conservando il contenuto esistente
(`"wb"`, al contrario, troncherebbe il file a zero). `f.write(data)` copia i
4096 byte del buffer sul disco a partire dall'offset. Il ciclo completo è
quindi: `readinto` porta i byte da disco a RAM, tu modifichi il buffer,
`write` li riporta da RAM a disco. Tutto il resto del database è costruito
su questo andirivieni.

A questo punto hai una pagina in memoria, ma è ancora una scatola opaca di
byte. Come si fa a leggere e scrivere *valori* dentro quella scatola? La
risposta è il modulo `struct` della libreria standard: `struct` impacchetta
e spacchetta numeri secondo un formato preciso, dicendo "scrivi un intero
da 4 byte a questa posizione del buffer". Il gesto tipico è:

```python
import struct

struct.pack_into("<I", data, 8, 12345)  # scrive l'intero 12345 all'offset 8
value = struct.unpack_from("<I", data, 8)[0]  # lo rilegge
```

Il formato `"<I"` è un linguaggio in miniatura: `<` significa *little-endian*
(tra un attimo), `I` significa intero senza segno da 4 byte. `pack_into` e
`unpack_from` lavorano dentro un buffer esistente a un offset preciso, senza
copiare porzioni di byte da una parte all'altra: è esattamente ciò che serve
per costruire e smontare una pagina come se fosse una griglia di campi.

Perché `struct` e non `pickle` o `json`, che sarebbero più comodi? Perché
`pickle` scrive su disco la rappresentazione interna degli oggetti Python:
il formato è deciso da Python, è fragile tra versioni, e tu non controlli
un singolo byte. `json` al contrario è un formato testuale, leggibile ma
gigantesco per un database e inadatto a occupare spazi precisi dentro una
pagina. Il `struct` invece mette in fila i byte esattamente come gli dici
tu: il formato su disco è sotto il tuo controllo, deterministico, e ogni
byte ha un perché. Questa è la filosofia dell'intero progetto — i byte si
scrivono a mano, non si delega la persistenza a una libreria che nasconde
il lavoro.

### Il byte order: quale estremità scrive per prima

Quando scrivi l'intero `12345` su 4 byte, c'è una domanda da decidere: quale
estremità del numero finisce per prima nel file? Puoi scrivere il byte più
significativo per primo (**big-endian**, "grande estremità per prima") o il
meno significativo per primo (**little-endian**, "piccola estremità per
prima"). La quasi totalità dell'hardware moderno (x86, ARM) lavora in
little-endian, ma non è una legge di natura: due macchine potrebbero leggere
gli stessi byte come numeri diversi se non concordassero l'ordine.

Per questo il formato della pagina *deve* fissarlo, e si fissa nel formato
del `struct`: il prefisso `<` (o `=`) dice "little-endian e senza
allineamento". Se non lo metti, `struct` usa l'ordine e l'allineamento
nativi della macchina, e il file risulterebbe diverso a seconda di dove
gira — un difetto di portabilità inaccettabile per un formato su disco. Se
vuoi sapere quanto spazio occupa un formato, `struct.calcsize("<I")` ti
risponde (4 byte per un intero, senza sorprese). Senza il prefisso che
disattiva l'**allineamento** — i byte di riempimento che il processore
inserisce per allineare i campi — `calcsize` può restituire numeri più
grandi della somma dei campi, e ti ritroveresti buchi misteriosi tra i dati.

## Far crescere il file: l'append di una pagina

Un file di pagine nasce vuoto e cresce in un modo solo: aggiungendo una
pagina in coda. Se il file contiene finora 10 pagine, la pagina 10
comincia all'offset `10 × PAGE_SIZE`, e il file deve diventare abbastanza
lungo da contenerla. Scrivere *oltre* la fine del file lo estende
automaticamente, riempiendo di zeri lo spazio vuoto tra la vecchia fine e
il punto scritto — un comportamento del sistema operativo che in pratica
significa: "la pagina N esiste" se e solo se il file è lungo almeno
`(N + 1) × PAGE_SIZE` byte.

Da qui due conseguenze. La prima: una pagina appena creata è **vuota**, cioè
tutta di zeri, e gli zeri sono una rappresentazione lecita di "pagina senza
dati" — non un errore. La seconda: leggere una pagina che sta oltre la fine
del file non è come leggere una pagina vuota, è come chiedere una pagina che
non esiste; il gesto corretto è prima controllare la dimensione del file e
rispondere "non c'è" invece di restituire byte fasulli. La distinzione tra
"pagina vuota" e "pagina inesistente" è sottile ma importante, e tornerà
nei moduli futuri quando si dovrà decidere dove inserire un nuovo record.

Un controllo di sanità che paghi imparare ora: la dimensione del file
dovrebbe essere sempre un multiplo esatto di `PAGE_SIZE`. Se un giorno il
file avrà una lunghezza che non lo è, qualcosa ha scritto a metà una
pagina — un'operazione interrotta, un errore di offset — e il file è da
considerare corrotto.

Come si legge concretamente quella dimensione, e perché il buffer delle
scritture può farla sembrare più corta del previsto, è il tema della wiki
[`buffering-e-flush.md`](buffering-e-flush.md) — utile prima di implementare
`num_pages()`.

## Il dump esadecimale: mettere gli occhi sui byte

Un file binario è invisibile: `cat` lo mostra come una sequenza di simboli
incomprensibili, e nessun editor di testo ti dirà se la pagina 3 è giusta.
Il database però ha bisogno di *vedere* i byte per verificare di averli
scritti bene, ed è qui che entra il **dump esadecimale**: una stampa del
file in cui ogni byte è mostrato come due cifre esadecimali, affiancate in
gruppi, con a lato l'offset di inizio riga e, di solito, la versione ASCII
dei byte leggibili.

```
00000000  00 00 00 00 00 00 00 00  00 00 39 30 00 00 00 00  |..........90....|
00000010  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
```

L'**esadecimale** è una notazione in base 16 — le cifre 0–9 e le lettere
a–f — che rappresenta un byte (un numero tra 0 e 255) con esattamente due
caratteri: ogni valore di byte ha una e una sola forma di due cifre. Per
questo è la lingua franca dell'ispezione binaria: compatto, univoco, e con
la pratica lo leggi come un nativo.

Il dump è un *riflesso fedele*: ti dice quali byte ci sono e in quale
ordine, senza interpretarli. È il *tuo* compito interpretarli secondo il
formato che hai definito, ed è qui che l'occhio umano sbaglia. In questo
file di esempio i byte in posizione 8 e 9 sono `39 30` (il dump li mostra
nell'ordine in cui stanno nel file, cioè il primo byte scritto a sinistra).
Se il formato dice little-endian — il byte meno significativo va scritto per
primo — allora `39` è la cifra bassa e `30` quella alta, e i due byte
formano `0x3039`, che in decimale è 12345. Sembra un dettaglio da niente, ma
invertire l'ordine di lettura restituirebbe `0x3930`, cioè 14640: un numero
diverso, e i dati diventerebbero silenziosamente sbagliati. La disciplina di
leggere i byte nell'ordine in cui stanno è esattamente ciò che ti evita la
metà dei bug di questo modulo.

Quando scriverai il tuo dump, l'architettura è sempre la stessa: per ogni
gruppo di 16 byte, stampa l'offset del gruppo in esadecimale, i byte come
coppie di cifre separate da spazi, e i caratteri stampabili accanto (i byte
non stampabili vanno rappresentati con un punto). Questo strumento, banale
come sembra, sarà il tuo microscopio per *tutti* i moduli a venire: quando
una query restituirà un risultato sbagliato, la prima domanda sarà "cosa
c'è davvero sul disco?", e il dump è l'unico modo per rispondere con
certezza, perché i byte non mentono.

## Trade-off: quanto deve essere grande una pagina

La scelta della dimensione della pagina è uno dei classici compromessi del
database design. Una pagina più piccola spreca meno spazio quando i dati
sono pochi — leggi un blocco da 4KB anche se il tuo record occupa 40 byte —
e rende più frequenti le operazioni di I/O per ogni record. Una pagina più
grande ammortizza meglio ogni singola lettura dal disco, ma riempi di dati
inutili una zona che non ti serve e, quando il buffer pool dovrà tenerla in
memoria, occuperà più RAM per ogni pagina. Come spesso accade in questo
campo, il valore giusto non esiste in assoluto: esiste il valore giusto per
il tuo carico di lavoro.

Per un database didattico la scelta di 4096 byte è però più che ragionevole,
ed è quella su cui si fondano sistemi reali come SQLite: coincide con la
dimensione delle pagine del sistema operativo e dei blocchi dei supporti
moderni, e c'è anche un motivo più profondo — circa 4KB è il blocco su cui
l'hardware di solito garantisce **scritture atomiche**: o il blocco intero
arriva su disco, o non arriva nulla. Scrivere su un'unità atomicamente
affidabile è esattamente ciò che un database vuole. Nessuna legge divina lo
impone — i sistemi di punta arrivano a 8KB come PostgreSQL o a 16KB come
InnoDB — ma partire da 4096 significa allineare il tuo database
all'hardware senza pensieri.

## Le insidie: dove il file a pagine morde

Questo modulo è piccolo, eppure concentra in poche righe la maggior parte
degli errori di tutta la parte storage di un database. I più frequenti,
in ordine di apparizione:

**Aprire il file in modalità testo.** `open(file, "r")` traduce i fine riga
e può corrompere i byte; un file di pagine si apre sempre in binario, con
`"rb"`, `"wb"` o `"r+b"` a seconda che si voglia leggere, creare, o leggere
e scrivere. La `b` non è un dettaglio: è la differenza tra un file che è
una sequenza fedele di byte e un file che un altro programma ha già
manomesso.

**Dimenticare il prefisso nel formato di `struct`.** `struct.pack("I", x)`
senza `<` o `=` usa l'ordine dei byte e l'allineamento della macchina su cui
gira. Il file risultante dipende dall'hardware, e `calcsize` può riportare
dimensioni diverse da quelle attese per via dell'allineamento. Il formato
della pagina si fissa con `<` e basta.

**L'errore di uno (off-by-one).** La pagina `N` occupa i byte da
`N × PAGE_SIZE` a `(N + 1) × PAGE_SIZE - 1` incluso. È facilissimo
scrivere o leggere un byte oltre la fine di una pagina e dentro l'inizio
della successiva — magari sovrascrivendo silenziosamente dati che credevi
al sicuro — perché nessuno ti dirà "stai sforando": il file è un'unica
lunga sequenza di byte e non ha concetti di confine. La pagina non è un
oggetto con un muro: è una zona *definita dalle tue moltiplicazioni*.

**Scrivere più byte di una pagina.** Il confine vale in entrambe le
direzioni: dati più lunghi di `PAGE_SIZE` scritti a un offset fisso
**traboccano nella pagina successiva** e la corrompono silenziosamente. Per
questo, prima di scrivere, si verifica che la lunghezza sia esattamente
`PAGE_SIZE`: non è un controllo cosmetico.

**Confondere pagina vuota e pagina inesistente.** Una pagina di zeri è una
pagina che esiste ma non contiene dati; una pagina oltre la fine del file
non esiste affatto. Prima di leggere, controlla la dimensione del file.

**Fidarsi di letture e scritture parziali.** In teoria, `read` e `write`
possono trasferire meno byte di quelli richiesti; sui file normali capita
raramente, ma un programma robusto controlla quanti byte sono stati
effettivamente trasferiti e verifica che una lettura di pagina restituisca
davvero `PAGE_SIZE` byte. Una lettura corta è quasi sempre la firma di un
file corrotto o troncato. Il valore di ritorno di `read`/`write` e le altre
scelte dell'API Python sono in
[`file-binari-in-python.md`](../knowledge/file-binari-in-python.md).

**I numeri magici sparsi nel codice.** `4096` non va scritto a ogni riga:
una sola costante nominata a livello di modulo, `PAGE_SIZE = 4096`, fa in
modo che cambiare la dimensione significhi cambiare un numero in un punto,
non cacciare ogni occorrenza. Lo stesso vale per gli offset di campo: sono
costanti nominate, mai letterali che compaiono dal nulla.

## Dove va a parare: la pagina come contenitore

A questo livello la pagina è una scatola opaca di 4096 byte che si legge e
si scrive per intero. Ma i record di una tabella hanno lunghezze variabili,
e dentro una pagina ci staranno più record — come si fanno stare dati di
misure diverse in contenitori identici? È il problema del modulo successivo,
la slotted page, che costruirà dentro la pagina una piccola struttura (una
directory di slot) per tenere traccia di dove inizia e finisce ogni record.
Il lavoro di questo modulo non cambierà: il file a pagine fisse resterà la
fondazione, e la slotted page ci costruirà sopra. Ogni piano di un edificio
ha bisogno di solai che tengano in piedi il piano di sopra; la pagina è il
solaio del database.