# Beaver DB

An educational relational DBMS built from scratch in Python.

Beaver DB exists for one reason: to understand how a database management
system works **from the inside** — how records actually live on disk, why
buffer pools exist, how a B+Tree stays balanced under splits, and what
happens between a `SELECT` and the bytes it touches. It is a learning
project, built the hard way: every data structure a real DBMS uses is
implemented by hand, with no shortcuts.

> **Status: work in progress.** The storage layer is being built first.
> The feature plan lives in [`docs/ROADMAP.md`](docs/ROADMAP.md).

## What Beaver DB is (and is not)

| It is | It is not |
|---|---|
| A real storage engine: fixed-size pages, slotted pages, heap files — hand-packed bytes | A CSV/JSON wrapper around lists of rows (the very thing this project refuses to be) |
| A buffer pool with pinning, dirty flags and eviction | A performance-oriented system: throughput is explicitly not a goal |
| A B+Tree index living on the same paged storage | A concurrent database: single-node, single-process, single-threaded by design |
| A small hand-written SQL parser feeding a Volcano-style executor | A production DBMS: no cost-based optimizer, no networking, no MVCC |

## Design principles

- **Bytes all the way down.** Persistence is never delegated to a library:
  no `pickle`, no `sqlite3` under the hood, no ORM. Pages are packed with
  `struct` into `bytearray`s and written with plain file I/O.
- **Depth over breadth.** A few components (storage, buffer pool, index)
  implemented honestly beat every box of the classic DBMS architecture
  diagram implemented badly.
- **Correctness is testable.** Property-based tests (Hypothesis) check the
  invariants that matter: a page round-trips bit-for-bit, the buffer pool
  never exceeds capacity, the tree always finds what was inserted.

## Architecture

```
        REPL / Python API
               │
        SQL parser → AST
               │
  Execution engine (Volcano iterators)
               │
  Access methods (heap file · B+Tree)
               │
  Buffer pool (pin/unpin, LRU, dirty flush)
               │
  Page manager ── 4 KiB fixed pages on disk
```

Each layer talks only to the layer directly below it, and the page is the
only unit of disk I/O.

## Roadmap

The order of work — persistence first, SQL last:

1. Durable tuple storage behind a Python API
2. Typed tables with a persistent catalog
3. Minimal SQL: `INSERT`, `SELECT` (full scan)
4. `WHERE` predicates
5. `UPDATE` / `DELETE`
6. Interactive REPL
7. Secondary B+Tree indexes (`CREATE INDEX`, index scan)
8. Crash durability with a write-ahead log — *stretch goal*

Deliberately out of scope: joins, aggregations, subqueries, concurrency,
cost-based optimization, networking. Why each of them is out, and when it
could come back, is written down in the roadmap's deferred table.

## Development

Requires Python 3.14 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                       # create the venv and install dev dependencies
uv run pytest                 # run the test suite
uv run ruff check .           # lint
uv run ruff check --fix .     # auto-fix lint issues
uv run ruff format .          # format
uv run basedpyright           # type check
```

## How this project is built

Beaver DB follows a wiki-first learning workflow: before a module is
implemented, its concepts are written up as a small textbook chapter; the
code is then written, reviewed and iterated. Every module leaves behind a
journal entry, and every non-trivial design decision is recorded as an ADR.

| Folder | What's inside |
|---|---|
| `docs/wiki/` | Concepts — how slotted pages, buffer pools, B+Trees work |
| `docs/journal/` | The story — what was built module by module, pitfalls included |
| `docs/adr/` | Decisions — why this design, alternatives considered |
| `docs/ROADMAP.md` | The product feature plan, ordered by dependencies |

## Credits and inspiration

- [CMU 15-445/645 Database Systems](https://15445.courses.cs.cmu.edu/) by
  Andy Pavlo, and its teaching DBMS [BusTub](https://github.com/cmu-db/bustub)
- *Database Internals* by Alex Petrov
- *Database Design and Implementation* and SimpleDB, by Edward Sciore
- [Let's Build a Simple Database](https://github.com/cstack/db_tutorial) by
  Connor Stack
