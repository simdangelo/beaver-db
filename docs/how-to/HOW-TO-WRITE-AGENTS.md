# Come scrivere un AGENTS.md (per chi imposta un progetto con un agente)

`AGENTS.md` è il file che un agente (LLM) legge all'inizio di ogni sessione di
lavoro sul progetto. È **il contratto tra l'autore del progetto e l'agente**:
dice all'agente cosa costruire, come, con quali regole — e soprattutto cosa
NON fare. Un buon AGENTS.md rende l'agente utile senza renderlo pericoloso.

Questo file spiega quali sezioni contiene un AGENTS.md ben scritto, cosa va
in ognuna, e gli errori comuni da evitare. È generalizzato: lo applichi a
qualsiasi progetto.

---

## Il principio guida: dire la cosa giusta, e solo quella

L'AGENTS.md deve rispondere a quattro domande che l'agente si porrà
continuamente:

1. **Cosa sto costruendo?** — l'obiettivo del progetto e il suo livello di
   ambizione.
2. **Come devo lavorare?** — il workflow, chi scrive cosa, l'ordine dei passi.
3. **Con cosa?** — le scelte tecniche (e quali NON sono negoziabili).
4. **Cosa non devo fare?** — i confini che proteggono l'autore.

Regola d'oro: **l'agente segue le istruzioni dell'utente sopra tutto**. Se
l'AGENTS.md dice una cosa e l'utente ne chiede un'altra nella sessione, vince
l'utente. L'AGENTS.md è la *base*, non una gabbia.

---

## Le sezioni tipiche (nell'ordine)

### 1. Project Overview

Una descrizione breve del progetto: cos'è, a chi serve, quanto deve essere
"serio" (un giocattolo? produzione? un progetto di apprendimento?). Questa
sezione calibra *tutte* le decisioni dell'agente: un progetto che dichiara
"production-ready" riceve risposte diverse da uno "demo".

**Cosa scrivere**: obiettivo, utente, livello di ambizione, e i vincoli
evidenti (monorepo, chi scrive il codice, ecc.).

### 2. Learning Workflow (se il progetto è di apprendimento)

Se il progetto serve per *imparare*, questa è la sezione più importante.
Definisce il loop che l'agente deve rispettare. Il pattern collaudato è:

```
1. WIKI       → l'agente scrive una guida sul CONCETTO
2. IMPLEMENTA → l'utente scrive il codice da solo
3. REVIEW     → l'agente recensisce e dice cosa sistemare e perché
4. ITERA      → l'utente corregge (1-2 giri)
5. SBLOCCO    → se l'utente è bloccato, l'agente scrive lui il codice
```

Cosa rende questo workflow funzionante (da scrivere esplicitamente):
- **Il codice lo scrive l'utente** — di norma. L'agente scrive la
  documentazione; il codice applicativo lo scrive l'agente solo come passo di
  sblocco esplicito.
- **Il wiki prima del codice** — non si implementa un concetto senza che la
  wiki lo abbia insegnato.
- **Ogni scelta non banale → ADR** — oltre alla wiki che insegna il concetto,
  l'ADR registra la decisione di questo progetto.

### 3. Learning Roadmap (ordine fisso dei moduli)

Se il progetto procede per moduli, l'ordine va fissato qui e **non va
riordinato senza proporlo esplicitamente**. L'agente deve sapere che il
roadmap di apprendimento è fisso (i moduli di prodotto stanno invece nel
ROADMAP di prodotto, vedi `HOW-TO-WRITE-A-ROADMAP.md`).

**Cosa scrivere**: l'elenco numerato dei moduli, in ordine, ognuno con una
frase sul contenuto. Le scelte future da esplorare (es. "auth decisa tramite
wiki+ADR quando arriverà il modulo") si annotano per non farle assumere in
anticipo.

### 4. Fixed Technology Choices

Le scelte tecniche **non negoziabili** a metà progetto. Questa sezione
protegge da due errori opposti: l'agente che propone di cambiare tutto, e
l'agente che assume una scelta che non è ancora stata fatta.

**Cosa scrivere**:
- Backend/frontend/strumenti con versioni e **comandi corretti vs sbagliati**
  (es. "sempre `uv run`, mai `pip`").
- Esplicitare cosa NON è in questa lista perché va deciso con wiki+ADR
  (es. "JWT vs sessions: non fissato qui, si decide nel modulo auth").

Il formato comandi-corretti/sbagliati è prezioso: l'agente impara i comandi
esatti del progetto e non inventa. Metti un blocco `# Correct` / `# Never`.

### 5. Architecture

Come è strutturato il codice: i layer, chi dipende da chi, le regole che non
si possono rompere. Non serve il dettaglio di ogni file — serve la **forma**
che l'agente deve rispettare quando tocca il codice.

**Cosa scrivere**: i layer top-down, le dipendenze permesse (e le proibite),
i pattern obbligatori (es. "i router sono sottili, la logica sta nei
servizi"), e il *perché* di una scelta architetturale (es. "niente repository
layer perché..."). Se il progetto ha una struttura di cartelle fissa,
descrivila.

### 6. Project Structure

La disposizione delle cartelle, con una riga di commento per ognuna. Se ci
sono regole tipo "il build context è la root del repo", vanno qui.

### 7. Migrations / DB / asset tecnici

Se il progetto ha convenzioni su migrazioni, database, o altri strumenti
trasversali (es. "mai modificare lo schema a mano, sempre Alembic"), si
scrivono qui con i comandi esatti.

### 8. Code Conventions

Le convenzioni di stile e naming che l'agente deve rispettare. **Le più
importanti da scrivere esplicitamente**:
- La convenzione di naming di funzioni/endpoint (CRUD, reports, ecc.).
- Le regole di tipo (type hints ovunque, niente `Any` senza motivazione).
- Le convenzioni di package/import (facade + `__all__`, import assoluti).
- Il pattern dei file che l'agente scrive di più (per chi scrive il frontend:
  quali componenti, come si nominano, dove vivono).

### 9. Testing

Come si testa il progetto: framework, livello (HTTP layer?), strategia (DB
reale di test?), comandi esatti. L'agente deve sapere **come verificare il
proprio lavoro**, non solo come scriverlo.

### 10. Boundaries

La sezione più importante per la sicurezza. Le regole che l'agente NON deve
mai rompere, scritte in modo assoluto:
- Mai cancellare file con `rm` (o equivalente).
- Mai eseguire `git` senza permesso esplicito.
- Mai scrivere codice di una parte del progetto senza autorizzazione.
- Mai committare segreti.

Ogni "mai" deve essere chiaro e non ambiguo. Questa sezione è il freno
dell'agente.

---

## Errori comuni da evitare

1. **AGENTS.md troppo vago** ("segui le best practice") — l'agente inventa
   le convenzioni. Ogni sezione deve dare regole concrete.
2. **AGENTS.md troppo rigido** — se vieti tutto, l'agente si blocca o lo
   ignora. Distingui *fisso* da *da decidere*.
3. **Comandi sbagliati o incompleti** — l'agente userà i comandi che leggi
   qui. Verificali davvero.
4. **Mancanza di Boundaries** — senza la sezione "cosa non fare", l'agente
   può essere eccessivamente proattivo (cancellare, committare, riscrivere).
5. **Regole in conflitto con l'utente** — se l'AGENTS.md dice una cosa e
   l'utente ne vuole un'altra, l'utente vince. Scrivilo esplicitamente per
   evitare che l'agente obbedisca al file invece che alla persona.

---

## Checklist prima di consegnare un AGENTS.md

- [ ] Dice cosa si sta costruendo e a quale livello di ambizione
- [ ] Definisce il workflow (chi scrive il codice, chi le wiki, l'ordine)
- [ ] Fissa il roadmap di apprendimento (se c'è) come non-riordinabile
- [ ] Elenca le scelte tecniche fisse con i comandi corretti/sbagliati
- [ ] Descrive l'architettura e le convenzioni di codice che l'agente deve rispettare
- [ ] Spiega come si testa (comandi esatti)
- [ ] Ha una sezione Boundaries chiara (mai cancellare, mai git senza permesso, mai segreti)
- [ ] Distingue ciò che è fisso da ciò che sarà deciso con wiki+ADR
- [ ] Tutti i comandi sono verificati contro il progetto reale