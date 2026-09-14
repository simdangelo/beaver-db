# Come scrivere un journal (per gli agenti che documentano il lavoro)

Questo file raccoglie le regole per i **journal** in `docs/journal/`. Un
journal è il *diario del progetto*: racconta, modulo per modulo, che cosa
abbiamo fatto, perché, e cosa abbiamo scoperto mentre lo facevamo. È il
documento che chi impara (l'autore del progetto) legge per capire in concreto
lo step-by-step. Non insegna concetti generali (quelli stanno in
`docs/wiki/`, con le sue regole in `HOW-TO-WRITE-A-WIKI.md`) e non registra
decisioni formali (quelle stanno in `docs/adr/`). Se una regola qui dentro è
ambigua, si torna a questo file come fonte di verità.

---

## Principio guida: il journal è un diario di bordo, non un manuale

Un journal non spiega "come funziona X in generale" — racconta "che cosa
abbiamo fatto noi, in questo modulo". Se il lettore deve capire un concetto,
gli si indica la wiki corrispondente; il journal invece risponde a domande
concrete:

- Che cosa abbiamo costruito e perché?
- Quali file abbiamo toccato e che cosa è cambiato in ognuno?
- Quali problemi abbiamo incontrato mentre lo facevamo, e come li abbiamo
  risolti?
- Cosa abbiamo verificato (test, comandi, risultati) e che cosa è rimasto
  aperto?

## Un journal è cronologico e per modulo

La cartella `docs/journal/` raccoglie un file per **modulo del roadmap** (o
per fetta di lavoro significativa), con un numero che ne fissa l'ordine
(`04-nome-modulo.md`, `09-nome-modulo.md`). Il numero segue la progressione
del lavoro: leggere i journal in ordine è rileggere la storia del progetto.

## La struttura tipica di un journal

Un journal di modulo ha di solito questa forma:

1. **Apertura** — che modulo è, che obiettivo aveva, dove si colloca nella
   storia (i moduli precedenti che gli servono).
2. **Le decisioni prese** — le scelte fatte durante il modulo, con rimando
   all'ADR che le registra formalmente (es. "perché cookie session, vedi
   ADR 0005").
3. **Le modifiche al codice** — i file toccati, una breve descrizione del
   perché, e gli aspetti non ovvi (es. un nome di campo, una normalizzazione,
   una trappola evitata).
4. **Le insidie incontrate** — gli errori e le sorprese scoperte
   implementando davvero, e come sono stati risolti.
5. **Le verifiche fatte** — test eseguiti, comandi di controllo, risultati
   attesi e ottenuti.
6. **Cosa è rimasto aperto** — le decisioni rimandate, i "farlo dopo"
   espliciti.

La struttura non è un copia-incolla obbligatorio: è una forma tipica. Il
contenuto minimo che non manca mai: *cosa abbiamo fatto*, *perché*, *quali
file*, *quali problemi*, *quali verifiche*.

## Il journal parla del progetto

Il journal è l'unico posto dove i riferimenti al progetto sono non solo
ammessi ma **obbligatori**: nomi di file, funzioni, decisioni, errori —
tutto ciò che è specifico del progetto. La lingua è quella del progetto (di
solito l'italiano, se il progetto è in italiano). Se una sezione di un
vecchio journal è in un'altra lingua (scritta prima del cambio di regola),
non va riscritta per principio: si corregge solo se la si tocca
sostanzialmente.

## Il journal non insegna concetti

Regola importante: se mentre racconti il lavoro ti accorgi di stare
spiegando un concetto generale ("ecco cos'è un reverse proxy..."), quello
non è posto per farlo. Il concetto va in una wiki (`docs/wiki/`) e nel
journal lo richiami con un riferimento (`vedi wiki/come-funziona-x.md`).
Il journal racconta l'applicazione, non la teoria. Un'eccezione: una
**insidia** scoperta lavorando è materiale da journal, e può *meritare* una
wiki dedicata se insegna qualcosa di generale — in quel caso si fanno
entrambe: la wiki insegna, il journal racconta quando l'abbiamo incontrata.

## Il journal si collega a wiki e ADR

Il journal non vive isolato: rimanda ai concetti (`docs/wiki/...`) e alle
decisioni (`docs/adr/...`). Il percorso dei riferimenti è relativo al file
(es. dal journal `docs/journal/09-nome-modulo.md`, la wiki è
`../wiki/nome-concetto.md`). Questi rimandi sono *punti di partenza*, non
sostituti della spiegazione: chi legge il journal deve capire la storia
anche senza aprirli, e usa i link per approfondire.

## Niente auto-citazioni

Come per le wiki: non riprendere tra virgolette frasi già scritte altrove.
Se un fatto va detto, si dice nel punto giusto — una volta.

## Lunghezza

Il journal deve essere **abbastanza dettagliato da permettere di capire e
rispiegare il lavoro fatto**, ma non ripetitivo. Un elenco secco di file
senza "perché" è inutile quanto una storia senza i file toccati. Il criterio:
un lettore che ha seguito il modulo deve ritrovare tutto ciò che è successo,
senza dover rileggere i commit.

## Le fonti vanno verificate

Le affermazioni del journal (cosa fa un file, perché un errore è successo)
vanno **verificate contro il codice reale** e la cronologia del lavoro. Il
journal non racconta una versione idealizzata: documenta ciò che è davvero
accaduto, errori compresi.

## Checklist prima di consegnare un journal

- [ ] Racconta cosa abbiamo fatto in questo modulo, non come funziona il mondo
- [ ] I titoli dicono l'argomento del paragrafo
- [ ] Elenca i file toccati con il *perché*, non solo i nomi
- [ ] Documenta le insidie incontrate e come le abbiamo risolte
- [ ] Documenta le verifiche fatte (test, comandi, risultati)
- [ ] I concetti generali rimandano a `docs/wiki/`, le decisioni a `docs/adr/`
- [ ] Un lettore che ha seguito il modulo può rispiegare il lavoro dopo averlo letto
- [ ] I fatti sono verificati contro il codice e la cronologia reale
- [ ] È nella lingua del progetto
- [ ] Non ci sono auto-citazioni o rinvii che sostituiscono le spiegazioni