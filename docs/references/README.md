# references/ — il distillato delle fonti

Questa cartella contiene l'**estratto delle fonti esterne** del progetto: i
due corsi salvati in locale, ridotti alle informazioni che servono a
beaver-db. È il posto dove andare a prendere i fatti senza rileggere le
fonti intere.

## Cos'è (e cosa NON è)

Questa cartella è un **quinto ruolo** accanto ai quattro di `docs/`:

- **NON è wiki**: i concetti in forma didattica e autoconsistente stanno in
  `docs/wiki/`. Da qui si *parte* per scrivere una wiki, non si linka qui.
- **NON è ADR**: le decisioni di questo progetto stanno in `docs/adr/`.
- **NON è journal**: la storia del lavoro sta in `docs/journal/`.

È **materia prima**: fatti, numeri, strutture e regole estratti dai corsi,
con l'indicazione di cosa il progetto adotta e cosa ignora.

## Le fonti

```
/home/mrbeaver/Documents/simonedangelo-blog/content/Courses & Playlists/Database System (by Andy Pavlo)
/home/mrbeaver/Documents/simonedangelo-blog/content/Courses & Playlists/Fundamentals of Database Engineering (by Hussein Nasser)
```

## Regole d'uso

1. **Scopo didattico prima di tutto.** beaver-db insegna i concetti, non
   corre per le performance: le approssimazioni sono ammesse e volute
   quando aiutano a capire. Non si costruisce "il miglior database del
   mondo".
2. **Fidelità**: i contenuti di questa cartella sono stati verificati
   contro le fonti il **2026-09-10**. Quando serve precisione (citazioni
   testuali, numeri esatti), si riapre la fonte.
3. **Proporzionalità**: un concetto si adotta solo se serve a beaver-db.
   "Presente nel corso" non è un motivo. Le esclusioni sono registrate in
   `fuori-scope.md`, così la domanda non torna ciclicamente.
4. **Cambiamenti grandi**: se un contenuto suggerisce modifiche ad
   architettura o roadmap, prima se ne discute con l'utente.

## Indice

| File | Fonte | Serve ai moduli |
|---|---|---|
| `pagine-e-storage.md` | Pavlo 03/04/05, Nasser 03 | page-manager, slotted-page, heap-file, buffer-pool |
| `indici-btree-e-hash.md` | Pavlo 07/08, Nasser 04 | btree-index, hash-index |
| `durabilita-e-wal.md` | Nasser 02 | wal (stretch) |
| `fuori-scope.md` | Pavlo 05, Nasser 06/08 | ciò che ignoriamo, con il perché |
