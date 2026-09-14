# Pacchetto docs portabile — Istruzioni per l'agente

Questo pacchetto insegna a un agente (LLM) come costruire la **struttura
documentale** di un progetto software di apprendimento, e come scriverne ogni
pezzo. È stato distillato da un progetto reale che usa questa struttura da
inizio a fine; qui è **generalizzato**, senza riferimenti a quel progetto,
così puoi portarlo in qualunque progetto futuro.

Porta con te questo file (il master) **insieme** agli altri file della
cartella: il master spiega la struttura e il workflow, i file dedicati
spiegano come scrivere ogni documento. Se devi consegnare un solo file,
consegna il master e i quattro HOW-TO come allegati.

---

## Come si usa questo pacchetto

1. **L'agente legge questo file per primo.** Da qui impara la struttura della
   cartella `docs/`, il workflow di apprendimento, e quali file esistono e a
   che cosa servono.
2. **Per scrivere un documento, segue il suo HOW-TO dedicato.** Ogni tipo di
   documento ha regole precise (stile, contenuto, cosa NON deve contenere).
3. **L'agente applica le regole al progetto specifico in cui lavora.** I
   nomi di file, i nomi dei moduli, la lingua, la roadmap: tutto dipende dal
   progetto. Qui c'è *come* farlo, non *cosa* il progetto deve essere.

---

## La struttura `docs/` e il suo perché

Il progetto usa una cartella `docs/` con **quattro ruoli distinti**, tenuti
separati in cartelle separate. La separazione è la regola più importante:
ogni tipo di informazione ha il suo posto, e mischiarli degrada tutti e
quattro.

```
docs/
├── wiki/       # CONCETTI generali e riutilizzabili ("come funziona X")
├── journal/    # STORIA del progetto ("cosa abbiamo fatto noi, modulo per modulo")
├── adr/        # DECISIONI formali ("perché abbiamo scelto X")
└── superpowers/ # SPEC e PIANI di implementazione (artefatti di lavoro)
    ├── specs/  # design document di una feature prima di implementarla
    └── plans/  # piani di implementazione task-by-task
```

### I quattro ruoli (e cosa NON va in ognuno)

| Cartella | Risponde a | Contiene | NON contiene |
|---|---|---|---|
| `wiki/` | "Come funziona il concetto?" | Teoria generale, estraibile, valida fuori dal progetto | La storia del progetto, le nostre decisioni |
| `journal/` | "Cosa abbiamo fatto e perché?" | Il racconto cronologico del lavoro: file toccati, insidie, verifiche | La teoria (rimanda alla wiki), le decisioni formali (rimanda all'ADR) |
| `adr/` | "Perché abbiamo scelto X?" | Decisioni architetturali, near-immutabili, con template | Le spiegazioni didattiche, le storie |
| `superpowers/` | "Cosa stiamo costruendo ora?" | Spec (design approvato) e plan (task da eseguire) | Documentazione a regime |

**La regola d'oro**: se un'informazione ha già un posto, la si mette lì — e
negli altri documenti la si **rimanda** con un link relativo, senza ripeterla.
Un concetto va nella wiki una volta sola; il journal lo richiama.

### I nomi dei file

- **Wiki**: nome breve che descrive il concetto, senza numeri
  (`middleware-http.md`, `sessions-vs-jwt.md`).
- **Journal**: `NN-nome-del-modulo.md` con numero progressivo che fissa
  l'ordine (`04-recurring-transactions.md`). Leggere i journal in ordine è
  rileggere la storia.
- **ADR**: `NNNN-titolo.md` con numero progressivo (`0005-cookie-sessions.md`).
- **Spec/plan**: `YYYY-MM-DD-titolo.md` (data del giorno in cui nascono).

---

## Il workflow di apprendimento (il cuore del metodo)

Il progetto è costruito per imparare facendo. Ogni modulo segue un loop:

```
1. WIKI     → l'agente scrive una guida sul CONCETTO (teoria, trade-off, insidie)
2. IMPLEMENTA → l'utente scrive il codice da solo, applicando la wiki
3. REVIEW   → l'agente recensisce il codice e dice cosa sistemare e perché
4. ITERA    → l'utente corregge, si ripete 1-2 volte
5. SBLOCCO  → se l'utente è bloccato, l'agente scrive lui il codice (normale, non un fallimento)
```

Regole del workflow:
- **Il codice lo scrive l'utente**, di norma. L'agente scrive solo wiki e
  (in alcuni progetti) frontend. Il backend lo scrive l'agente solo come
  passo di sblocco esplicito.
- **La wiki viene prima del codice.** Non si implementa un concetto senza
  che la wiki lo abbia insegnato.
- **Ogni scelta architetturale non banale** diventa un ADR, oltre alla wiki.
  Wiki insegna il concetto; ADR registra la decisione di QUESTO progetto.

### ADR vs Wiki — la distinzione

- La **wiki** insegna il concetto generale (es. "sync vs async in Python").
- L'**ADR** registra la decisione specifica del progetto (es. "noi usiamo
  la connessione al database in modo sincrono, ADR 0002") con template:
  Context, Decision, Alternatives considered, Consequences.
- Un ADR è **near-immutabile**: se la decisione cambia, si scrive un ADR
  nuovo che la supera, non si edita il vecchio.

---

## Gli altri file che l'agente deve saper scrivere

Oltre a `docs/`, il progetto ha due file alla radice che definiscono come
lavora l'agente stesso. I loro HOW-TO sono nel pacchetto.

- **`AGENTS.md`** — le istruzioni permanenti che l'agente legge a ogni
  sessione: obiettivo del progetto, workflow, scelte tecniche fisse, comandi,
  architettura, convenzioni, confini (cosa NON fare). Come scriverlo:
  vedi `HOW-TO-WRITE-AGENTS.md`.
- **`docs/ROADMAP.md`** — il piano delle *feature di prodotto* (non dei moduli
  di apprendimento, quelli sono in AGENTS.md): la fonte di verità per "cosa
  l'app deve fare dopo", ordinato per dipendenze. Come scriverlo:
  vedi `HOW-TO-WRITE-A-ROADMAP.md`.

---

## Il confine wiki/journal — esempio pratico

Se stai scrivendo un journal e ti accorgi di stare spiegando un concetto
generale ("ecco cos'è un reverse proxy..."), **fermati**: quel concetto va
nella wiki. Nel journal scrivi solo "abbiamo messo un reverse proxy davanti
all'app; il concetto è in `../wiki/reverse-proxy.md`". Il journal racconta
l'applicazione; la wiki insegna la teoria. Un'eccezione: un'insidia scoperta
lavorando è materiale da journal, e può meritare una wiki dedicata se insegna
qualcosa di generale — in quel caso si fanno entrambe.

---

## Checklist per l'agente, a colpo d'occhio

- [ ] Ho capito qual è il posto giusto per questa informazione (wiki/journal/adr/spec)?
- [ ] Il concetto generale sta nella wiki, la storia nel journal, la decisione nell'ADR?
- [ ] Nei file uso link relativi invece di ripetere contenuti già scritti altrove?
- [ ] Seguo l'HOW-TO del tipo di documento che sto scrivendo?
- [ ] Il workflow rispetta l'ordine: wiki → implementazione → review → iterazione?
- [ ] Le scelte non banali hanno un ADR?

---

## Indice dei file del pacchetto

| File | Per quando serve |
|---|---|
| `README.md` | **Questo file** — la struttura e il workflow (leggere per primo) |
| `HOW-TO-WRITE-A-WIKI.md` | Prima di scrivere una wiki di concetto |
| `HOW-TO-WRITE-A-JOURNAL.md` | Prima di scrivere un journal di modulo |
| `HOW-TO-WRITE-AGENTS.md` | Prima di creare/aggiornare `AGENTS.md` |
| `HOW-TO-WRITE-A-ROADMAP.md` | Prima di creare/aggiornare `docs/ROADMAP.md` |