# knowledge/ — conoscenza generale e trasversale

Questa cartella raccoglie la conoscenza **generale e riutilizzabile** emersa
lavorando al progetto: come si usano le API di Python, come si testa, e in
generale tutto ciò che non è specifico di beaver-db. È il sapere che
servirebbe in qualunque progetto Python, non solo in questo.

## Cos'è (e cosa NON è)

- **NON è wiki**: in `docs/wiki/` stanno i concetti del **dominio del
  progetto**, cioè i moduli del learning roadmap (page-manager,
  slotted-page, heap-file, ...).
- **NON è references**: in `docs/references/` sta il distillato delle
  **fonti esterne** (i corsi) — materiale che citiamo, non nostro.
- **NON è journal/adr**: la storia del progetto e le decisioni stanno lì.

Qui c'è il "mestiere": Python, testing, strumenti. Documenti che
resteranno utili anche se beaver-db cambiasse forma.

## Indice

| File | Cosa insegna |
|---|---|
| `file-binari-in-python.md` | API dei file binari: stream vs `Path`, `read`/`readinto`, `bytes`/`bytearray`, short I/O, categorie di errore |
| `struct-e-buffer.md` | `struct` (`pack`/`unpack`/`pack_into`/`unpack_from`), offset e disegni del buffer passo per passo |
| `testing-con-pytest-e-hypothesis.md` | pytest (nomi, fixture, `tmp_path`), quando costruire a mano, Hypothesis e gli health check |

## Riferimenti incrociati

I documenti di questa cartella possono rimandare alle wiki del progetto (per
il concetto applicato al dominio) e viceversa. I link sono relativi al file:
da qui la wiki del page-manager è `../wiki/page-manager.md`.
