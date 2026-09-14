# Come scrivere un ROADMAP di prodotto (per chi pianifica le feature)

`docs/ROADMAP.md` è il piano delle **feature di prodotto** del progetto: la
fonte di verità per "cosa l'app deve fare dopo", ordinata per *dipendenze*,
non per modulo di apprendimento. È distinto dal **roadmap di apprendimento**
(che vive in `AGENTS.md` e fissa l'ordine dei moduli didattici): uno dice
"quali capacità di business costruiamo", l'altro dice "in quale ordine
impariamo".

Questo file spiega come scrivere un ROADMAP di prodotto che resti utile nel
tempo. È generalizzato: lo applichi a qualunque progetto.

---

## Il principio guida: una roadmap è un piano, non una lista di desideri

Un ROADMAP risponde a tre domande, in ordine:

1. **Cosa abbiamo già fatto** — le feature completate, con le decisioni di
   design prese (così non si ripetono e non si discutono di nuovo).
2. **Cosa faremo dopo** — le feature pianificate, ordinate per dipendenza.
3. **Cosa NON faremo (per ora)** — le feature rimandate, con il perché.

Il ROADMAP è **la fonte di verità**: quando una feature viene costruita, il
suo stato qui passa da `planned` → `in progress` → `done`. Se una decisione
di design fatta durante l'implementazione corregge quanto scritto, si
aggiorna il ROADMAP insieme alla spec e al piano (mai lasciarlo stantio).

---

## Le sezioni tipiche

### 1. Intestazione

- Il titolo (`# Product Roadmap — <Nome Progetto>`).
- Una nota che spiega la **distinzione** dal roadmap di apprendimento (che
  sta in `AGENTS.md` e non è questo documento).
- La **legenda degli stati**: `planned` → `in progress` → `done`.

### 2. Le feature, una per sezione, in ordine di dipendenza

Ogni feature ha una sezione numerata. Il numero segue l'**ordine di
dipendenza** (una feature che ne richiede un'altra viene dopo), non l'ordine
cronologico di implementazione.

Ogni sezione contiene:
- **Goal** — una frase su cosa fa per l'utente.
- **Design decisions (made)** — le decisioni di design già prese (bullet
  points concisi), perché una feature completata non deve far ripetere i suoi
  perché. Se una decisione è registrata in un ADR, si cita (`ADR 0005`).
- **Dependencies** — su cosa si appoggia (opzionale, se non ovvio).
- **Design questions open** — le domande rimandate esplicitamente (slot
  aperti per il futuro, senza forzarli ora).

La sezione di una feature `done` non deve essere cancellata: resta come
memoria delle decisioni prese. Una feature nuova si *aggiunge* in fondo o al
posto giusto nell'ordine, mai riscrivendo la storia delle completate.

### 3. Deferred (esplicitamente fuori scope)

Una tabella delle feature rimandate, con tre colonne:
| Feature | Perché rimandata | Quando potrebbe tornare |

Questa tabella è importante quanto le feature pianificate: mette nero su
bianco cosa NON costruiamo e perché, così la domanda non torna ciclicamente.
Quando una feature rientra, si sposta da qui alla sua sezione numerata.

### 4. Ordering rationale

Un breve paragrafo che spiega *perché* l'ordine è quello: "X è
auto-contenuta, Y è la fondazione di Z, quindi prima X poi Y". Questa sezione
permette a chi legge di capire se una feature nuova va messa prima o dopo, e
all'autore di difendere l'ordine senza rispiegarlo ogni volta.

---

## Come mantenere il ROADMAP nel tempo

- **Quando una feature parte**: stato → `in progress`.
- **Quando è finita**: stato → `done`, le decisioni di design restano nella
  sezione (non si cancellano).
- **Quando una feature costruita rivela una correzione**: si aggiorna la
  sezione insieme alla spec e al piano — il ROADMAP non deve driftare dalla
  realtà.
- **Quando si vuole aggiungere una feature**: si cerca il posto giusto
  nell'ordine di dipendenza (non in coda a caso), e si valuta se va anche
  nella tabella Deferred invece che pianificata.
- **Il ROADMAP non è il luogo dei dettagli tecnici**: i dettagli stanno
  nelle spec/plan; qui basta il goal e le decisioni. Se una sezione cresce
  troppo, è il segnale che il dettaglio va spostato altrove.

---

## Errori comuni da evitare

1. **Confondere roadmap di prodotto e di apprendimento** — sono due piani
   diversi con due vite diverse. Il primo in `docs/ROADMAP.md`, il secondo in
   `AGENTS.md`. Mescolarli confonde sia chi impara sia chi costruisce.
2. **Cancellare le feature completate** — perdono le decisioni di design e i
   perché; poi le stesse discussioni si ripetono. Restano, con stato `done`.
3. **Ordinare per entusiasmo invece che per dipendenza** — l'ordine deve
   riflettere cosa serve prima, non cosa è più bello.
4. **Dimenticare la tabella Deferred** — senza il "perché no", le feature
   rimandate tornano a bussare ogni settimana.
5. **Trattarlo come un documento statico** — il ROADMAP vive con il
   progetto: si aggiorna a ogni feature costruita e a ogni correzione emersa
   implementando.

---

## Checklist prima di consegnare un ROADMAP

- [ ] L'intestazione distingue chiaramente prodotto da apprendimento
- [ ] La legenda degli stati è presente (`planned` → `in progress` → `done`)
- [ ] Le feature sono numerate e ordinate per dipendenza, non per desiderio
- [ ] Ogni feature ha Goal + Design decisions; le ADR sono citate dove servono
- [ ] Le feature completate restano (stato `done`) con le loro decisioni
- [ ] Le domande aperte sono esplicite, non implicite
- [ ] La tabella Deferred elenca cosa non si fa e perché
- [ ] L'Ordering rationale spiega perché l'ordine è quello
- [ ] È in sync con spec/plan delle feature costruite (nessun drift)