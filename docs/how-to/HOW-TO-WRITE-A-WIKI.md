# Come scrivere una wiki (per gli agenti che scrivono i concetti)

Questo file raccoglie le regole di stile e di formato per i documenti di
**concetto** in `docs/wiki/`. Ogni wiki insegna un concetto generale e
estraibile: non racconta la storia di questo progetto (quella sta in
`docs/journal/`, con le sue regole in `HOW-TO-WRITE-A-JOURNAL.md`), non
registra decisioni formali (quelle stanno in `docs/adr/`). Se una regola qui
dentro è ambigua, si torna a questo file come fonte di verità.

---

## Principio guida: la wiki è un capitolo di un libro di testo

Una wiki non è un insieme di appunti, né una FAQ, né una lista di comandi
commentati. È un **capitolo di un libro di testo**: ha un filo logico, si
legge dall'inizio alla fine, e ogni concetto viene introdotto quando serve e
spiegato la prima volta che compare.

Conseguenza pratica: il testo deve **scorrere**. Niente strutture spezzate in
tanti blocchi separati — niente "Part 0", niente box "Plainly", niente
evidenziazioni che interrompono il discorso. Le spiegazioni stanno *dentro*
la prosa, nel punto in cui servono.

## I titoli contengono l'argomento

Ogni titolo (sezione o sottosezione) deve dire, in poche parole, **di cosa
parla il paragrafo che apre**. Un titolo come "Part 1" o "Concetti" non dice
nulla. Uno come "Il reverse proxy: il portiere davanti ai tuoi servizi" dice
esattamente cosa troverai sotto.

## Il lettore deve poter capire e rispiegare

Lo scopo di una wiki è che chi la legge la capisca davvero — non che
l'abbia "scorsa". Questo significa:

- **Non dare per scontato nulla.** Se usi un termine tecnico (porta, VPS,
  dominio, immagine, variabile d'ambiente), spiegalo la prima volta che
  compare, anche quando sembra ovvio. Cosa è ovvio per chi scrive non lo è
  per chi legge.
- **Usa analogie concrete** (condominio e campanelli per le porte, portinaio
  per il reverse proxy), ma **integrate nel discorso**, non in box a parte.
- **Spiega il "perché"**, non solo il "come". "Si copia il lockfile prima del
  codice" senza spiegare il layer caching è una regola da memoria; con la
  spiegazione diventa comprensibile.

## È un documento estraibile

La wiki insegna un concetto **generale**, valido al di fuori di questo
progetto. Il contenuto deve reggersi da solo: chi non conosce il progetto
deve comunque imparare il concetto. Non si scrivono wiki "calate" su una sola
situazione. Le decisioni specifiche del progetto stanno negli ADR
(`docs/adr/`), la storia sta nei journal (`docs/journal/`), i concetti stanno
nelle wiki.

## Self-contained

Una wiki deve essere leggibile da sola, senza dover aprire altri file.
Quando rimanda altrove (un'altra wiki, un ADR), lo fa per *approfondire*,
non perché il contenuto manca. Regola pratica: se il riferimento è
necessario per capire, va scritto nel testo; se è facoltativo, va linkato.

## Niente auto-citazioni e niente rinvii goffi

Non riprendere tra virgolette una frase già scritta altrove nel testo ("come
detto sopra, 'tutto dietro localhost'"). Se un concetto va detto, si dice
nel punto giusto — una volta — nel modo naturale. I rinvii interni ("vedi la
sezione sul reverse proxy") sono ammessi solo come indicazioni di percorso,
mai come sostituti della spiegazione.

## Lingua

Le wiki si scrivono nella **lingua del progetto** (di solito l'italiano).
I file scritti in un'altra lingua prima di un eventuale cambio di regola non
vanno riscritti per principio, ma ogni nuova wiki e ogni riscrittura
sostanziosa sono nella lingua del progetto.

## La struttura tipica di una wiki di concetto

Una wiki di concetto ha di solito questa forma:

1. **Apertura** — il concetto in una frase, perché esiste, quando ti serve.
2. **Il concetto centrale** — spiegato dal generale al particolare, con
   analogie integrate nel discorso.
3. **I trade-off** — le alternative e quando scegliere l'una o l'altra.
4. **Le insidie** — gli errori comuni, specialmente quelli scoperti usando
   davvero il concetto.

La struttura non è un copia-incolla obbligatorio: è una forma tipica. Ciò
che non cambia mai sono il principio guida (testo scorrevole), i titoli
significativi e la didattica. **Non** si aggiungono esercizi con checkpoint
del progetto: quella è materia del journal, che racconta cosa abbiamo fatto.

## Lunghezza

La lunghezza giusta è quella che serve a spiegare. Una wiki corta che dà per
scontato i concetti è sbagliata quanto una wiki gonfiata di ripetizioni. Se
il contenuto richiede spazio, lo spazio va usato — ma ogni frase deve
aggiungere qualcosa.

## Le fonti vanno verificate

Quando una wiki si basa su una fonte esterna (una guida, un tutorial, un
post), i fatti tecnici vanno **verificati contro il codice reale del
progetto o la documentazione ufficiale**, e gli errori della fonte vanno
corretti, non copiati. La wiki non eredita le imprecisioni della fonte.

## Checklist prima di consegnare una wiki

- [ ] Si legge dall'inizio alla fine come un capitolo, senza blocchi spezzati
- [ ] I titoli dicono l'argomento del paragrafo
- [ ] Ogni termine tecnico è spiegato alla prima occorrenza
- [ ] Il lettore potrebbe rispiegare il concetto a qualcun altro dopo averla letta
- [ ] È estraibile: regge da sola fuori da questo progetto
- [ ] Non racconta la storia del progetto (quella va nel journal)
- [ ] I fatti tecnici sono verificati, non copiati da una fonte
- [ ] È nella lingua del progetto
- [ ] Non ci sono auto-citazioni o rinvii che sostituiscono le spiegazioni