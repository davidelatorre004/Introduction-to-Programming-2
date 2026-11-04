# Plot Twist: regole per ogni modifica

Queste regole valgono per tutte le modifiche future al gioco in questa cartella.

## Architettura

- `story.py` contiene solo dati: stanze, oggetti, porte, flag, testi.
- `engine.py` contiene funzioni pure: ricevono uno stato e restituiscono `(nuovo_stato, outcome)`, senza mai modificare lo stato ricevuto.
- `main.py` contiene solo pygame: input, movimento, disegno, suoni.

## Lo stato di gioco

- `STATE_KEYS` non cambia (`room`, `inventory`, `flags`, `ending`).
- Le novità della storia diventano nuovi flag in `story.FLAGS`, validati da `engine._allowed_values` e da `engine.restore_state`.

## Testi e stile

- I testi del gioco sono in inglese.
- Commenti e docstring seguono lo stile del codice esistente.

## Compatibilità

- In modalità 1 giocatore il gioco deve comportarsi esattamente come prima.

## Test e modo di lavorare

- Ogni modifica ha i suoi test.
- Dopo ogni passo lancia `uv run pytest`. Se qualcosa fallisce, fermati e spiega perché prima di correggere.
- Alla fine di ogni passo riassumi in breve cosa è cambiato e perché.
