# Testare in Python con pytest e Hypothesis

Un database si costruisce per strati, e ogni strato va verificato prima di
fidarsene. La suite di test è ciò che permette di cambiare il codice senza
paura e di dire "funziona" con delle prove invece che con un'intuizione.
Questa pagina raccoglie le convenzioni e le trappole di `pytest` e
`Hypothesis` incontrate scrivendo il page manager.

## pytest scopre i test per convenzione, non per magia

`pytest` non esegue tutto: raccoglie solo i file che si chiamano `test_*.py`
(o `*_test.py`) e, dentro, solo le funzioni il cui nome **inizia con
`test_`**. Una funzione scritta come `allocate_page_writes_a_zero_filled_page`
non viene **né eseguita né segnalata**: sparisce silenziosamente. È una
trappola insidiosa, perché il test manca senza che nulla fallisca — anzi, il
numero di "passed" sembra normale. Quando un test "non fa niente",
il primo sospetto è sempre il nome.

Lo stesso vale per le fixture: un parametro del test viene risolto come
fixture solo se il nome **combacia esattamente** con una fixture definita.
Un refuso (`tmp` invece di `tmp_path`) non è un errore di tipo che il
type checker vede: è un problema a runtime, e solo se il test viene
raccolto.

## Le fixture: setup e teardown condivisi

Una **fixture** è una funzione che prepara ciò che serve al test e lo
pulisce alla fine. `pytest` inietta la fixture in ogni test che la dichiara
come parametro:

```python
@pytest.fixture
def pm(tmp_path: Path) -> Iterator[PageManager]:
    manager = PageManager(tmp_path / "db.bin")
    yield manager  # ...qui il test gira...
    manager.close()  # ...e qui si pulisce
```

La parola `yield` divide la fixture in due fasi: tutto ciò che sta prima
gira come **setup**, tutto ciò che sta dopo il `yield` gira come
**teardown**, anche se il test fallisce. È il modo idiomatico per
garantire che risorse come i file vengano chiuse.

`tmp_path` è la fixture più utile per i test che toccano il filesystem:
`pytest` crea una directory temporanea **nuova per ogni test** e la passa
come `pathlib.Path`. Ogni test parte così da un ambiente pulito, senza file
che si accumulano tra un test e l'altro.

## Fixture o costruzione manuale?

La fixture conviene quando il setup è sempre lo stesso e basta un oggetto
pronto all'uso. Non conviene quando il test ha bisogno di **preparare lo
stato prima** che l'oggetto esista, o di gestirne il ciclo di vita:

- pre-riempire un file con contenuto noto *prima* di aprirlo;
- creare un file corrotto o di dimensione anomala;
- chiudere e riaprire (test di persistenza);
- aspettarsi che il **costruttore fallisca**;
- avere più oggetti contemporaneamente.

In quei casi si costruisce a mano, con `try/finally` per la chiusura:

```python
def test_something(tmp_path: Path) -> None:
    path = tmp_path / "db.bin"
    path.write_bytes(...)  # preparo il file
    manager = PageManager(path)  # poi lo apro
    try:
        ...  # asserzioni
    finally:
        manager.close()  # pulizia garantita
```

Un errore da evitare: prendere una fixture come `pm` e poi **riassegnarla**
nel corpo del test. La fixture ha già creato e aperto un oggetto; sovrascriverne
la variabile lascia il primo handle aperto e rende il test difficile da
capire. O si usa la fixture, o si costruisce a mano.

## Hypothesis: testare invarianti, non esempi

Un test normale verifica un caso scelto a mano. **Hypothesis** ti fa scrivere
una **proprietà** che deve valere sempre, e genera da solo centinaia di
input per provare a smentirla; quando trova un controesempio, prova a
**ridurlo** al più piccolo caso che fallisce (*shrinking*).

```python
@given(st.binary(min_size=PAGE_SIZE, max_size=PAGE_SIZE))
def test_write_read_round_trip(data: bytes) -> None:
    ...
    assert manager.read_page(0) == data
```

Regole pratiche:

- La strategia (`st.binary`, `st.integers`, ...) descrive **quali input**
  generare.
- La proprietà deve essere vera per *ogni* input lecito, non solo per quelli
  che avevi in mente.
- Se il test è difficile da generare, spesso è il **design** a essere
  complicato, non il test.

## Le fixture e Hypothesis non vanno d'accordo

`Hypothesis` esegue lo stesso test molte volte con input diversi, ma una
fixture **function-scoped** (come `tmp_path`) non viene ricreata tra un
input e l'altro: tutti gli esempi condividono lo stesso file, e lo stato si
accumula. Hypothesis se ne accorge e ferma il test con un **health check**:

```
FailedHealthCheck: ... uses a function-scoped fixture 'tmp_path'.
```

La soluzione corretta **non** è sopprimere il controllo (nasconderebbe un
bug reale), ma creare la risorsa *dentro* il test, così che ogni esempio ne
abbia una nuova:

```python
@given(st.integers(min_value=1, max_value=50))
def test_num_pages_equals_number_of_allocations(count: int) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = PageManager(Path(tmp) / "db.bin")
        try:
            ...
        finally:
            manager.close()
```

## Gli health check si sopprimono solo con un motivo

Ogni tanto un health check è un **falso positivo**, e la soppressione è
legittima — ma va motivata. Esempio reale: generare una pagina intera con
`st.binary(min_size=PAGE_SIZE, max_size=PAGE_SIZE)` fa scattare
`large_base_example`, perché Hypothesis ritiene "enorme" qualunque input
minimo di 4096 byte. Ma 4096 è la dimensione di pagina **fissa per
progetto**: non è riducibile. Si sopprime esplicitamente:

```python
@given(st.binary(min_size=PAGE_SIZE, max_size=PAGE_SIZE))
@settings(suppress_health_check=[HealthCheck.large_base_example])
def test_write_read_round_trip(data: bytes) -> None: ...
```

La differenza tra i due casi è tutta qui: nel primo (fixture condivisa) il
controllo segnala un bug **vero**, e si corregge il test; nel secondo segnala
un vincolo **voluto**, e si sopprime con una spiegazione. Sopprimere per
zittire un problema reale è il modo più rapido per perderlo di vista.

## Perché vale la pena

Scrivere prima il test e **guardarlo fallire** non è rituale: è la prova che
il test misura davvero qualcosa. Un test che non viene raccolto, o che passa
per caso, dà una falsa sicurezza — e in un database, dove gli errori sono
offset sbagliati di un byte, la falsa sicurezza è il nemico numero uno.
