# Il buffer pool: la cache di pagine che evita il disco

Il page manager sa leggere e scrivere pagine intere su disco, ma il disco è
**lentissimo** rispetto alla memoria: un accesso su disco costa ordini di
grandezza più di un accesso in RAM. Se il database leggesse una pagina dal disco
ogni volta che le serve, passerebbe la vita ad aspettare. La soluzione è una
**cache**: tenere in memoria le pagine usate di recente e rileggerle dal disco
solo quando non ci sono. Questa cache si chiama **buffer pool** ed è il
componente che sta tra gli access method (slotted page, heap file, indici) e il
page manager.

## Perché una cache funziona: località e ammortamento

Tre fatti rendono la cache conveniente. Primo, il **disco è lento**: evitare
anche un solo accesso si sente. Secondo, gli accessi sono **locali**: una query
che scorre una tabella rilegge pagine vicine, un indice torna più volte sulla
stessa pagina, un record appena letto verrà probabilmente riletto. Terzo, c'è
l'**ammortamento**: leggere una pagina per una sola tupla ne porta in memoria
molte altre, e riscrivere la pagina intera per una modifica è il prezzo che si
paga una volta per tutte. Tenere quella pagina in RAM significa non ripetere
quel prezzo.

## Cosa c'è dentro: frame e page table

Il buffer pool è un **array di frame** di dimensione fissa: ogni frame contiene
una pagina (nel nostro caso 4096 byte) e i suoi metadati. Il numero di frame è
la **capacità** del pool, e in genere è molto minore del numero di pagine del
database: è una cache, non una copia di tutto.

Per sapere se una pagina è già in memoria serve una mappa da `page_id` a frame,
la **page table** (tipicamente una hash map). Ogni frame porta con sé:

- **quale pagina** contiene;
- un **pin count** (quante parti del sistema la stanno usando);
- un **dirty flag** (se è stata modificata e la copia su disco è vecchia).

```
   page table (page_id -> frame)
   +--------------------------+
   |  page 1  ->  frame 0     |
   |  page 3  ->  frame 1     |
   |  page 7  ->  frame 3     |
   +--------------------------+

   frame 0          frame 1          frame 2          frame 3
  +--------------+ +--------------+ +--------------+ +--------------+
  | page 1       | | page 3       | | (libero)     | | page 7       |
  | pin count: 2 | | pin count: 0 | | pin count: 0 | | pin count: 1 |
  | dirty: no    | | dirty: sì    | | dirty: no    | | dirty: no    |
  +--------------+ +--------------+ +--------------+ +--------------+
```

Il frame 1 tiene la pagina 3, è **sporca** e ha pin count `0`: è la prima
candidata all'eviction. Il frame 0 ha pin count `2`, quindi due parti del sistema
lo stanno usando e non si tocca.

## Pin e unpin: chi sta usando una pagina

Una pagina non può essere buttata fuori mentre qualcuno la sta leggendo o
modificando. Per questo, prima di usarla, un componente la **pinna**: il pin
count sale di uno, e la pagina diventa non eleggibile per l'eviction. Quando ha
finito, la **unpinna** e il conteggio scende. Solo le pagine con pin count `0`
possono essere rimpiazzate.

Il pin è la salvaguardia contro un errore sottile: se il buffer pool buttasse
fuori una pagina che un operatore sta ancora leggendo, quel puntatore
punterebbe a memoria riciclata, e il risultato sarebbe spazzatura.

## Hit e miss: fetch, eviction, flush

L'operazione base è **fetch** di una pagina:

- **hit**: la pagina è già nella page table → la si pinna e la si restituisce,
  senza disco;
- **miss**: la pagina non c'è → serve un frame libero. Se non ce n'è, si sceglie
  una **vittima** tra i frame con pin count `0` (l'**eviction**). Se la vittima
  è **sporca**, prima di riusarla si riscrive su disco (il **flush**); poi si
  carica la pagina richiesta nel frame.

Il **flush** è anche un'operazione a sé: riscrivere su disco una pagina sporca
quando serve (per esempio al momento dello spegnimento o di un checkpoint).

```
   fetch(page_id):
     1. la pagina è già nella page table?
          SÌ  -> HIT:  pinna e restituisci (nessun accesso al disco)
          NO  -> MISS:
                 2. serve un frame libero
                 3. se non ce n'è, EVICTION:
                      scegli una vittima con pin count = 0
                      se la vittima è sporca -> FLUSH su disco
                 4. carica la pagina dal disco nel frame
                 5. pinna e restituisci
```

## La politica di rimpiazzo: LRU e Clock

Quando serve un frame e sono tutti occupati, quale pagina si butta fuori? La
scelta è la **politica di rimpiazzo**, e due sono le più comuni.

**LRU (Least Recently Used)**: si butta la pagina usata meno di recente. È una
buona approssimazione di ciò che serve, ma richiede di tenere traccia, per ogni
accesso, di quando è avvenuto: un libro contabile che si aggiorna a ogni hit.

**Clock**: i frame sono disposti in un cerchio, ognuno con un **reference bit**
che il sistema accende quando la pagina viene usata. Una "lancetta" avanza: se
il bit della pagina puntata è `1`, lo azzera e passa oltre; se è `0`, quella
pagina è la vittima. È un'approssimazione economica di LRU: non sa *quanto*
tempo fa una pagina è stata usata, solo se è stata usata di recente.

```
   posizione:  0        1        2        3     (poi ricomincia da 0)
             +--------+--------+--------+--------+
   frame:    | F2     | F0     | F5     | F1     |
   ref bit:  |  1     |  0     |  1     |  0     |
   pin:      |  0     |  0     |  2     |  0     |
             +--------+--------+--------+--------+
                ^
                lancetta (parte da sinistra): azzera i ref bit a 1 e si ferma
                sulla prima pagina con ref bit 0 e pin 0. Qui azzera F2 (r=1)
                e trova F0 pronta: F0 è la vittima. F5 ha pin 2, quindi è
                saltata anche se il suo ref bit è vecchio.
```

Il compromesso è il solito: LRU è più precisa ma paga un aggiornamento a ogni
accesso; Clock è più economica e in pratica va quasi altrettanto bene. I sistemi
reali scelgono l'una o l'altra (o varianti), e la scelta va documentata perché
cambia il comportamento sotto carico.

## Pagine sporche: il dirty flag e il flush

Quando si **modifica** una pagina nel pool, la copia su disco diventa vecchia.
Il **dirty flag** segnala proprio questo: "in memoria c'è una versione più
recente di quella su disco". La pagina viene riscritta su disco al momento
dell'eviction (se sporca), o con un flush esplicito.

Attenzione a non confondere il **flush** con la **durabilità**: riscrivere la
pagina attraverso il page manager la consegna al sistema operativo, ma per
essere davvero sicuri contro un crash serve un `fsync` (il tema è in
[`buffering-e-flush.md`](buffering-e-flush.md)). Il buffer pool decide *quando*
le pagine vanno scritte; la durabilità è una questione separata, che toccherà
il write-ahead log.

## Perché non lasciare la cache al sistema operativo (mmap)

Viene la tentazione di non costruire nulla: si mappa il file in memoria con
`mmap` e si lascia che il sistema operativo faccia da cache. È comodo, ed è
quel che fa qualche sistema reale (LMDB). Ma il sistema operativo **non sa
nulla di SQL né di transazioni**: vede solo letture e scritture di pagine.

Tre problemi lo rendono inadatto a un DBMS che vuole controllo:

- **Ordine e transazioni**: l'OS può scrivere le pagine sporche su disco
  nell'ordine che vuole, anche quello sbagliato, lasciando il file incoerente
  dopo un crash.
- **Eviction fuori controllo**: l'OS può togliere dalla memoria una pagina nel
  mezzo di un'operazione, o bloccare il thread su un page fault quando meno te
  lo aspetti.
- **Errori non gestibili**: un errore hardware su una pagina mappata arriva
  come un segnale (SIGBUS), non come un'eccezione che puoi catturare e
  correggere.

Costruire il proprio buffer pool costa, ma dà al database il controllo su
*cosa* sta in memoria, su *quando* si scrive, e su *come* si reagisce agli
errori. È la stessa ragione per cui il page manager non si affida ai comodi
del sistema operativo.

## Il buffer pool è l'unico che tocca il disco (sopra il page manager)

L'architettura a strati è netta: gli access method **chiedono pagine al buffer
pool**, e solo il buffer pool chiama il page manager per leggere o scrivere.
Sopra il page manager, nessun altro componente fa I/O direttamente.

```
   access method   (slotted page, heap file, indici)
          |  chiedono pagine
          v
     buffer pool   (pin/unpin, dirty flag, eviction)
          |  legge/scrive pagine intere
          v
    page manager   (pagine fisse su file)
          |  I/O
          v
        disco
```

Per questo, dopo l'arrivo del buffer pool, la slotted page non chiamerà più `read_page`
/`write_page`: riceverà una pagina dal pool e la modificherà in memoria. Il
meccanismo sotto resta identico; cambia *chi* chiede le pagine.

## Le insidie

**Buttare fuori una pagina pinnata.** È il peggior errore: corrompe il puntatore
di chi la stava usando. Si evincono solo le pagine con pin count `0`.

**Dimenticare di pinnare.** Se si usa una pagina senza pinnarla, il buffer pool
può riciclare il frame mentre la si legge.

**Dimenticare il dirty flag.** Se si modifica una pagina senza marcarla sporca,
all'eviction viene riscritta la versione vecchia e le modifiche spariscono.

**Pin count che non torna a zero.** Una pagina mai unpinnata resta per sempre in
memoria e non può essere rimpiazzata: la cache si riempie di pagine "bloccate".

**Credere che il disco sia aggiornato.** Finché una pagina sporca è nel pool, il
file su disco è vecchio. Chi legge il file per conto proprio vede dati stantii.

**Confondere il buffer pool col buffer di I/O.** Il buffer di I/O (e la cache
dell'OS) servono a fare meno chiamate di sistema; il buffer pool è una cache di
**pagine del database**. Stanno a livelli diversi (vedi
[`buffering-e-flush.md`](buffering-e-flush.md)).

**Scegliere la politica a caso.** LRU e Clock non sono equivalenti sotto carico:
la scelta va fatta consapevolmente e documentata.

## Dove va a parare: heap file e indici

Con il buffer pool, ogni access method smette di parlare col disco e parla con
la cache. Il **heap file** (modulo successivo) userà il buffer pool per leggere
e scrivere le pagine della tabella; gli **indici** faranno lo stesso per i nodi
del B+Tree. Più avanti, il write-ahead log si coordinerà con il flush del buffer
pool per garantire la durabilità: prima si scrive il log, poi — quando serve —
si scrivono le pagine.
