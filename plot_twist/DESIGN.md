# Plot Twist — documento di design

Gioco 2D top-down in stile 8-bit (alla *The Binding of Isaac*, senza combattimento), scritto in Python con pygame, per il brief [Plot Twist](https://nova-sbe-introduction-to-programming.github.io/intro-to-programming-2026/weeks/week-05/01-plot-twist-brd.html) della settimana 5.

Questo documento raccoglie le decisioni prese prima di scrivere codice:
- i dati della storia;
- le regole del motore;
- il salvataggio;
- l'interfaccia;
- come si verifica ogni requisito del brief;
- il piano di lavoro.

## 1. Il gioco

Una nave è alla deriva nell'oceano. Il protagonista si sveglia sul ponte, con una bacchetta magica a terra lì vicino. Nelle due stanze chiuse della nave aspettano un granchio e un angelo: a chi dare la bacchetta decide il finale.

| Scena | id | Cosa c'è |
|---|---|---|
| Ponte (esterno, inizio) | `deck` | La bacchetta a terra e le porte verso tutte le altre stanze |
| Cabina del capitano | `cabin` | Un enigma che, risolto con la bacchetta, fa comparire la chiave |
| Stiva | `hold` | Un enigma che, risolto con la bacchetta, rivela che il granchio dice la verità |
| Stanza del granchio | `crab_room` | Il granchio: dargli la bacchetta porta al finale *Tutti salvi* |
| Stanza dell'angelo | `angel_room` | L'angelo: dargli la bacchetta porta al finale *La nave esplode* |

Regole della storia:
- **Porte:** dal ponte si entra liberamente in cabina e in stiva. Le porte del granchio e dell'angelo richiedono la chiave.
- **Scelta:** aprire una delle due porte finali sigilla l'altra per sempre.
- **Oggetti:** non si consumano e non si duplicano.
- **Percorso minimo:** bacchetta → enigma della cabina → chiave → una porta finale → dare la bacchetta. La stiva è facoltativa: dà l'indizio per scegliere la porta giusta.
- **Enigmi:** per ora sono placeholder ("usa la bacchetta sull'oggetto X"). Il design vero arriva in M5.

Controlli:
- frecce o WASD per muoversi;
- **E** per interagire con ciò che è vicino;
- **I** per l'inventario;
- **Esc** per il menu.

Cosa chiede il brief per la prima versione, e dove si trova nel gioco:

| Il brief chiede | Nel gioco |
|---|---|
| Almeno 5 scene | 5 stanze |
| Almeno 2 oggetti collezionabili | Bacchetta e chiave |
| 2 finali raggiungibili | *Tutti salvi* e *La nave esplode* |
| Un finale che dipende da una scelta o da un oggetto precedente | Entrambi dipendono dalla porta scelta (`chosen_door`) e dalla bacchetta |
| Circa 10 minuti di gioco | Obiettivo di M5: con gli enigmi placeholder si finisce in 2–3 minuti |
| Testo e controlli semplici | Riquadri di testo e 4 tasti |
| Nessun servizio a pagamento né integrazione esterna | pygame e un file JSON locale |

## 2. Principi

1. **Lo stato contiene solo ciò che si salva:** stanza, inventario, flag, finale. Da questi quattro campi si ricava tutto il resto: cosa c'è a terra, quali porte sono aperte o sigillate, quali enigmi sono risolti. Così gli oggetti non possono duplicarsi, e il salvataggio scrive lo stato così com'è.
2. **Il motore (`engine.py`) non sa niente di pixel, tasti o file.** Riceve azioni come "raccogli X", "usa X su Y", "entra dalla porta Z". `main.py` decide cosa è vicino al giocatore; il motore decide se l'azione è permessa e cosa cambia. Tutte le regole si testano senza aprire una finestra.
3. **Le azioni non modificano lo stato che ricevono:** restituiscono uno stato nuovo e un esito. Un'azione rifiutata restituisce lo stato di prima, intatto.
4. **Ogni esito ha un testo:** il risultato visibile se l'azione è accettata, la spiegazione se è rifiutata.
5. **Si salva dopo ogni azione accettata,** e solo allora.

## 3. File

| File | Ruolo | Importa |
|---|---|---|
| `story.py` | I dati della storia: solo costanti | Niente |
| `engine.py` | Stato e regole | `story` (e `copy`) |
| `save.py` | Scrive e legge il salvataggio JSON | `json`, `os` |
| `main.py` | pygame: finestra, input, disegno, scene | `engine`, `save`, `story` |
| `test_engine.py` | Scenari A1–A6 e requisiti del brief | `engine`, `story`; da M2 anche `save` |
| `test_save.py` | Comportamento di `save.py` | `save`, `engine` |
| `conftest.py` | Preparazione comune dei test: sposta il salvataggio in una cartella temporanea | `save` |
| `test_main.py` | Layout, muri e porte, movimento, menu e salvataggio visti dall'interfaccia, senza aprire finestre | `main`, `engine`, `save`, `story`, `pygame` |

La cartella `plot_twist/` sta accanto a `splitit/` ed è organizzata allo stesso modo:
- un `pyproject.toml` per uv, con Python 3.12, pygame e pytest;
- un `.gitignore` che esclude il file di salvataggio.

## 4. `story.py`: i dati

Convenzioni:
- **Solo costanti:** niente funzioni, niente import.
- **Id:** ogni cosa, stanze comprese, ha un id stringa unico in tutto il gioco, in inglese (come `chosen_door`). I testi a schermo sono in italiano.
- **Dizionari piatti:** oggetti, porte e personaggi stanno in dizionari `id → dati` con un campo `room`, invece di essere elencati dentro le stanze. Così ogni informazione sta in un posto solo.
- **Testi:** stanno tutti qui, mai nel motore. Puoi riscrivere i dialoghi senza toccare né le regole né i test.

| Costante | Contenuto | Campi |
|---|---|---|
| `START_ROOM` | `"deck"` | — |
| `FLAGS` | Nome del flag → valore iniziale | `cabin_solved: False`, `crab_truthful: False`, `chosen_door: None` |
| `ROOMS` | Le 5 stanze | `name`, `description`, `outdoor` (il ponte è all'aperto: serve al disegno) |
| `ITEMS` | `wand`, `key` | `name`, `description`, `room`, `appears_if` (flag che lo fa comparire, o `None`), `pickup_text` |
| `DOORS` | 8 porte, una per verso | `room`, `to`, `requires` (oggetto o `None`), `choice_flag` (flag o `None`), `locked_text`, `sealed_text`, `open_text` (i tre testi solo per le porte chiuse a chiave) |
| `OBJECTS` | 2 enigmi e 2 personaggi | `kind` (`puzzle` o `character`), `name`, `room`, `look_text`, `done_text` (obbligatorio per gli enigmi), `reactions` (oggetto usato → reazione) |
| `ENDINGS` | `saved`, `explosion` | `title`, `text` (righe della schermata finale), `good` |
| `CLUES` | Flag → testo mostrato nell'inventario | `crab_truthful` → "Il granchio dice sempre la verità." |
| `MESSAGES` | Testi generici | Scena d'apertura, domanda di conferma per ricominciare, spiegazioni dei rifiuti ("non succede niente", "non è qui", …), testo di una porta aperta, etichette delle azioni del tasto E |

### Porte

| id | Collegamento | Apertura |
|---|---|---|
| `deck_to_cabin`, `deck_to_hold` | Ponte → cabina, stiva | Libere |
| `deck_to_crab`, `deck_to_angel` | Ponte → stanze finali | `requires: key`, `choice_flag: chosen_door` |
| `cabin_to_deck`, `hold_to_deck`, `crab_to_deck`, `angel_to_deck` | Ritorno al ponte | Libere |

Ogni collegamento ha due porte e ognuna sta in una sola stanza, quindi il motore non deve capire da che lato si sta passando.

### Oggetti collezionabili

- `wand`: sul ponte, con `appears_if: None`.
- `key`: in cabina, con `appears_if: cabin_solved`.

### Reazioni

Una reazione imposta un flag (`set_flag` con il nome e `value` con il valore) oppure chiude la partita (`ending` con l'id del finale). In entrambi i casi ha un `text`.

| Bersaglio | Oggetto usato | Effetto |
|---|---|---|
| `cabin_puzzle` | `wand` | `cabin_solved = True`: compare la chiave |
| `hold_puzzle` | `wand` | `crab_truthful = True`: l'indizio compare nell'inventario |
| `crab` | `wand` | Finale `saved` |
| `angel` | `wand` | Finale `explosion` |

Gli enigmi placeholder sono solo una reazione alla bacchetta. Con gli enigmi veri cambierà il modo di arrivare al flag, ma il resto del gioco legge solo il flag. Un enigma a più passi potrà aggiungere alla reazione una condizione su altri flag (`requires`).

### Regole derivate

Le calcola il motore; non si salvano mai.

- **Oggetto a terra:** un oggetto è a terra se sono vere tutte e tre le condizioni:
  - sta nella stanza corrente;
  - `appears_if` è `None` o vero;
  - non è nell'inventario.

  Per questo la chiave compare quando `cabin_solved` diventa vero, e sparisce appena raccolta.
- **Stato di una porta:** senza `requires` è sempre aperta. Con `choice_flag`:
  - è aperta se il flag contiene l'id di questa porta;
  - è **sigillata per sempre** se contiene l'id di un'altra;
  - è chiusa se il flag è `None`.

  Una porta chiusa "normale" è una porta il cui `choice_flag` non è condiviso con nessun'altra.
- **Enigma risolto:** il suo flag ha già il valore della reazione, quindi ripeterlo non fa niente.
- **Partita finita:** `ending` non è `None`.

### Layout

Si aggiunge in M3, e il motore non lo legge mai.
- `entry` per ogni stanza: il punto in cui si compare riprendendo una partita.
- `side` per ogni porta: N, S, E oppure O, a metà parete.
- `pos` per oggetti e personaggi.

Le coordinate sono in tile, non in pixel. Così spostare qualcosa nella stanza non rompe i test, e cambiare risoluzione non tocca la storia.

## 5. Lo stato

| Campo | Tipo | A inizio partita |
|---|---|---|
| `room` | id della stanza corrente | `"deck"` |
| `inventory` | Lista di id in ordine di raccolta, senza doppioni | Vuota |
| `flags` | Copia di `FLAGS` | Tutti al valore iniziale |
| `ending` | id del finale raggiunto, o `None` | `None` |

È esattamente ciò che il brief chiede di ricordare: scena corrente, oggetti raccolti, decisioni rilevanti, finale raggiunto.
- **Tipi:** solo tipi nativi JSON, niente set né tuple.
- **Posizione del giocatore:** non si salva. Quando si riprende una partita si riparte dall'ingresso della stanza.

## 6. `engine.py`: stato e regole

### Esito ed errori

Ogni funzione che agisce restituisce `(stato, esito)`. L'esito ha tre campi:
- `ok`: l'azione è stata accettata. `main.py` salva se e solo se è vero.
- `event`: un codice per i test e per l'interfaccia.
- `text`: mai vuoto. È il risultato visibile (PT02) oppure la spiegazione del rifiuto (PT04).

Ci sono due tipi di errore:
- **Il giocatore non può farlo:** si restituisce un esito con `ok` falso.
- **Il codice ha passato un id inesistente:** si solleva un'eccezione, perché è un bug.

### Sessione

- **`new_game()`:** crea lo stato iniziale, con `START_ROOM`, inventario vuoto, una **copia** di `FLAGS` e nessun finale. Non restituisce mai i dizionari di `story.py`: la prima modifica li cambierebbe per tutte le partite successive e per tutti i test.
- **`start_new_game(existing, confirmed)`:** l'unico modo di iniziare una partita. `existing` sono i progressi attuali o salvati.
  - Se `existing` non è `None` e `confirmed` è falso, rifiuta con `needs_confirmation`. Il testo è la domanda da mostrare, ed `existing` resta intatto.
  - Altrimenti restituisce `new_game()`, con la scena d'apertura come testo.
  - Il menu iniziale, "Ricomincia" nel menu Esc e la schermata finale passano tutti da qui, quindi la conferma non si può dimenticare.
- **`menu_options(existing)`:** "Nuova partita" c'è sempre; "Riprendi" solo se `existing` non è `None`.
- **`restore_state(data)`:** controlla un dizionario letto dal salvataggio e restituisce uno stato pulito, oppure `None`. Verifica che:
  - ci siano le 4 chiavi;
  - la stanza esista;
  - gli oggetti siano noti e senza doppioni;
  - i flag siano noti e con valori validi;
  - il finale esista.

  I flag mancanti li completa con il valore iniziale: servirà quando si aggiungeranno i flag degli enigmi veri.

### Letture

Queste funzioni non cambiano niente.
- **`is_over(state)`:** dice se è stato raggiunto un finale.
- **`has_item(state, item)`:** dice se un oggetto è nell'inventario.
- **`door_status(state, door)`:** restituisce `"open"`, `"locked"` o `"sealed"`, secondo le regole derivate.
- **`things_here(state)`:** restituisce tutto ciò che c'è ora nella stanza, con id, tipo e stato: oggetti a terra visibili, porte, enigmi (risolti o no), personaggi. `main.py` sa cosa disegnare e cosa è solido solo da qui.
- **`actions_for(state, target)`:** restituisce le azioni possibili premendo E vicino al bersaglio, ciascuna con un'etichetta:
  - "Raccogli" per un oggetto a terra;
  - "Entra" per una porta aperta;
  - "Esamina" oppure "Parla";
  - "Usa X" o "Dai X" per **ogni** oggetto dell'inventario, non solo per quello giusto, altrimenti il menu rivelerebbe la soluzione.

  Segna come `irreversible` le azioni che aprono una porta di scelta o fanno scattare un finale. Dopo il finale restituisce una lista vuota.
- **`clues(state)`:** restituisce i testi di `CLUES` dei flag veri, da mostrare nell'inventario.

### Azioni

Ogni azione controlla per prima cosa che la partita non sia finita.
- **`pick_up(state, item)`:** accettata se l'oggetto è a terra in questa stanza. Lo aggiunge in fondo all'inventario.
- **`enter(state, door)`:** accettata se la porta è in questa stanza ed è aperta. Cambia `room`, e il testo è il nome della nuova stanza. Se la porta è chiusa o sigillata, rifiuta con il testo della porta.
- **`use_item(state, item, target)`:** richiede che `item` sia nell'inventario e che `target` sia nella stanza.
  - Su una porta chiusa che richiede quell'oggetto: la apre scrivendo il proprio id nel suo `choice_flag` (per le porte finali, `chosen_door`). Da quel momento l'altra porta finale è sigillata.
  - Su un enigma o un personaggio: applica la reazione. Se non c'è una reazione il testo è "non succede niente"; se la reazione è già stata applicata è "già fatto".
  - L'oggetto resta sempre nell'inventario, anche dopo "dai".
- **`examine(state, target)`:** restituisce solo un testo. A seconda del bersaglio è:
  - la descrizione della stanza, se il bersaglio è la stanza corrente;
  - la descrizione di un oggetto;
  - la battuta di un personaggio;
  - "è chiusa a chiave";
  - il `done_text` di un enigma risolto.
- **`perform(state, action)`:** riceve un'azione come dato e chiama la funzione giusta. L'azione ha verbo, oggetto e bersaglio, cioè la stessa forma prodotta da `actions_for`. `main.py` fa passare tutte le azioni da qui, e i test scrivono gli scenari come liste di azioni.

### Codici di `event`

- **Azioni accettate:** `started`, `picked_up`, `entered`, `door_opened`, `flag_set`, `ending`, `info`.
- **Azioni rifiutate:** `needs_confirmation`, `game_over`, `not_here`, `already_have`, `no_item`, `locked`, `sealed`, `already_open`, `already_done`, `nothing_happens`.

Funzioni private di supporto:
- costruire un esito o un rifiuto;
- verificare se una cosa è nella stanza corrente;
- applicare una reazione a una copia dello stato.

## 7. `save.py`: il salvataggio

- **Funzioni:** `save_game(state, path)` e `load_game(path)`. Il percorso è facoltativo: se manca si usa `SAVE_PATH`, cioè `savegame.json` accanto al gioco. `SAVE_PATH` si legge a ogni chiamata, così `conftest.py` può spostarlo in una cartella temporanea per ogni test e nessun test tocca il salvataggio vero.
- **Formato:** il file contiene un numero di `version` più lo stato.
- **Scrittura atomica:** prima un file temporaneo, poi la rinomina. Si salva dopo ogni azione, quindi un crash a metà scrittura non deve corrompere la partita.
- **Errori in lettura:** un file mancante, un JSON rotto o una versione diversa danno `None`, mai un'eccezione. Il contenuto lo valida `restore_state`.
- **Errori in scrittura:** non si nascondono, ma si sollevano. Sarà `main.py` (M3) a mostrare un messaggio se il salvataggio non riesce.
- **Repo:** il file di salvataggio e la sua copia temporanea sono nel `.gitignore`.

## 8. `main.py`: l'interfaccia pygame

### Disegno

- **Risoluzione:** tutto si disegna su una Surface 256×224, poi la si scala ×3 (768×672) con `scale`, che è nearest, mai con `smoothscale`. Il gioco gira a 60 fps.
- **Griglia:** con tile da 16 px la griglia è 16×14: 2 righe di HUD e una stanza 16×12 con i muri. Le porte stanno a metà parete, come in Isaac.
- **Testi:** senza antialias; in M6 si passa a un font pixel.
- **Grafica:** fino a M6 tutto è fatto di rettangoli colorati.

### Scene

La sequenza è menu → conferma → gioco → finale. Sopra il gioco possono aprirsi pausa, dialogo, menu delle azioni e inventario.

### Flussi

- **Avvio:** `load_game` e `restore_state` danno i progressi esistenti, oppure `None`. `menu_options` decide se mostrare "Riprendi".
- **Riprendi:**
  - se la partita è finita si apre la schermata del finale, per rivedere l'esito (PT05);
  - altrimenti si compare nell'`entry` della stanza salvata.
- **Nuova partita e Ricomincia:** chiamano `start_new_game(existing)`. Se la risposta è `needs_confirmation` compare la domanda Sì/No. "Sì" richiama la funzione con la conferma; "No" non cambia niente.
- **Salvataggio:** ogni azione passa da `perform`. Dopo ogni esito `ok`, sia di un'azione sia di `start_new_game`, si chiama `save_game`.
- **Testi degli esiti:** compaiono in un riquadro che blocca il movimento finché non lo chiudi. Fa eccezione `entered`: il nome della nuova stanza compare come titolo per qualche secondo, senza bloccare.

### Movimento e porte

- **Movimento:** con frecce o WASD. Il giocatore si ferma contro muri, porte chiuse, enigmi e personaggi. Gli oggetti a terra invece si possono calpestare.
- **Porte:** camminare dentro una porta chiama `enter` **una volta per contatto**. Se la porta è aperta si cambia stanza, altrimenti compare il testo del rifiuto (A1, PT04).
- **Arrivo:** entrando da una porta si compare davanti a quella che riporta indietro.

### Interazione

- **HUD:** due righe.
  - Prima riga: il nome della stanza e "I: inventario".
  - Seconda riga: "E: <azione>" e le icone degli oggetti raccolti. Il bersaglio è la cosa più vicina entro `REACH` pixel; se nessuna cosa è a portata, l'indicatore mostra "Guarda intorno". In un gioco top-down è così che si mostrano le azioni disponibili (PT02). Se le azioni sono più d'una, l'indicatore mostra il nome della cosa.
  - La lista completa dei comandi è in fondo alla schermata del titolo.
- **E:** chiama `actions_for`. Se c'è un'azione sola la esegue subito, se sono di più apre un mini-menu. Le azioni `irreversible` chiedono conferma, con "No" evidenziato. Se vicino non c'è niente, E descrive la stanza. Solo E fa agire: Invio e Spazio servono a chiudere i testi e a scegliere nei menu.
- **I:** mostra l'inventario, con descrizioni e indizi (`clues`).
- **Esc:** apre la pausa, con Continua, Ricomincia, Menu principale ed Esci. Non c'è "Salva", perché si salva già dopo ogni azione.

### Finale

La schermata dice chiaramente quale finale è ("Finale 1 di 2 — Tutti salvi"). Offre "Nuova partita", che passa da `start_new_game` e quindi chiede conferma.

## 9. Requisiti e verifica

| Requisito | Come lo soddisfa il design | Verifica | Milestone |
|---|---|---|---|
| **PT01** Start and resume | `menu_options`; `start_new_game` con conferma; `restore_state` | `test_pt01_*`, A4, A6 | M1, M2, M3 |
| **PT02** Explore | `things_here` e `actions_for`; "E: <azione>" nell'HUD; E senza bersagli descrive la stanza; ogni azione accettata ha un testo | `test_pt02_*` | M1, M4 |
| **PT03** Collect and use | Inventario con I; la chiave apre le porte finali; niente doppioni | A2, A3 | M1, M4 |
| **PT04** Apply consequences | `chosen_door` sigilla l'altra porta e decide il finale; ogni rifiuto ha una spiegazione | A5, `test_pt04_*` | M1 |
| **PT05** Finish and replay | `ENDINGS` con titolo; dopo il finale ogni azione è rifiutata; schermata finale con "Nuova partita" | A5, `test_pt05_*` | M1, M4 |
| **R1** Azioni solo con stanza e condizioni giuste | Ogni azione verifica stanza e condizioni; un rifiuto restituisce lo stato intatto | `test_r1_*` | M1 |
| **R2** Oggetti solo dove previsti, una volta, riutilizzabili | `room` e `appears_if`; `pick_up` rifiuta i doppioni; gli oggetti non si consumano | `test_r2_*`, A2, A3 | M1 |
| **R3** Le scene ricordano i cambiamenti | Visibilità derivata; `done_text`; enigmi risolti disegnati come tali | `test_r3_*`, A3 | M1, M4 |
| **R4** Nuova partita azzera i progressi, non la storia; ogni finale è raggiungibile | `new_game` copia i dati; `story.py` non si modifica mai | `test_r4_*`, A5 | M1 |
| Ricordare scena, oggetti, decisioni e finale | I 4 campi dello stato | A4 | M1, M2 |
| Salvare dopo ogni azione accettata | `main.py` salva dopo ogni esito `ok` | `test_persistence_*`, checklist di M4 | M2, M4 |
| Le modifiche accettate sopravvivono al riavvio; quelle rifiutate non toccano i dati | Scrittura atomica; nessun salvataggio sui rifiuti | `test_persistence_*` | M2 |
| Prima versione: 5 scene, 2 oggetti, 2 finali, circa 10 minuti | Vedi §1 | `test_story_*`, checklist di M4 | M1, M5 |

## 10. Scenari di accettazione

| Scenario | Passi | Cosa si verifica | Milestone |
|---|---|---|---|
| **A1** A locked route | Nuova partita, poi `enter` sulla porta del granchio e su quella dell'angelo | Rifiuto `locked` con spiegazione; il giocatore resta sul ponte, l'inventario non cambia, lo stato è identico | M1 |
| **A2** An unlocked route | Bacchetta, enigma della cabina, chiave, ritorno sul ponte, "usa chiave" sulla porta del granchio, `enter` | Si arriva nella stanza del granchio, con la chiave ancora nell'inventario | M1 |
| **A3** No duplicate collection | Raccogli la bacchetta, vai in cabina, torna e riprova; poi lo stesso con la chiave | Rifiuto, e una sola copia di ciascun oggetto. Tornando in cabina la chiave non è più in `things_here`, e ripetere l'enigma dà `already_done` | M1 |
| **A4** Resume correctly | Bacchetta, chiave, apertura della porta del granchio (la scelta); poi salva e riapri con `load_game` e `restore_state` | Stanza, inventario e flag uguali. `door_status` e `actions_for` identici prima e dopo: stesse vie disponibili, porta dell'angelo ancora sigillata | M1 con giro JSON, M2 con il file |
| **A5** Two outcomes | Due partite nuove, una per finale | Si ottengono `saved` ed `explosion`. Dopo il finale ogni azione è rifiutata e lo stato non cambia, anche dopo aver ricaricato | M1 |
| **A6** Restart safely | Con progressi salvati, `start_new_game` prima senza conferma, poi con conferma | Senza conferma: stato identico e file intatto. Con conferma: ponte, inventario vuoto, flag iniziali, nessun finale, file sovrascritto | M1 e M2 |

Ogni scenario si dimostra due volte: con il test automatico (da `test_a1_*` a `test_a6_*`) e con la checklist manuale qui sotto, nel gioco vero.

### Checklist manuale

Avvia il gioco con `uv run python main.py` dentro `plot_twist/`. Per partire da zero cancella `savegame.json`.

| Scenario | Cosa fare | Cosa deve succedere |
|---|---|---|
| **A1** | Nuova partita. Cammina contro la porta a est (chela) e poi contro quella a ovest (ala). | Compare "È chiusa a chiave". Resti sul ponte e la seconda riga dell'HUD non mostra icone di oggetti. |
| **A2** | Raccogli la bacchetta (E). In cabina: E sul cassetto, poi "Usa: Bacchetta magica". Raccogli la chiave. Sul ponte: E sulla porta della chela, poi "Usa: Chiave d'ottone" e "Sì". Entra. | Sei nella stanza del granchio e la chiave è ancora nell'inventario (I). |
| **A3** | Torna in cabina dopo aver preso la chiave. Prova E vicino al cassetto. | Non c'è una seconda chiave. "Usa: Bacchetta magica" risponde "L'hai già fatto". Nell'inventario c'è una sola chiave. |
| **A4** | A metà partita, dopo aver aperto una porta finale, chiudi la finestra. Riapri e scegli "Riprendi". | Ricompari all'ingresso della stessa stanza, con gli stessi oggetti. La porta scelta è ancora aperta e l'altra ancora sigillata. |
| **A5** | Gioca fino a dare la bacchetta al granchio. Poi, da una partita nuova, all'angelo. | Prima il testo dell'azione, poi la schermata finale ("Finale 1 di 2 — Tutti salvi" o "Finale 2 di 2 — La nave esplode"). Riprendendo la partita torni sulla schermata finale, e non si può più giocare. |
| **A6** | A metà partita, Esc e poi "Ricomincia". Rispondi "No". Rifallo e rispondi "Sì". | Con "No" la partita resta com'era. Con "Sì" sei sul ponte all'inizio, senza oggetti, con la scena d'apertura. |
| **PT04** | Dopo aver aperto la porta della chela, prova la porta dell'ala, sia camminandoci contro sia con "Usa: Chiave d'ottone". | Compare "si è fusa. Non si aprirà mai più". |

## 11. Altri test

- **Integrità dei dati** (`test_story_*`):
  - gli id sono unici;
  - ogni riferimento a stanze, oggetti e flag esiste;
  - ogni porta ha la sua porta di ritorno;
  - ogni porta con `requires` ha un `choice_flag`;
  - ogni enigma ha un `done_text`;
  - nessun testo è vuoto.
- **PT02 e PT04:** in ogni stanza e in vari momenti della partita si provano tutte le azioni di `actions_for`, più alcune impossibili. Le azioni accettate hanno un testo, quelle rifiutate una spiegazione.
- **R1:** ogni rifiuto lascia identici stanza, inventario e flag.
- **R2:** la chiave non si raccoglie prima dell'enigma, né da un'altra stanza.
- **R4:**
  - i dati della storia sono identici dopo due partite complete;
  - un `new_game()` fatto dopo una partita è uguale al primo;
  - entrambi i finali si raggiungono da `new_game()`, anche senza passare dalla stiva.
- **Persistenza (M2):**
  - dopo un'azione rifiutata il file è identico byte per byte;
  - dopo ogni azione accettata, ricaricare dà lo stesso stato;
  - con un file mancante o rotto, "Riprendi" non compare.

Convenzioni:
- **Nomi:** il nome di ogni test contiene l'id del requisito (`test_a1_…`, `test_pt02_…`, `test_r1_…`), così il file di test è anche la dimostrazione dei requisiti.
- **Helper:** ce ne sono due.
  - Il primo gioca una lista di azioni a partire da `new_game()` e verifica che ognuna sia accettata, così ogni scenario è un copione di poche righe.
  - Il secondo fa "`perform`, e se `ok` salva", esattamente come `main.py`.
- **Cosa si controlla:** `event` e stato, **mai i testi**.
- **Isolamento:** i test non importano pygame e non toccano il salvataggio vero.

## 12. Milestone

### M1 — Il gioco senza grafica

**Stato: fatta.** 60 test verdi. In più, 23 bug inseriti apposta nel motore vengono tutti scoperti dai test.

File: `story.py`, `engine.py`, `test_engine.py`.

Ordine di lavoro, scrivendo ogni volta il test prima della funzione:
1. Dati e test di integrità.
2. `new_game`, `start_new_game`, `menu_options`.
3. `pick_up`.
4. `door_status` ed `enter`.
5. `use_item` sugli enigmi.
6. Porte di scelta.
7. Finali e blocco dopo il finale.
8. `restore_state`.
9. `things_here`, `actions_for`, `perform`, `clues`.

*Fatto quando*:
- `uv run pytest` è verde;
- A1–A6 passano nella parte che riguarda il motore (A4 con un giro JSON);
- `story.py` ed `engine.py` non importano pygame;
- entrambi i finali si raggiungono usando solo il motore.

Per chiudere del tutto A4 e A6 già in M1 basta anticipare `save.py`, che è piccolo.

### M2 — Salvataggio

**Stato: fatta.** 83 test verdi in tutto, compresi A4 e A6 con il file vero. In più, 9 bug inseriti apposta in `save.py` vengono tutti scoperti dai test.

File: `save.py`, `test_save.py`, `conftest.py`. In più si completano la parte su file di A4 e A6 e i test di persistenza.

*Fatto quando*:
- salvi a metà partita, ricarichi, e ritrovi stanza, inventario, flag e porta sigillata identici;
- un'azione rifiutata non tocca il file.

### M3 — Finestra, menu e movimento, a rettangoli

**Stato: fatta.** 109 test verdi. In più, 15 bug inseriti apposta in `main.py` vengono tutti scoperti dai test.

Due cose previste per M4 sono arrivate già qui:
- **Schermata finale:** serve per riprendere una partita già finita.
- **"Ricomincia" nella pausa:** usa la stessa conferma della "Nuova partita".

- **Scene e menu:** disegno 256×224 ×3; il menu usa `menu_options` e `start_new_game`, conferma compresa.
- **Stanze:** il layout entra in `story.py`; movimento e collisioni.
- **Porte:** `enter` una volta per contatto. Si compare davanti alla porta di ritorno, oppure in `entry` quando si riprende una partita.

*Fatto quando*:
- giri tra ponte, cabina e stiva;
- provando a passare dalla porta del granchio compare "è chiusa a chiave";
- chiudi il gioco e riprendi dall'ingresso della stanza giusta.

### M4 — Gioco completo, ancora a rettangoli

**Stato: fatta nel codice.** 119 test verdi. Tra i test ci sono due partite complete giocate solo con i tasti, una per finale. In più, 13 bug inseriti apposta nelle parti nuove di `main.py` vengono tutti scoperti dai test. Manca la checklist manuale (§10), da fare sul gioco vero con una finestra.

- "E: <azione>" nell'HUD; E con mini-menu e conferme; riquadro di dialogo.
- Inventario con indizi.
- Dopo il finale si passa alla schermata finale, che esiste già da M3.

*Fatto quando* la checklist manuale A1–A6 passa nel gioco vero:
- una partita completa per ciascun finale;
- uscita e ripresa a metà partita;
- un tentativo di aprire la porta sigillata;
- "Ricomincia" prima annullato, poi confermato.

### M5 — Enigmi veri

- **Enigmi:** si sostituiscono le reazioni placeholder. Se servono meccaniche nuove (sequenze, codici) si aggiungono condizioni al formato della reazione, oppure una funzione al motore, sempre scrivendo prima il test.
- **Test:** il contratto "risolvere un enigma = impostare un flag" resta lo stesso. Nei test cambiano solo i passi che risolvono gli enigmi.
- **Durata:** si aggiungono cose da esaminare, fino a circa 10 minuti di gioco.

*Fatto quando*: i test sono verdi con gli enigmi veri, e chi non conosce la soluzione finisce in circa 10 minuti.

### M6 — Grafica 8-bit

- **Sprite 16×16:** il giocatore in 4 direzioni, con animazione del passo; granchio e angelo; porte aperte, chiuse e sigillate ben distinguibili.
- **Grafica e testi:** un tileset per stanza e un font pixel.
- **Effetti:** transizione tra le stanze, esplosione nel finale, suoni facoltativi.
- **Sprite mancanti:** gli sprite si cercano per id, e se ne manca uno si disegna il rettangolo colorato.

*Fatto quando*: non restano rettangoli, il gioco gira a 60 fps, e i test, invariati, sono tutti verdi.

## 13. Assunzioni

- **Hub:** il ponte è l'hub, e tutte e quattro le porte partono da lì.
- **Menu contestuale:** E apre un menu contestuale, invece di far scegliere un oggetto nell'inventario prima di premere E. Così non c'è un "oggetto in mano" da gestire, e solo il motore sa cosa si può fare.
- **Conferme:** aprire una porta finale e dare la bacchetta chiedono conferma. Una E premuta per sbaglio non deve decidere la partita.
- **Riprendi:** su una partita finita mostra di nuovo il finale.
- **Nuova partita:** chiede conferma ogni volta che esiste un salvataggio, anche di una partita finita (PT01 alla lettera).
- **Stiva:** è facoltativa. L'indizio aiuta a scegliere, ma non serve per finire.
