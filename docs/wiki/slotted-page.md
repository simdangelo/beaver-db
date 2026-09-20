# La slotted page: record di lunghezza variabile dentro una pagina

Il page manager ci ha consegnato contenitori identici da 4096 byte. Ma i dati
che vorremo metterci dentro non sono affatto identici: una riga di tabella può
avere un nome corto o lungo, campi opzionali, stringhe di dimensioni diverse.
Come si fa stare contenuto variabile in contenitori fissi, potendo aggiungere,
leggere e cancellare righe, continuando a dare a ogni riga un indirizzo
stabile? La risposta standard è la **slotted page**.

## Contenitori fissi, contenuti variabili

Il primo istinto è sbagliato in un modo istruttivo: se le pagine sono fisse,
perché non rendere fisse anche le righe? Si riserva a ogni riga una lunghezza
massima e la pagina diventa una griglia di caselle uguali. Funziona finché le
righe sono davvero corte, ma appena compare una stringa lunga hai due
possibilità: o la tronchi, o riservi a tutte le righe lo spazio di quella più
lunga e sprechi enormità. Un database non sceglie nessuna delle due.

L'altro istinto è impacchettare le righe una dopo l'altra e identificarle con
la loro **posizione in byte** dentro la pagina. Sembra naturale, ed è fatale:
appena cancelli una riga in mezzo, o ne inserisci una più grande di un buco,
tutto quello che segue deve scorrere — e ogni indirizzo che puntava lì diventa
all'istante sbagliato. Se un indice puntava alla riga "al byte 1024", dopo lo
spostamento quel byte contiene altro.

L'intuizione che scioglie il nodo è separare l'**identità** di una riga dalla
sua **posizione fisica**. L'identità è un piccolo numero stabile; la posizione
può cambiare quanto vuole.

## L'indirezione: lo slot come indirizzo stabile

Una riga si indirizza con il suo **numero di slot**, un intero piccolo e
stabile. Lo slot, a sua volta, contiene l'offset che dice *dove* la riga si
trova davvero nella pagina. Se la riga si sposta, cambia solo il numero dentro
lo slot; il numero di slot — cioè l'indirizzo della riga — resta identico.

Questo è lo stesso trucco che il page manager usa un livello sopra: lì
"pagina 5" è un'identità stabile e l'offset `5 × PAGE_SIZE` è la posizione, e
nessuno tiene in mano l'offset. Qui, un livello sotto, "slot 5" è l'identità e
l'offset dentro la pagina è la posizione. L'indirezione è il cuore di tutta la
faccenda.

Da qui nasce il **Record ID**: la coppia `(page_id, slot)`. Il page id dice
*in quale pagina*, lo slot dice *quale riga dentro quella pagina*. È
l'indirizzo con cui heap file e indici si riferiranno alle righe nei moduli
successivi.

## Il layout di una pagina a slot

Dentro la pagina convivono tre cose: i metadati, l'elenco degli slot e i dati
veri e propri. La disposizione standard li mette in questo modo:

```
inizio pagina  +--------------------------------+
               | header di pagina               |  metadati (num slot, confini, ...)
               +--------------------------------+
               | slot 0 | slot 1 | slot 2 | ... |  lo slot array cresce verso la fine
               +--------------------------------+
               |                                |
               |         spazio libero          |  la zona contesa dai due lati
               |                                |
               +--------------------------------+
               | ... | tupla 2 | tupla 1 | tupla 0 |  i dati crescono verso l'inizio
fine pagina    +--------------------------------+
```

L'header sta in cima. Lo **slot array** parte subito dopo l'header e cresce
**verso la fine** della pagina. I **dati delle tuple** partono dalla fine e
crescono **verso l'inizio**. In mezzo resta lo **spazio libero**, l'unica zona
che entrambi possono reclamare. La pagina è piena quando i due fronti si
incontrano.

Questo arrangiamento non è un vezzo: entrambe le regioni crescono nello stesso
spazio invece di avere due riserve separate, e crescono da lati opposti. Aggiungere
uno slot è un piccolo innesto a dimensione fissa da un lato; aggiungere una
tupla è un innesto a dimensione variabile dall'altro. I due fronti sono due
numeri che tieni nell'header: il prossimo slot libero e il punto in cui iniziano
i dati.

Su disco o in memoria, una pagina sono sempre `PAGE_SIZE` byte, e la slotted
page li interpreta secondo questo formato e li **modifica in posto**, senza
spostare la pagina né copiarla. Nel nostro progetto quei byte, in memoria,
sono una `bytearray` di `PAGE_SIZE`, e la slotted page è la logica che li
legge e li scrive.

## Lo slot: un puntatore a dimensione fissa

Ogni slot è una voce di **dimensione fissa** che contiene l'offset dove inizia
la sua tupla; facoltativamente anche la lunghezza della tupla. Il fatto che sia
a dimensione fissa è ciò che rende lo slot array indicizzabile con
un'aritmetica semplicissima: lo slot numero `k` comincia a `header + k ×
dimensione_slot`. È la stessa moltiplicazione del page manager, applicata un
livello sotto.

Nota che la lunghezza della tupla puoi registrarla in due posti: nello slot
oppure nell'header della tupla. Scegline uno, non entrambi; ma da qualche parte
deve stare, altrimenti non sai dove finisce una tupla e comincia la
successiva.

## Inserire una tupla

L'inserimento è una piccola coreografia:

1. **Verifica lo spazio.** Ti serve spazio per la tupla *e* per un nuovo slot,
   se non hai uno slot libero da riusare. Se non c'è, la pagina è piena e la
   responsabilità passa a chi gestisce le pagine (il futuro heap file).
2. **Scegli lo slot.** Se esiste uno slot libero — lasciato da una
   cancellazione — riusalo. Altrimenti aggiungi un nuovo slot in coda
   all'array, allargandolo di una voce.
3. **Scrivi la tupla** a partire dall'attuale confine dei dati, che avanza
   verso l'inizio della dimensione della tupla.
4. **Aggiorna lo slot** perché punti alla tupla appena scritta.

Riutilizzare gli slot liberi non è un'ottimizzazione marginale: se ogni
insert aggiungesse sempre uno slot nuovo, l'array crescerebbe all'infinito
anche cancellando e reinserendo di continuo, mangiandosi lo spazio dei dati.

## Cancellare: la tombstone

Cancellare una tupla **non** significa rimuoverne i byte. Farlo sposterebbe
tutte le tuple successive e invaliderebbe i loro offset. La cancellazione è
**logica**: lo slot viene marcato come libero — per esempio l'offset viene
messo a un valore sentinella, oppure si usa un flag — e questo si chiama
**tombstone**. Da quel momento lo slot è disponibile per un nuovo inserimento,
ma il numero di slot non cambia e nessuno degli altri indirizzi si sposta.

Da notare: non si rimuove mai lo slot dall'array, perché rimuoverlo
sposterebbe gli indici di tutti gli slot successivi, cioè cambierebbe
l'indirizzo delle righe. Un array di slot con dei "buchi" è normale e
accettabile; un array di slot i cui indici cambiano non lo è.

## Compaction e frammentazione

Le cancellazioni lasciano buchi. Un nuovo inserimento può riusare un buco solo
se la tupla è abbastanza piccola; se è più grande, il buco resta lì e lo spazio
libero si **frammenta** in tanti piccoli spazi inutilizzabili. Col tempo una
pagina può sembrare piena — i due fronti sono vicini — pur avendo molto spazio
sprecato in buchi.

La soluzione è la **compaction**: far scorrere le tuple vive tutte verso la
fine, compattandole, e aggiornare di conseguenza gli offset negli slot. Le
tuple si spostano fisicamente, ma **gli slot non cambiano numero**: grazie
all'indirezione, l'indirizzo delle righe resta stabile. È esattamente il
momento in cui l'indirezione paga il suo prezzo.

Quando compattare è un compromesso classico:

- **a ogni cancellazione o inserimento**: lo spazio libero resta sempre
  contiguo e facile da gestire, ma ogni scrittura paga lo spostamento.
- **pigra, o mai**: le scritture sono veloci, ma la frammentazione può rendere
  una pagina "piena" quando non lo è.

I sistemi reali differiscono, ed entrambe le scuole sono valide: PostgreSQL,
per esempio, non compatta sugli insert, mentre SQL Server sì.

## Header di pagina e header di tupla

L'**header di pagina** tiene i metadati necessari: il numero di slot, i due
confini (prossimo slot libero e inizio dei dati), e i flag di stato. Nei
sistemi reali può contenere anche checksum, versione, o informazioni di
visibilità transazionale; qui prendiamo solo ciò che usiamo davvero.

L'**header di tupla** sta davanti ai dati della tupla e contiene almeno la sua
lunghezza (se non l'hai messa nello slot); facoltativamente una **bitmap dei
NULL**, cioè un bit per colonna che dice se quella colonna è NULL. La bitmap è
il modo più comune di rappresentare i NULL senza inventare un valore sentinella
per ogni tipo, che sarebbe ambiguo (e se il valore sentinella fosse un dato
legittimo?).

Il formato binario esatto di header e slot è una decisione del progetto, non
una legge: cambia il formato, cambiano i file, e in sviluppo i file si
ricreano. Qui è fissato nell'[ADR 0002](../adr/0002-formato-slotted-page.md):
header di 4 byte e slot di 4 byte, tutti interi senza segno da 2 byte in
little-endian. Le sezioni seguenti lo mostrano **in byte**, con i disegni della
pagina dopo ogni operazione; i meccanismi di Python per leggere e scrivere quei
byte sono in
[`../knowledge/struct-e-buffer.md`](../knowledge/struct-e-buffer.md).

## Il formato concreto: header e slot in byte

La pagina è una sequenza di byte, e al suo interno ci sono due tipi di voci a
dimensione fissa. L'**header di pagina** occupa i primi **4 byte**: `num_slots`
(quanti slot sono allocati, tombstone inclusi) e `data_start` (a quale offset
inizia la zona dei dati). Ogni **slot** occupa **4 byte** subito dopo l'header:
`offset` (dove inizia il record) e `length` (quanti byte è lungo). Tutti e
quattro i campi sono interi senza segno da 2 byte in little-endian, quindi
stanno nel formato `"<HH"`.

Due valori speciali riassumono lo stato della pagina. `data_start == 0` indica
una pagina **non formattata**: una pagina appena allocata è tutta zeri e va
inizializzata a `num_slots = 0`, `data_start = PAGE_SIZE`. Un record con
`offset == 0` è uno slot **libero**, cioè un tombstone. Lo slot numero `k`
comincia sempre a `HEADER_SIZE + k * SLOT_SIZE`, quindi trovarlo è una
moltiplicazione.

## Esempio: una slotted page da 32 byte

Una pagina reale è da 4096 byte, scomoda da disegnare tutta. Usiamo una **pagina
giocattolo da 32 byte** con lo stesso formato: header di 4 byte e slot di 4 byte
ciascuno. Nei disegni ogni scatola corrisponde a una zona della pagina: header e
slot sono scatole **fisse e uguali**, lo **spazio libero è un unico blocco**, e i
dati stanno in coda.

### Pagina nuova, formattata

Una pagina appena allocata è tutta zeri. La formattiamo scrivendo
`num_slots = 0` e `data_start = 32`.

```
+--------+---------------+
| header | spazio libero |
+--------+---------------+
  4 byte      28 byte
```

`data_start` vale 32, cioè punta alla fine della pagina: quando arriveranno i
dati, calerà.

### Inseriamo il record `"AB"` (2 byte)

L'inserimento tocca i due estremi: la voce dello slot in testa, i byte del record
in coda. I due byte di `"AB"` sono `41 42`, le loro codifiche ASCII. Il record va
in fondo, quindi il confine dei dati arretra: `data_start` cala da 32 a 30, e i
due byte finiscono negli offset 30 e 31. La voce del nuovo slot, da 4 byte, si
aggiunge subito dopo l'header.

```
+--------+--------+---------------+---------+
| header | slot 0 | spazio libero | tupla 0 |
+--------+--------+---------------+---------+
  4 byte   4 byte      22 byte       2 byte
```

L'header ora ha `num_slots = 1` e `data_start = 30`; lo slot 0 punta al record
con `offset = 30` e `length = 2`, e chiamiamo quel record **tupla 0**, dal numero
dello slot che lo identifica.

### Inseriamo il record `"CDE"` (3 byte)

I byte di `"CDE"` sono `43 44 45`. `data_start` cala da 30 a 27, i byte vanno
negli offset da 27 a 29, e un secondo slot da 4 byte si aggiunge dopo il primo.

```
+--------+--------+--------+---------------+---------+---------+
| header | slot 0 | slot 1 | spazio libero | tupla 1 | tupla 0 |
+--------+--------+--------+---------------+---------+---------+
  4 byte   4 byte   4 byte      15 byte       3 byte    2 byte
```

I dati sono 5 byte in coda: `"CDE"` agli offset 27-29 e `"AB"` agli offset 30-31.
L'ultimo record inserito (`"CDE"`) sta **prima** del primo (`"AB"`), perché i
record si accodano dalla fine verso l'inizio. Il numero della tupla segue lo
slot, non l'ordine fisico: a sinistra c'è la **tupla 1** (`"CDE"`, slot 1) e a
destra la **tupla 0** (`"AB"`, slot 0). L'header ora ha `num_slots = 2` e
`data_start = 27`.

### Cancelliamo lo slot 0

Cancellare un record non tocca i byte dei dati: si marca **solo lo slot** come
libero (`offset = 0`, `length = 0`), il cosiddetto tombstone. L'header non
cambia, perché il numero di slot resta 2 e `data_start` resta 27.

```
+--------+--------+--------+---------------+---------+---------+
| header | libero | slot 1 | spazio libero | tupla 1 | tupla 0 |
+--------+--------+--------+---------------+---------+---------+
  4 byte   4 byte   4 byte      15 byte       3 byte    2 byte
```

I byte della **tupla 0** (`"AB"`) in fondo sono ancora al loro posto, ma nessuno
slot li indica più: sono un buco che la compaction potrà recuperare. Il numero di
slot non è cambiato, quindi gli indirizzi fatti di pagina e slot restano validi.

Questo comportamento rivela una proprietà generale: a contare sono l'header e
gli slot, mentre i byte dei dati sono inerti finché nessuno slot li indica. La
stessa proprietà vale per l'operazione opposta, cioè **formattare una pagina**:
si riscrive l'header allo stato iniziale (`num_slots = 0`,
`data_start = PAGE_SIZE`) e i vecchi byte restano nel buffer ma fuori dalla zona
usata, quindi ignorati. Non serve azzerare i 4096 byte.

### Compattiamo

La compaction sposta i record vivi verso la fine. L'unico vivo è la **tupla 1**
(`"CDE"`, slot 1): la spostiamo agli offset 29-31, `data_start` diventa 29, e lo
slot 1 punta lì. La tupla 0 era cancellata, quindi il suo spazio viene recuperato
e sparisce; lo slot 0 resta libero.

```
+--------+--------+--------+---------------+---------+
| header | libero | slot 1 | spazio libero | tupla 1 |
+--------+--------+--------+---------------+---------+
  4 byte   4 byte   4 byte      17 byte       3 byte
```

Gli offset 27 e 28 contengono ancora `43 44`, cioè "C" e "D", residuo della
posizione precedente: spostare un record **non cancella i byte vecchi**. Non è
un problema, perché quei byte sono dentro lo spazio libero e nessuno li legge:
**lo spazio libero è definito dall'header, non dal valore dei byte**. Il prossimo
inserimento scriverà sopra quei byte, rimpiazzandoli.

## Dalla pagina giocattolo a quella vera

La pagina vera è di **4096 byte**: stessa struttura, molti più byte. Il numero
massimo di slot è all'incirca `(4096 − 4) / 4`, cioè poco più di mille. In
Python questi byte si leggono e scrivono con `struct`: l'header è un `"<HH"`
all'offset 0, e lo slot numero `k` è un `"<HH"` a `HEADER_SIZE + k * SLOT_SIZE`.

## Le insidie

**Due fronti che si scontrano.** Slot array e dati crescono l'uno verso
l'altro: se non calcoli lo spazio per il nuovo slot *e* per la nuova tupla
prima di scrivere, i due fronti si sovrascrivono e la pagina si corrompe.

**Compattare l'array degli slot.** Non rimuovere mai gli slot cancellati: gli
indici degli slot successivi cambierebbero, tradendo ogni Record ID. Il buco
resta, lo slot si riusa.

**Confondere numero di slot e offset.** Il primo è l'identità stabile della
riga, il secondo è volatile. Se nel mondo esterno esporti l'offset al posto del
numero di slot, la compaction rompe tutto.

**Non registrare la lunghezza.** Senza la lunghezza (nello slot o nell'header
della tupla) non sai dove finisce una tupla: con dati a lunghezza variabile
non esiste un "fine" implicito.

**Frammentazione invisibile.** Considerare "piena" una pagina solo perché i
fronti sono vicini è un errore se lo spazio è di fatto buchi inutilizzabili:
serve una politica di compaction.

**I buchi si spostano, non svaniscono.** Anche la compaction ha un costo e va
temporizzata; compattare a ogni operazione è semplice ma lento, non compattare
mai accumula fragilità.

## Struttura e persistenza: la slotted page non tocca il disco

Una slotted page non legge né scrive file. Il suo mestiere è organizzare i byte
di **una pagina già in memoria**: sa dove stanno header, slot e record, e li
modifica. Chi porta le pagine dal disco alla memoria e viceversa è un altro
componente, il **page manager** (vedi
[`page-manager.md`](page-manager.md)): per lui una pagina è un blocco opaco di
`PAGE_SIZE` byte, e non sa nulla di slot e record. Il page manager sposta
contenitori chiusi; la slotted page decide come sistemarne il contenuto.

La separazione si vede nel flusso di un'operazione: si legge una pagina dal
disco (una `bytearray` di 4096 byte), la si avvolge in una slotted page, si
inseriscono o si leggono record, e infine si riscrive la pagina intera su
disco. Il primo e l'ultimo passo sono del page manager, quelli in mezzo della
slotted page. "Scrivere" significa quindi due cose diverse: la slotted page
scrive campi **nella `bytearray` in memoria**, il page manager scrive la
pagina **sul disco**. In concreto, usare i due livelli insieme è questo:

```python
pm = PageManager("database.bin")
data = pm.read_page(0)  # 1. dal disco alla memoria (bytearray di PAGE_SIZE)
page = SlottedPage(data)  # 2. la logica che dà struttura ai byte
slot = page.insert(b"record")  # 3. modifica i byte in memoria
pm.write_page(0, data)  # 4. dalla memoria al disco (la pagina intera)
```

Questa divisione ha due vantaggi. La slotted page si può provare senza file,
basta una `bytearray` da `PAGE_SIZE`; e il modo di leggere e scrivere le
pagine su disco si cambia in un punto solo, senza toccare la logica della
struttura. In futuro, tra i due livelli si inserirà il **buffer pool**, la
cache di pagine che si occupa di tenerle in memoria e riscriverle (vedi
[`buffering-e-flush.md`](buffering-e-flush.md)): le pagine verranno chieste a
lui, ma sotto il meccanismo resterà lo stesso.

## Dove va a parare: il heap file

Una slotted page sa organizzare *una* pagina; ma in quale pagina inserire una
nuova riga? Non lo decide lei. Sarà il **heap file** (modulo successivo) a
tenere l'elenco delle pagine e a scegliere quella con spazio libero, usando la
page directory. Il Record ID `(page_id, slot)` è ciò che tiene insieme i due
livelli: la pagina è il contenitore, lo slot è la riga, e il heap file è la
tabella fatta di contenitori.
