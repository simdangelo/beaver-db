# Manipolare i byte con `struct`: pack, unpack e i buffer in memoria

Al livello dello storage i dati sono **byte grezzi**, e un byte non porta con
sé il proprio significato: lo stesso valore può essere il numero 65 oppure la
lettera "A", e un gruppo di byte non "sa" di rappresentare un certo numero. A
dare un senso ai byte è sempre un **formato**: la descrizione di quali campi ci
sono, quanto sono larghi e in che ordine. Questa pagina spiega `struct`, un
modulo della libreria standard di Python (non serve installarlo) che scrive e
legge valori a posizioni precise di un buffer. Un esempio applicato completo,
con i byte disegnati dopo ogni operazione, è nella wiki del progetto:
[`../wiki/slotted-page.md`](../wiki/slotted-page.md).

## Il bit: il mattone fondamentale

Il **bit** è l'unità più piccola dell'informazione: può stare in due soli
stati, che scriviamo `0` e `1`. Fisicamente questi due stati corrispondono a
qualcosa come una tensione alta o bassa, o una carica presente o assente: il
modo concreto dipende dalla tecnologia, ma il principio è sempre quello. Tutto
il resto è costruito con i bit.

## Il byte: otto bit, 256 valori

Otto bit messi insieme formano un **byte**:

```
1 byte = 8 bit
```

Con otto bit si possono comporre `2^8 = 256` combinazioni diverse, che usiamo
come i numeri da 0 a 255. In binario, un byte si scrive come un gruppo di otto
cifre, dalla prima all'ultima:

```
00000000 = 0
00000001 = 1
00000010 = 2
...
11111111 = 255
```

Memoria e disco, in fondo, contengono sequenze di byte, cioè gruppi di 8 bit.
Ogni singolo byte può rappresentare un valore da 0 a 255, ma più byte possono
essere combinati per rappresentare numeri molto più grandi, testi, immagini,
programmi e altri tipi di dati.

## L'esadecimale: scrivere un byte con due cifre

### Perché un byte si scrive con due cifre esadecimali

Il sistema esadecimale usa **16 cifre**:

```text
0 1 2 3 4 5 6 7 8 9 A B C D E F
```

Le cifre da `0` a `9` hanno il loro valore abituale. Le lettere rappresentano i
valori da `10` a `15`:

```text
A = 10
B = 11
C = 12
D = 13
E = 14
F = 15
```

Con **4 bit** possiamo rappresentare 16 valori diversi, da `0` a `15`, perché:

```text
2⁴ = 16
```

Quindi **una cifra esadecimale corrisponde esattamente a 4 bit**.

Per esempio:

```text
Esadecimale    Binario
0              0000
1              0001
A              1010
F              1111
```

Un **byte** è formato da 8 bit. Possiamo dividerlo in due gruppi da 4 bit:

```text
1 byte = 8 bit

1010 0101
 ↑      ↑
 4 bit  4 bit
```

Ogni gruppo da 4 bit può essere rappresentato da una cifra esadecimale. Perciò:

```text
1010 = A
0101 = 5
```

E il byte diventa:

```text
10100101 = 0xA5
```

**Ecco perché un byte si scrive con esattamente due cifre esadecimali**, da `00` a `FF`.

Il prefisso `0x` serve a indicare che il numero è scritto in esadecimale. Non fa
parte del valore: è solo una convenzione di scrittura.

Per esempio:

```text
0x41 = 4 × 16 + 1 = 65
```

Quindi **`0x41` e `65` rappresentano lo stesso numero**, scritto in due sistemi
di numerazione diversi.

## Lo stesso byte, due significati possibili

Un byte non è né un numero né una lettera: **dipende da come lo si
interpreta**. Con una tabella di codifica chiamata **ASCII**, il valore `0x41`
si legge come la lettera `'A'`, `0x42` come `'B'`, `0x20` come uno spazio. Ma
lo stesso `0x41` può essere letto come il numero 65. È il *formato* a
stabilire quale delle due letture vale: senza formato, un byte è solo un
numero. La lettura dei byte di un file, con accanto la posizione di ogni byte e
la sua resa in ASCII, è l'oggetto del **dump esadecimale**, descritto in
[`../wiki/page-manager.md`](../wiki/page-manager.md).

## La memoria: caselle indirizzate a byte

Fisicamente la memoria è fatta di bit, ma il computer la **organizza e la
indirizza per byte**: ogni casella ha un **indirizzo** e contiene un byte.
Quando il processore legge o scrive, ragiona per indirizzi di byte, non di
singoli bit.

```
Indirizzo   Contenuto (8 bit)
1000        01001101
1001        01100001
1002        01110010
1003        01101001
```

Ogni indirizzo identifica un byte, non un bit. Questo non vuol dire che i bit
non esistano: vuol dire che **otto bit vengono raggruppati in una posizione di
memoria che chiamiamo byte**. In una frase: il bit è il mattone, il byte è il
gruppo di otto bit con cui la memoria è normalmente organizzata e indirizzata,
e si può pensare a una catena "memoria → byte → bit", ricordando che il byte
non è altro che otto bit insieme.

## Numeri più grandi di un byte e l'ordine dei byte

Un byte si ferma a 255. Per numeri più grandi si usano **più byte** insieme, e
il loro numero fissa l'intervallo dei valori rappresentabili: due byte (16 bit)
arrivano a 65.535, quattro byte (32 bit) a oltre quattro miliardi, otto byte
(64 bit) a numeri enormi. In generale, `n` byte sono `8 × n` bit e coprono
`2^(8n)` valori, da `0` a `2^(8n) − 1`.

Quando un numero occupa più di un byte bisogna stabilire **in che ordine**
scriverne le parti. Non tutte le parti pesano uguale: in un numero decimale
come 42, la cifra 4 pesa dieci volte la cifra 2, perché sono rispettivamente le
decine e le unità. Allo stesso modo un numero a due byte ha un **byte alto**,
che pesa di più (vale 256 volte l'altro), e un **byte basso**, che pesa di meno.
Prendiamo `4096`, che in esadecimale è `0x1000`. Dato che un byte corrisponde a
due cifre esadecimali, un numero scritto con quattro cifre (`0x1000`) è fatto
di due byte, e il taglio cade a metà, a coppie di cifre: `10` e `00`. Il primo
è il byte alto, il secondo il byte basso. In binario la divisione si vede
ancora meglio, perché anche i bit si separano in due gruppi da otto:

```
0x1000 = 00010000 00000000
         \______/ \______/
         alto     basso
         (0x10)   (0x00)
```

Non `0x1`, che è una sola cifra e quindi mezzo byte, né `0x100`, che di cifre ne
ha tre e quindi è un byte e mezzo: un byte deve essere un numero intero di due
cifre.

Esistono due convenzioni opposte per mettere in fila questi due byte:

- **little-endian**: prima il byte **basso**, poi l'alto;
- **big-endian**: prima il byte **alto**, poi il basso.

Per `4096`, little-endian scrive `00 10` e big-endian scrive `10 00`. È lo
stesso numero, scritto nei due ordini. La quasi totalità dell'hardware moderno
(x86, ARM) è little-endian, ma non è una legge: due macchine che non concordano
l'ordine leggerebbero gli stessi byte come numeri diversi. Per questo il formato
**deve** fissarlo, e lo si fissa prima di scrivere i byte. In questo progetto
l'ordine è little-endian, la stessa scelta già presa per il formato su disco
nell'[ADR 0001](../adr/0001-dimensione-file-e-flush.md), e la teniamo in tutte
le strutture.

Da qui nasce un errore tipico nella lettura di un **dump esadecimale**, che
mostra i byte nell'ordine fisico in cui stanno in memoria. Se si vedono i byte
`00 10` e li si legge da sinistra a destra "come sembra naturale", si ottiene
`0x0010`, cioè 16: sbagliato. Il formato dice little-endian, quindi il byte
basso viene per primo e l'ordine va invertito per leggere il valore: `0x1000`,
cioè 4096. Il dump non interpreta, mostra; a interpretare è il formato.

## Un buffer è una fila di byte: l'offset

Un **buffer** è una zona di memoria: una fila di byte come le caselle
dell'esempio sopra, ma contata a partire da 0 invece che da un indirizzo
qualunque. La posizione di un byte in questa fila si chiama **offset**: dire
"offset 5" significa "il sesto byte, contando da zero".

Il buffer non dice cosa contengono i byte: sono valori tra 0 e 255, senza
etichette. Per dare un senso a quei byte serve di nuovo un **formato**, che dica
quali campi ci sono, quanto sono larghi e in che ordine. È un po' come un modulo
cartaceo con caselle di dimensione fissa: la riga in alto ("nome", "data",
"importo") è il formato, le caselle sono i byte; senza quella riga, le caselle
sono carta anonima.

## Il formato di `struct`: quali campi, quanto larghi, in che ordine

`struct` descrive il layout con una **stringa di formato** fatta di caratteri.
Ogni carattere è un campo, e la sua lettera ne fissa tipo e larghezza:

| Codice | Tipo | Byte | Intervallo senza segno |
|---|---|---|---|
| `B` | intero senza segno | 1 | 0 .. 255 |
| `H` | intero senza segno | 2 | 0 .. 65.535 |
| `I` | intero senza segno | 4 | 0 .. 4.294.967.295 |
| `Q` | intero senza segno | 8 | 0 .. 18.446.744.073.709.551.615 |
| `b` `h` `i` `q` | come sopra ma **con segno** | 1/2/4/8 | metà positivi, metà negativi |
| `s` | byte grezzi (non un numero) | n | — |

Un intero "senza segno" usa tutti i suoi bit per il valore, quindi parte da 0;
un intero "con segno" riserva metà dei valori ai numeri negativi, per esempio un
`b` da un byte va da −128 a 127. I campi di una pagina (numero di slot, offset,
lunghezze) non sono mai negativi, quindi si usano i tipi senza segno.

La larghezza si sceglie la più piccola che contiene il valore massimo previsto.
Le larghezze disponibili sono 1, 2, 4 e 8 byte, perché sono quelle dei tipi
interi dell'hardware; non esiste un intero "da 3 byte". Nel nostro caso i campi
non superano 4096: un `B` da un byte arriverebbe solo a 255 e non basterebbe,
mentre un `H` da due byte arriva a 65.535 e basta, senza sprecare i due byte in
più che servirebbero con un `I`.

La stringa di formato porta anche un carattere che fissa l'ordine dei byte visto
poco sopra: `<` significa little-endian, `>` big-endian. Senza questo carattere,
`struct` userebbe l'ordine della macchina e potrebbe inserire byte di **padding**
(riempimento) tra i campi; è un comportamento comodo in memoria ma instabile su
disco, e va evitato nei formati salvati. Quindi `"<HH"` significa due interi
senza segno da due byte, little-endian, per un totale di quattro byte, mentre
`"<H"` sono due byte.

## Quanti byte occupa un formato: `calcsize`

`struct.calcsize("<HH")` restituisce **4**, la somma delle larghezze dei campi.
Serve a sapere quanto è grande un formato senza contare i byte a mano, ed è utile
per definire costanti come la dimensione dell'header di una pagina.

## `pack` e `unpack`: tradurre tra valori e byte

`struct.pack(stringa_di_formato, valori...)` **costruisce** un `bytes` a partire
dai valori, mentre `struct.unpack(stringa_di_formato, dati)` fa il contrario:
legge i byte e restituisce una **tupla**, cioè una sequenza ordinata e immutabile
di valori, scritta tra parentesi come `(0, 4096)`.

```python
import struct

struct.pack("<H", 4096)  # b'\x00\x10'      (2 byte)
struct.pack("<HH", 0, 4096)  # b'\x00\x00\x00\x10'  (4 byte)
struct.unpack("<HH", b"\x00\x00\x00\x10")  # (0, 4096)
struct.calcsize("<HH")  # 4
```

Nel primo esempio, `b'\x00\x10'` è il modo in cui Python scrive due byte: il
prefisso `b'...'` indica che sono byte, e `\x00` e `\x10` sono i due byte in
esadecimale.

## `pack_into` e `unpack_from`: scrivere e leggere dentro un buffer

`pack` crea un `bytes` nuovo, ma una pagina non è un `bytes` nuovo ogni volta: è
**un unico grande buffer** in cui i campi vivono a offset precisi. Per questo
esistono le varianti con `_into` e `_from`, che lavorano *dentro* un buffer
esistente senza crearne uno nuovo:

- `struct.pack_into(stringa_di_formato, buffer, offset, valori...)` scrive i byte
  dentro `buffer` a partire da `offset`, modificandolo in place;
- `struct.unpack_from(stringa_di_formato, buffer, offset)` legge i valori a
  partire da `offset`.

Il buffer deve essere una **`bytearray`**, cioè una sequenza di byte
**mutabile**, modificabile. Un `bytes`, invece, è **immutabile** e `pack_into`
su di esso fallisce; la differenza tra i due è spiegata in
[`file-binari-in-python.md`](file-binari-in-python.md).

```python
buf = bytearray(8)
struct.pack_into("<HH", buf, 0, 0, 4096)  # scrive i primi 4 byte (offset 0)
struct.pack_into("<HH", buf, 4, 30, 2)  # scrive i byte 4..7
# buf == b'\x00\x00\x00\x10\x1e\x00\x02\x00'
```

Leggere l'header di una pagina è esattamente un `unpack_from` all'offset 0:

```python
struct.unpack_from("<HH", buf, 0)  # (0, 4096)
```

## Quando `struct` non serve: i byte a lunghezza variabile

`struct` traduce **numeri** secondo un **formato fisso**: sai in anticipo che
`num_slots` è un intero da 2 byte e lo leggi con `"<H"`. Ma non tutti i dati
hanno un formato fisso. Il **payload** di un record è una sequenza di byte la
cui lunghezza si conosce solo *a runtime*: non è un numero, e non esiste una
stringa di formato scritta nel codice che lo descriva.

Per prendere N byte da un buffer si usa lo **slicing**, non `struct`:

```python
record = bytes(self._data[offset : offset + length])
```

Si potrebbe anche costruire il formato al volo
(`struct.unpack_from(f"<{length}s", data, offset)[0]`), ma è più contorto e non
aggiunge nulla: lo slice fa la stessa cosa in modo diretto.

Il `bytes(...)` finale avvolge la copia rendendola **immutabile**: uno slice di
una `bytearray` è già una copia (non una vista), ma è mutabile; `bytes(...)` la
rende coerente col fatto che un record letto non deve poter modificare la
pagina.

Regola pratica: **`struct` per i campi a formato fisso (i numeri), slicing per i
byte a lunghezza variabile (il payload).** Quando i record avranno colonne
tipate, `struct` servirà per decodificare i **campi dentro** il record, ma il
record come tale resterà una sequenza di byte.

## Un esempio applicato

I meccanismi visti — leggere e scrivere campi a offset con `pack_into` e
`unpack_from` — si applicano a una struttura reale, la **slotted page**, con cui
un database tiene record a lunghezza variabile in pagine di dimensione fissa.
L'esempio completo, con i disegni dei byte dopo ogni operazione (formattazione,
inserimento, cancellazione, compaction), è nella wiki del progetto:
[`../wiki/slotted-page.md`](../wiki/slotted-page.md).

## Le insidie

**Dimenticare il carattere dell'ordine dei byte.** Senza `<` o `>`, `struct` usa
l'ordine della macchina e può aggiungere padding: il formato non è più
portabile.

**Leggere i byte nell'ordine sbagliato.** Little-endian vuol dire "byte basso
per primo"; leggere un dump da sinistra a destra dà il numero sbagliato.

**Scrivere con `pack_into` su un `bytes`.** Il buffer deve essere mutabile,
quindi una `bytearray`; `bytes` è immutabile e l'operazione fallisce.

**Confondere `pack` con `pack_into`.** Il primo restituisce byte nuovi, il
secondo scrive dentro un buffer esistente a un offset: in una pagina serve quasi
sempre il secondo.

**Sbagliare l'offset.** Le posizioni sono in byte, non in parole; lo slot numero
`k` comincia a `HEADER_SIZE + k * SLOT_SIZE`, e queste due grandezze vanno usate
come costanti, mai come numeri scritti a mano.

**Dimenticare un valore di `unpack_from`.** Quando ne serve solo uno, si scrive
`_, data_start = struct.unpack_from(...)`, altrimenti i linter segnalano la
variabile inutilizzata.

## Dove approfondire

- Il concetto di pagina e record, con i disegni dei byte passo per passo: [`../wiki/slotted-page.md`](../wiki/slotted-page.md)
- Il dump esadecimale, cioè leggere i byte con offset e ASCII: [`../wiki/page-manager.md`](../wiki/page-manager.md)
- Le API dei file binari, con `bytes` e `bytearray`: [`file-binari-in-python.md`](file-binari-in-python.md)
- Dove finiscono i byte quando si scrive, tra buffer e `flush`: [`../wiki/buffering-e-flush.md`](../wiki/buffering-e-flush.md)
