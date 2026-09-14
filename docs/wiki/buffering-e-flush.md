# Buffering e flush: dove finiscono davvero i byte quando scrivi

Un programma che scrive su un file sembra compiere un gesto immediato: chiami
`write`, i byte vanno nel file. In realtà tra il tuo processo e il supporto
fisico c'è una catena di passaggi, e in mezzo ci sono zone di memoria
temporanea chiamate **buffer**. Capire questa catena spiega tre cose che
altrimenti sembrano magie o bug: perché un file può contenere dati che non
"vedi" subito, perché i database parlano continuamente di `flush` e `fsync`,
e perché due modi diversi di chiedere "quanto è grande questo file?" possono
dare risposte diverse.

## Cos'è un buffer: una sala d'attesa per i byte

Un **buffer** è una zona di memoria che raccoglie dati in transito, per
spostarli in blocchi più grandi invece che uno alla volta. L'immagine è quella
della cassa del supermercato: non paghi ogni prodotto appena lo prendi dallo
scaffale, metti tutto nel carrello e passi alla cassa una volta. Il carrello
è il buffer; il motivo per cui esiste è che "andare alla cassa" — cioè
attraversare il confine tra il tuo programma e il disco — costa.

Quel confine si attraversa con una **chiamata di sistema** (*system call*):
un'operazione con cui il programma chiede al sistema operativo di fare
qualcosa, per esempio scrivere su un file. Ogni chiamata di sistema ha un
costo fisso, e farne una per ogni singolo byte sarebbe lentissimo. Il buffer
raccoglie i byte e ne fa una sola, grande. La stessa idea vale in lettura: si
porta in memoria un blocco intero in anticipo, perché probabilmente servirà
tutto.

Nel nostro progetto i byte non si scrivono uno alla volta, ma **intere
pagine da 4096 byte**: anche questo è buffering, però fatto più in alto, dalla
logica del database.

## I tre livelli tra write() e il disco

Quando scrivi, i byte attraversano tipicamente tre livelli, e a ogni livello
possono fermarsi in una zona di memoria diversa:

1. **Il buffer del processo.** La `write` di Python non scrive davvero sul
   disco: deposita i byte in una zona di memoria del tuo processo, il buffer
   del *file object*. Qui i byte sono nella RAM del tuo programma, invisibili
   a chiunque altro.
2. **La page cache del sistema operativo.** La chiamata di sistema che porta
   i byte fuori dal processo li affida al kernel, che li tiene in una zona di
   RAM chiamata *page cache* ("cache delle pagine"). Da questo momento il file
   è cresciuto per il sistema operativo, ma i byte potrebbero non essere ancora
   sul supporto fisico.
3. **Il supporto fisico.** Prima o poi il kernel scrive davvero i byte sul
   disco o sull'SSD, che a loro volta hanno piccole cache interne.

Tre gesti spostano i dati da un livello al successivo:

- **`flush()`** spinge i byte dal buffer del processo al sistema operativo
  (livello 1 → 2). Anche `close()` fa un flush prima di chiudere.
- **`fsync()`** (in Python `os.fsync`) chiede al sistema operativo di scrivere
  davvero i dati sul supporto fisico e di aspettare che sia fatto (livello
  2 → 3). È il gesto che dà la vera **durabilità**, ed è costoso.
- **`close()`** chiude il file dopo aver fatto flush: l'ultimo saluto pulito.

Attenzione a non confondere i primi due: `flush` e `fsync` non sono la stessa
cosa. `flush` consegna i byte al sistema operativo; `fsync` li rende
resistenti a un crash della macchina. Un database che dichiara "transazione
completata" dopo un `flush` ma senza `fsync` ha mentito, perché
un'interruzione di corrente può ancora perdere quei byte.

## Cosa significa "il file esiste" a ogni livello

La frase "i dati sono sul file" ha tre significati diversi, uno per livello:

- ai byte nel **buffer del processo** non accede nessun altro, nemmeno un
  altro programma che apre lo stesso file;
- ai byte nella **page cache** accede chiunque legga il file, perché il kernel
  è la fonte di verità condivisa;
- i byte **sul supporto** sopravvivono a crash e spegnimenti.

Da qui due conseguenze. Se il processo muore, perdi i byte ancora nel *suo*
buffer, ma non quelli già flushati — la page cache appartiene al kernel, non
al processo. Se si spegne la macchina, perdi i byte nella page cache che non
sono stati fsyncati.

## Perché due modi di misurare la dimensione possono discordare

Torniamo alla domanda che ha generato questa pagina: quanto è grande il file?
Esistono due strade, e la differenza sta proprio nei livelli qui sopra.

La prima è **chiedere al filesystem**, con `Path.stat().st_size`. Questa
lettura consulta i **metadati** del file, che il kernel aggiorna quando riceve
i byte, cioè quando il processo ha fatto flush. Vede quindi tutto ciò che è
arrivato almeno al livello 2, ma non i byte ancora nel buffer del processo.

La seconda è **chiedere all'handle aperto**, spostandosi alla fine e leggendo
la posizione (`seek` fino alla fine, poi `tell`). Questa riflette la posizione
*logica* del file object, che include anche i byte ancora nel suo buffer; per
giunta, spostarsi fa scattare il flush. È la dimensione che il processo
"crede" di avere.

Finché non fai `flush`, le due risposte possono discordare di un blocco
intero. È il motivo per cui, nel page manager, scrivere una pagina con un
metodo e poi leggere la dimensione con l'altro può restituire un numero
vecchio — e portare a riallocare una pagina già esistente.

## Il buffer del file non è il buffer pool del database

Qui serve una distinzione che salva da una confusione comune, perché in
questo progetto la parola "buffer" tornerà con un significato diverso.

Il **buffer di I/O** di cui parla questa pagina è un dettaglio *meccanico*:
serve a fare meno chiamate di sistema e a spostare i byte in blocchi. Vive
nello strato più basso, quello dei file.

Il **buffer pool** (il modulo 3) è una cosa di livello più alto: una *cache*
in RAM delle **pagine** del database, che esiste per evitare di rileggere la
stessa pagina dal disco ogni volta. Il suo scopo non è "spedire byte al
file", ma "tenere in memoria le pagine che servono di frequente". Entrambi
sono "memoria che contiene dati temporaneamente", da cui il nome simile, ma
risolvono problemi diversi e stanno a livelli diversi: il buffer pool sta
*sopra* il page manager, il buffer di I/O sta *sotto*.

Confonderli porta a un errore mentale: credere che avere un buffer pool renda
automaticamente sicure le scritture. Non è così. Il buffer pool decide quali
pagine restano in RAM; la sicurezza delle scritture dipende da flush e fsync.

## Il trade-off: quanto bufferizzare

Bufferizzare di più significa meno chiamate di sistema e quindi più velocità,
ma anche più dati "in volo" e visibilità ritardata: un altro processo che
legge il file non vede i tuoi byte finché non fai flush. Al contrario, flush
frequenti danno visibilità immediata ma costano; fsync frequenti danno
durabilità immediata e costano molto di più.

I database seri non si affidano al buffering per la correttezza: gestiscono
loro *quando* le pagine vanno scritte (il buffer pool) e aggiungono un log
per la durabilità (il WAL, modulo 11). È il senso della regola del progetto
secondo cui, sopra il page manager, solo il buffer pool tocca il disco.

Per un database didattico la regola pratica è più semplice: va benissimo
lasciare che il buffering faccia il suo lavoro, **purché si sappia quando si
fa flush**. Un `flush()` dopo ogni scrittura di pagina è lento per gli
standard reali, ma perfettamente adeguato qui, ed è una scelta che si vede e
si capisce.

## Le insidie

**Credere che `write` significhi "salvato".** I byte vanno nel buffer del
processo, non sul disco: senza `flush` (o `close`), chi legge da fuori non li
vede.

**Misurare la dimensione prima del flush.** `stat().st_size` non vede i byte
ancora nel buffer del processo: dopo una scrittura senza flush, la dimensione
può indicare un file più corto di quello che hai appena scritto.

**Confondere `flush` e `fsync`.** `flush` consegna al sistema operativo,
`fsync` scrive sul supporto. Il primo non basta per la durabilità.

**Dimenticare `close()`.** Un programma che termina senza chiudere può perdere
l'ultimo blocco bufferizzato. La chiusura esplicita è la fine pulita.

**Usare il numero magico per la fine del file.** Per spostarsi alla fine si
usa la costante nominata (`SEEK_END`), non un `2` che nessuno ricorda.
