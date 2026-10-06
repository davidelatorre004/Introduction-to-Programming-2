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
| Cabina del capitano | `cabin` | Quattro generatori collegati: accenderli tutti insieme dissolve la barriera che protegge la prima metà della chiave |
| Stiva | `hold` | Sbarrata da un cancello finché non hai la prima metà. Dentro, cinque piastrelle da calpestare in tre sequenze: dissolvono la barriera intorno all'incudine, con sopra la seconda metà. Sull'incudine le due metà si fondono nella chiave fusa. E un barile che, con la bacchetta, rivela che il granchio dice la verità |
| Stanza del granchio | `crab_room` | Il granchio, grande 2×2 caselle: dargli la bacchetta porta al finale *Tutti salvi* |
| Stanza dell'angelo | `angel_room` | L'angelo, alto 2 caselle: dargli la bacchetta porta al finale *La nave esplode* |

Regole della storia:
- **Porte:** dal ponte si entra liberamente in cabina. La porta della stiva ha un cancello, che si apre da solo appena hai la prima metà della chiave. Le porte del granchio e dell'angelo richiedono la chiave fusa: le due metà, fuse sull'incudine della stiva. Con la chiave fusa si aprono entrambe.
- **Scelta:** a chi dare la bacchetta. Le porte finali si possono aprire tutte e due, quindi si può incontrare sia il granchio sia l'angelo prima di decidere.
- **Oggetti:** non si duplicano, e non si consumano usandoli. L'unica trasformazione è all'incudine: le due metà della chiave diventano la chiave fusa.
- **Percorso minimo:** bacchetta → generatori in cabina → prima metà della chiave → piastrelle in stiva → seconda metà → fusione all'incudine → una porta finale → dare la bacchetta. Il barile della stiva è facoltativo: dà l'indizio per scegliere la porta giusta.
- **Enigmi:** due, entrambi veri (M5), descritti in §4: gli interruttori collegati in cabina e le piastrelle in stiva. Il barile resta una semplice reazione alla bacchetta.

Controlli:
- frecce o WASD per muoversi;
- **E** per interagire con ciò che è vicino;
- **I** per l'inventario;
- **Esc** per il menu.

Cosa chiede il brief per la prima versione, e dove si trova nel gioco:

| Il brief chiede | Nel gioco |
|---|---|
| Almeno 5 scene | 5 stanze |
| Almeno 2 oggetti collezionabili | Bacchetta e le due metà della chiave, che all'incudine diventano la chiave fusa |
| 2 finali raggiungibili | *Tutti salvi* e *La nave esplode* |
| Un finale che dipende da una scelta o da un oggetto precedente | Entrambi dipendono da a chi si dà la bacchetta, e servono la chiave fusa per arrivarci |
| Circa 10 minuti di gioco | Due enigmi veri. Quanto dura davvero va misurato con chi non conosce le soluzioni |
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
| `main.py` | pygame: finestra, input, disegno, scene, trigger di movimento | `engine`, `save`, `sounds`, `sprites`, `story`, `pixel_font` |
| `sounds.py` | Gli effetti sonori, fatti di onde quadre generate nel codice: niente file audio | `pygame`, `array` |
| `test_engine.py` | Scenari A1–A6 e requisiti del brief | `engine`, `story`; da M2 anche `save` |
| `test_save.py` | Comportamento di `save.py` | `save`, `engine` |
| `conftest.py` | Preparazione comune dei test: sposta il salvataggio in una cartella temporanea | `save` |
| `test_main.py` | Layout, muri e porte, movimento, menu e salvataggio visti dall'interfaccia, senza aprire finestre | `main`, `engine`, `save`, `story`, `pygame` |
| `sprites.py` | Gli sprite e le piastrelle in pixel art, scritti come testo (una lettera per pixel) | `pygame` |
| `pixel_font.py` | Il font pixel, scritto come testo; si usa come `pygame.font.Font` | `pygame` |
| `test_graphics.py` | Sprite, font e animazioni (M6) | `main`, `sprites`, `pixel_font`, `engine`, `story`, `pygame` |
| `test_sounds.py` | Le onde degli effetti, e il gioco che resta muto senza audio (M5) | `sounds`, `pygame` |

La cartella `plot_twist/` sta accanto a `splitit/` ed è organizzata allo stesso modo:
- un `pyproject.toml` per uv, con Python 3.12, pygame e pytest;
- un `.gitignore` che esclude il file di salvataggio.

## 4. `story.py`: i dati

Convenzioni:
- **Solo costanti:** niente funzioni, niente import.
- **Id:** ogni cosa, stanze comprese, ha un id stringa unico in tutto il gioco, in inglese (come `crab_door`). I testi a schermo sono in italiano.
- **Dizionari piatti:** oggetti, porte e personaggi stanno in dizionari `id → dati` con un campo `room`, invece di essere elencati dentro le stanze. Così ogni informazione sta in un posto solo.
- **Testi:** stanno tutti qui, mai nel motore. Puoi riscrivere i dialoghi senza toccare né le regole né i test.

| Costante | Contenuto | Campi |
|---|---|---|
| `START_ROOM` | `"deck"` | — |
| `FLAGS` | Nome del flag → valore iniziale | `generator_a: False`, `generator_b: True`, `generator_c: True`, `generator_d: False`, `cabin_solved: False`, `hold_phase: 1`, `hold_step: 0`, `hold_solved: False`, `crab_truthful: False`, `crab_door: None`, `angel_door: None` |
| `ROOMS` | Le 5 stanze | `name`, `description`, `outdoor` (il ponte è all'aperto: serve al disegno) |
| `ITEMS` | `wand`, `key`, `second_key`, `fused_key` | `part_of` (l'oggetto in cui si fonde, o `None`), `name`, `description`, `room`, `appears_if` (flag che lo fa comparire, o `None`), `free_if` (flag che permette di raccoglierlo, o `None`), `pickup_text` |
| `DOORS` | 8 porte, una per verso | `room`, `to`, `requires` (lista di oggetti, vuota se la porta non ha serratura), `choice_flag` (flag o `None`), `opens_with` (oggetto o `None`), `locked_text`, `sealed_text`, `open_text` (solo per le porte con serratura), `barred_text` (solo per le porte sbarrate) |
| `OBJECTS` | 4 generatori, 5 piastrelle, 2 barriere, un altare, un'incudine, un barile e 2 personaggi | `kind`, `name`, `room`, `look_text`, `done_text` (obbligatorio per gli enigmi), `reactions` (oggetto usato → reazione). I generatori hanno in più `flag`, `toggles`, `toggle_text` e `label`; le piastrelle `label`; le barriere `open_if`; l'incudine `fuse_text`. Granchio e angelo hanno `size` |
| `CIRCUITS` | `cabin_circuit` | `room`, `switches` (i generatori), `solved_flag`, `solved_text` |
| `FLOOR_PUZZLES` | `hold_tiles` | `room`, `zone`, `phases` (ognuna con `name` e `steps`), `phase_flag`, `step_flag`, `solved_flag` e i testi `lit_text`, `phase_text`, `wrong_text`, `left_text`, `solved_text` |
| `ENDINGS` | `saved`, `explosion` | `title`, `text` (righe della schermata finale), `good` |
| `CLUES` | Flag → testo mostrato nell'inventario | `crab_truthful` → "Il granchio dice sempre la verità." |
| `MESSAGES` | Testi generici | Scena d'apertura, domanda di conferma per ricominciare, spiegazioni dei rifiuti ("non succede niente", "non è qui", "la barriera ti impedisce di prenderla", "a questa chiave manca l'altra metà", …), testo di una porta aperta, etichette delle azioni del tasto E |

I `kind` di `OBJECTS`:
- `puzzle` e `character`: reagiscono quando ci usi sopra un oggetto (vedi "Reazioni").
- `switch`: un generatore di un circuito. Attivarlo inverte i flag elencati in `toggles`, compreso il suo.
- `tile`: una piastrella numerata di un enigma a pavimento. Non è solida: ci si cammina sopra, ed è camminandoci sopra che si gioca.
- `barrier`: blocca il passaggio finché il flag `open_if` è falso, poi sparisce.
- `altar`: si può solo guardare, e ci si appoggia un oggetto: l'altare della cabina.
- `anvil`: anche sull'incudine si appoggia un oggetto, e in più ci si fondono le parti di un oggetto (vedi "La fusione").

### Porte

| id | Collegamento | Apertura |
|---|---|---|
| `deck_to_cabin` | Ponte → cabina | Libera |
| `deck_to_hold` | Ponte → stiva | Sbarrata da un cancello finché il giocatore non ha la prima metà della chiave (`opens_with: key`). Poi è libera: non serve usare niente |
| `deck_to_crab`, `deck_to_angel` | Ponte → stanze finali | `requires: [fused_key]`, con un flag a testa (`crab_door`, `angel_door`): aprirne una non sigilla l'altra. Le metà separate non girano |
| `cabin_to_deck`, `hold_to_deck`, `crab_to_deck`, `angel_to_deck` | Ritorno al ponte | Libere |

Ogni collegamento ha due porte e ognuna sta in una sola stanza, quindi il motore non deve capire da che lato si sta passando.

### Oggetti collezionabili

- `wand`: sul ponte, sempre a terra (`appears_if` e `free_if` sono `None`).
- `key`, la "Chiave centrale": la prima metà della chiave. In cabina, sull'altare. Si vede da subito, ma con `free_if: cabin_solved` non si raccoglie finché c'è la barriera.
- `second_key`, la "Seconda chiave": la seconda metà. In stiva, sull'incudine, con `free_if: hold_solved`.
- `fused_key`, la "Chiave fusa": non sta da nessuna parte (`room` e `pos` sono `None`). Nasce all'incudine dalle due metà, che hanno `part_of: fused_key`.

### La fusione

Si usa una delle due metà sull'incudine (E vicino all'incudine, poi "Usa: …").
- Con entrambe le metà nell'inventario, le metà spariscono e al posto della prima compare la Chiave fusa. Compare il `fuse_text` dell'incudine.
- Con una metà sola, rifiuta con `missing_item`: manca l'altra.
- Le metà fuse non tornano più: non ricompaiono né sull'altare né sull'incudine, e la porta della stiva resta aperta, perché la chiave fusa vale come la prima metà.
- Una metà usata su una porta finale non gira: rifiuta con `not_fused`, e il testo dice di fonderla all'incudine.
- La chiave fusa non si consuma: dopo aver aperto una porta, apre anche l'altra.

### Reazioni

Una reazione imposta un flag (`set_flag` con il nome e `value` con il valore) oppure chiude la partita (`ending` con l'id del finale). In entrambi i casi ha un `text`.

| Bersaglio | Oggetto usato | Effetto |
|---|---|---|
| `hold_puzzle` | `wand` | `crab_truthful = True`: l'indizio compare nell'inventario |
| `crab` | `wand` | Finale `saved` |
| `angel` | `wand` | Finale `explosion` |

Il barile della stiva è solo una reazione alla bacchetta. I due enigmi veri invece non usano reazioni: ognuno ha un meccanismo suo, i circuiti e gli enigmi a pavimento. In tutti i casi il resto del gioco legge solo il flag finale (`crab_truthful`, `cabin_solved`, `hold_solved`).

### L'enigma dei generatori (M5)

Nella cabina ci sono quattro generatori agli angoli di un quadrato:
- A in alto a sinistra;
- B in alto a destra;
- C in basso a sinistra;
- D in basso a destra.

Ogni generatore è un flag booleano: vero è acceso, falso è spento. È collegato con un cavo ai due generatori vicini lungo i lati del quadrato, mai a quello in diagonale. Attivarlo inverte lui e i due vicini:

| Attivi | Si invertono |
|---|---|
| A | A, B, C |
| B | B, A, D |
| C | C, A, D |
| D | D, B, C |

Regole:
- **Inizio:** A spento, B acceso, C acceso, D spento. I generatori tornano così **ogni volta che si entra in cabina**, finché il circuito non è completo.
- **Vittoria:** dopo ogni attivazione si controlla il circuito. Se i quattro generatori sono accesi insieme:
  - `cabin_solved` diventa vero;
  - la barriera sparisce, e con lei la sua collisione;
  - compare "Il flusso elettrico è completo! La barriera si è dissolta!";
  - la Chiave centrale sull'altare si può raccogliere.
- **Dopo la vittoria:** i generatori restano accesi e non si attivano più.

Soluzione: l'ordine non conta, e attivare due volte lo stesso generatore lo annulla. Risolvere vuol dire quindi scegliere quali generatori attivare una volta. Dalla configurazione iniziale bastano A e D. Ognuna delle 16 configurazioni possibili ha una soluzione; la più lunga, da tutti spenti, richiede di attivarli tutti e quattro.

### L'enigma delle piastrelle (M5)

Nella stiva ci sono cinque piastrelle numerate da 1 a 5, in fila, una casella sì e una no. Intorno c'è una zona di grata metallica, una casella più larga su ogni lato: le corsie sopra e sotto le piastrelle permettono di saltarne alcune, per esempio per andare dalla 5 alla 3 senza calpestare la 4. Si gioca camminando: il tasto E non serve.

L'enigma è una macchina a stati. Lo stato sono due flag: la fase in corso (`hold_phase`, da 1 a 3) e quante piastrelle della sua sequenza sono già accese (`hold_step`).

| Fase | Nome | Sequenza |
|---|---|---|
| 1 | L'Onda | 1 → 2 → 3 → 4 → 5 |
| 2 | Il Ritorno | 5 → 3 → 1 |
| 3 | Il Cortocircuito | 1 → 5 → 2 → 4 → 3 |

Regole:
- **Passo giusto:** calpestare la prossima piastrella della sequenza la accende.
- **Fine di una fase:** la fase dopo parte dalla piastrella su cui il giocatore sta, che resta accesa. La Fase 2 parte già con la 5 accesa, la Fase 3 con la 1, come chiede la consegna ("partendo dalla piastrella 5").
- **Errore:** calpestare qualsiasi altra piastrella, anche una accesa prima nella stessa fase, oppure uscire dalla zona. Le luci si spengono e ricomincia **la fase in corso**, dalla sua prima piastrella; le fasi già superate restano superate. Uscire dalla stiva vale come uscire dalla zona.
- **Non sono errori:** tornare sulla piastrella accesa per ultima, e uscire dalla zona quando nessuna piastrella è accesa.
- **Vittoria:** l'ultima piastrella della Fase 3 imposta `hold_solved`. Allora:
  - la barriera intorno all'incudine sparisce, e con lei la sua collisione;
  - compare "Il sistema della stiva si sblocca! La barriera si è dissolta!";
  - la Seconda chiave sull'incudine si può raccogliere.

  Da quel momento le piastrelle restano tutte accese e non reagiscono più.

Indizi: i nomi delle tre fasi sono incisi sull'incudine (li si legge esaminando la barriera), e ogni cambio di fase annuncia il nome della prossima.

La soluzione più corta è 1 2 3 4 5, 3 1, 5 2 4 3: undici passi. Un test prova ogni piastrella in ogni momento e verifica che non esista un'altra soluzione della stessa lunghezza.

### Regole derivate

Le calcola il motore; non si salvano mai.

- **Oggetto a terra:** un oggetto è a terra se sono vere tutte e tre le condizioni:
  - sta nella stanza corrente;
  - `appears_if` è `None` o vero;
  - non è nell'inventario.

  Per questo un oggetto con `appears_if` compare quando il suo flag diventa vero, e ogni oggetto sparisce appena raccolto.
- **Oggetto protetto:** un oggetto a terra si raccoglie solo se `free_if` è `None` o vero. Altrimenti si vede e si può esaminare, ma `pick_up` lo rifiuta. È il caso della chiave dietro la barriera.
- **Barriera:** c'è finché il suo `open_if` è falso. Poi sparisce da `things_here`, e quindi anche dal disegno e dalle collisioni.
- **Stato di un generatore:** è il suo flag. Un circuito è completo quando tutti i suoi generatori sono accesi.
- **Porta sbarrata:** con `opens_with`, è sbarrata finché il giocatore non ha quell'oggetto; poi vale come le altre.
- **Piastrella accesa:** è tra le prime `hold_step` della sequenza della fase in corso. Se l'enigma è risolto, sono accese tutte.
- **Stato di una porta:** senza `requires` è sempre aperta. Con `choice_flag`:
  - è aperta se il flag contiene l'id di questa porta;
  - è **sigillata per sempre** se contiene l'id di un'altra (succede solo a porte che condividono il flag: oggi nessuna);
  - è chiusa se il flag è `None`.

  Una porta chiusa "normale" è una porta il cui `choice_flag` non è condiviso con nessun'altra.
- **Enigma risolto:** il suo flag ha già il valore della reazione, quindi ripeterlo non fa niente.
- **Partita finita:** `ending` non è `None`.

### Layout

Si aggiunge in M3, e il motore non lo legge mai.
- `entry` per ogni stanza: il punto in cui si compare riprendendo una partita.
- `side` per ogni porta: N, S, E oppure O, a metà parete.
- `pos` per oggetti e personaggi.
- `size` per ciò che occupa più di un tile: ogni barriera ne copre 3×2, intorno all'altare o all'incudine; il granchio 2×2; l'angelo 1×2. Gli sprite hanno la stessa misura dell'area.
- `zone` per ogni enigma a pavimento: il rettangolo intorno alle piastrelle. Uscirne fa ricominciare la fase.

Un oggetto può stare sul tile di un altare: è così che la chiave sta sull'altare.

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
  - il finale esista;
  - ogni enigma a pavimento non risolto abbia meno piastrelle accese della sequenza della sua fase. Un salvataggio con, per esempio, la Fase 2 e quattro piastrelle accese è impossibile, e viene rifiutato.

  I flag mancanti li completa con il valore iniziale. Così un salvataggio fatto prima che esistessero i flag dei generatori o delle piastrelle si riprende ancora.

### Letture

Queste funzioni non cambiano niente.
- **`is_over(state)`:** dice se è stato raggiunto un finale.
- **`has_item(state, item)`:** dice se un oggetto è nell'inventario.
- **`door_status(state, door)`:** restituisce `"open"`, `"barred"`, `"locked"` o `"sealed"`, secondo le regole derivate.
- **`things_here(state)`:** restituisce tutto ciò che c'è ora nella stanza, con id, tipo e stato:
  - oggetti a terra visibili (`on_floor`, oppure `guarded` se non si possono ancora raccogliere);
  - porte;
  - enigmi (risolti o no);
  - generatori (`on` o `off`);
  - piastrelle (`lit` o `dark`);
  - le barriere, finché ci sono (`up`);
  - personaggi, altare e incudine.

  `main.py` sa cosa disegnare e cosa è solido solo da qui.
- **`actions_for(state, target)`:** restituisce le azioni possibili premendo E vicino al bersaglio, ciascuna con un'etichetta:
  - "Raccogli" per un oggetto a terra, oppure solo "Esamina" se è protetto;
  - "Attiva" per un generatore, come unica azione;
  - "Entra" per una porta aperta;
  - "Esamina" oppure "Parla";
  - "Usa X" o "Dai X" per **ogni** oggetto dell'inventario, non solo per quello giusto, altrimenti il menu rivelerebbe la soluzione.

  Segna come `irreversible` le azioni che fanno scattare un finale, o che aprono una porta che ne sigilla un'altra (oggi nessuna: le porte finali hanno un flag a testa). Quindi chiede conferma solo dare la bacchetta. Dopo il finale restituisce una lista vuota, e così per un enigma a pavimento: non è un bersaglio di E.
- **`clues(state)`:** restituisce i testi di `CLUES` dei flag veri, da mostrare nell'inventario.

### Azioni

Ogni azione controlla per prima cosa che la partita non sia finita.
- **`pick_up(state, item)`:** accettata se l'oggetto è a terra in questa stanza e non è protetto. Lo aggiunge in fondo all'inventario. Se è protetto rifiuta con `guarded`.
- **`enter(state, door)`:** accettata se la porta è in questa stanza ed è aperta. Cambia `room`, e il testo è il nome della nuova stanza. Spegne le piastrelle degli enigmi a pavimento non risolti della stanza che lascia: uscire dalla stanza è uscire dalla zona. Rimette nella configurazione iniziale i generatori dei circuiti non completi della nuova stanza. Se la porta è sbarrata, chiusa o sigillata, rifiuta con il testo della porta.
- **`activate(state, switch)`:** accettata se il generatore è nella stanza e il suo circuito non è ancora completo.
  - Inverte ogni flag in `toggles`.
  - Poi controlla il circuito. Se tutti i generatori sono accesi imposta `solved_flag` e risponde `circuit_complete` con `solved_text`; altrimenti risponde `toggled` con il `toggle_text` del generatore.
  - Su un circuito già completo rifiuta con `already_done`: i generatori restano accesi.
  - Un id che non è un generatore solleva un'eccezione, come ogni id sbagliato.
- **`step_on(state, tile)`:** la chiama `main.py` quando il giocatore arriva su una piastrella. Fa avanzare la macchina a stati descritta in §4:
  - `tile_lit` se la piastrella è la prossima della sequenza;
  - `phase_complete` se chiude una fase, con il nome della prossima nel testo;
  - `tiles_complete` se chiude l'ultima, con `solved_text`;
  - `tiles_reset` se è sbagliata: la fase ricomincia.

  Rifiuta con `already_lit` se è la piastrella accesa per ultima, con `already_done` se l'enigma è già risolto, con `not_here` se la piastrella è in un'altra stanza.
- **`leave_zone(state, floor_puzzle)`:** la chiama `main.py` quando il giocatore esce dalla zona intorno alle piastrelle. Se c'era almeno una piastrella accesa, risponde `tiles_reset` e la fase ricomincia; altrimenti rifiuta con `nothing_happens`.
- **`use_item(state, item, target)`:** richiede che `item` sia nell'inventario e che `target` sia nella stanza.
  - Su una porta chiusa che richiede quell'oggetto: se il giocatore ha **tutti** gli oggetti di `requires`, la apre scrivendo il proprio id nel suo `choice_flag` (`crab_door` o `angel_door`); altrimenti rifiuta con `missing_item`. Una parte di un oggetto richiesto (una metà della chiave) rifiuta con `not_fused`.
  - Sull'incudine: fonde le parti, come in "La fusione".
  - Su un enigma o un personaggio: applica la reazione. Se non c'è una reazione il testo è "non succede niente"; se la reazione è già stata applicata è "già fatto".
  - L'oggetto resta sempre nell'inventario, anche dopo "dai".
- **`examine(state, target)`:** restituisce solo un testo. A seconda del bersaglio è:
  - la descrizione della stanza, se il bersaglio è la stanza corrente;
  - la descrizione di un oggetto;
  - la battuta di un personaggio;
  - "è chiusa a chiave", o che cosa sbarra la porta;
  - il `done_text` di un enigma risolto.
- **`perform(state, action)`:** riceve un'azione come dato e chiama la funzione giusta, `step_on` e `leave_zone` comprese. L'azione ha verbo, oggetto e bersaglio, cioè la stessa forma prodotta da `actions_for`. `main.py` fa passare tutte le azioni da qui, e i test scrivono gli scenari come liste di azioni.

### Codici di `event`

- **Azioni accettate:** `started`, `picked_up`, `entered`, `door_opened`, `fused`, `flag_set`, `toggled`, `circuit_complete`, `tile_lit`, `phase_complete`, `tiles_complete`, `tiles_reset`, `ending`, `info`.
- **Azioni rifiutate:** `needs_confirmation`, `game_over`, `not_here`, `already_have`, `guarded`, `no_item`, `barred`, `locked`, `sealed`, `already_open`, `missing_item`, `not_fused`, `already_done`, `already_lit`, `nothing_happens`.

Un errore sulle piastrelle (`tiles_reset`) è un'azione accettata: cambia lo stato, quindi si salva.

Funzioni private di supporto:
- costruire un esito o un rifiuto;
- verificare se una cosa è nella stanza corrente;
- applicare una reazione a una copia dello stato;
- dire se un oggetto è protetto e se una cosa è ancora in piedi;
- trovare il circuito di un generatore, dire se è completo, rimettere i generatori nella configurazione iniziale;
- trovare l'enigma a pavimento di una piastrella, dire se una piastrella è accesa, spegnere le piastrelle della stanza che si lascia, controllare che un salvataggio non abbia un momento impossibile delle piastrelle.

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
- **Testi:** con il font pixel di `pixel_font.py`, a tre misure: testo, titoli, titolo grande.
- **Grafica:** sprite 16×16 e piastrelle da `sprites.py`.
  - Le porte sono disegnate per la parete nord e girate per le altre.
  - Il giocatore guardando a sinistra è lo sprite di destra specchiato.
  - Chi sta più in basso sullo schermo copre ciò che sta dietro.
  - Se manca uno sprite si disegna il rettangolo colorato.
- **Animazioni:** contano i frame in `app["frame"]`, non il tempo reale, così i test le possono riprodurre. Sono:
  - due passi alternati quando il giocatore cammina;
  - due immagini di mare;
  - la nave che dondola;
  - la freccia lampeggiante del testo;
  - la stanza che esce dal buio dopo una porta;
  - le barriere che crepitano;
  - le piastrelle che lampeggiano di rosso dopo un errore (`FLASH_FRAMES`), prima di spegnersi;
  - l'alba o l'esplosione nei finali.
- **Piastrelle:** la zona è una grata metallica; sopra, le piastrelle grigie da spente e gialle da accese, con il numero scritto dal font. La porta della stiva, finché è sbarrata, ha le sbarre e una placca d'ottone con l'incavo a mezza chiave. Le due metà della chiave nell'inventario sono l'anello e la parte con i denti; la chiave fusa è intera, con il segno della saldatura. Il granchio è disegnato 32×32 e l'angelo 16×32.
- **Generatori:** ognuno ha una lampada e una leva, e sopra la sua lettera. Accesi e spenti si distinguono a colpo d'occhio. Un cavo unisce due generatori collegati, e si illumina quando sono accesi entrambi. La chiave sull'altare è disegnata un po' più in alto, appoggiata sopra.

### Scene

La sequenza è menu → conferma → gioco → finale. Sopra il gioco possono aprirsi pausa, dialogo, menu delle azioni e inventario.

### Flussi

- **Avvio:** `load_game` e `restore_state` danno i progressi esistenti, oppure `None`. `menu_options` decide se mostrare "Riprendi".
- **Riprendi:**
  - se la partita è finita si apre la schermata del finale, per rivedere l'esito (PT05);
  - altrimenti si compare nell'`entry` della stanza salvata.
- **Nuova partita e Ricomincia:** chiamano `start_new_game(existing)`. Se la risposta è `needs_confirmation` compare la domanda Sì/No. "Sì" richiama la funzione con la conferma; "No" non cambia niente.
- **Salvataggio:** ogni azione passa da `perform`. Dopo ogni esito `ok`, sia di un'azione sia di `start_new_game`, si chiama `save_game`.
- **Testi degli esiti:** compaiono in un riquadro che blocca il movimento finché non lo chiudi. Fanno eccezione, comparendo per qualche secondo senza bloccare:
  - `entered`: il nome della nuova stanza, come titolo;
  - `toggled`: il "Clic!" di un generatore, così si provano le combinazioni senza chiudere un riquadro ogni volta;
  - gli esiti delle piastrelle (`tile_lit`, `phase_complete`, `tiles_reset`), perché il giocatore sta camminando.

  I messaggi di vittoria dei due enigmi (`circuit_complete`, `tiles_complete`) compaiono invece nel riquadro.

### Movimento e porte

- **Movimento:** con frecce o WASD. Il giocatore si ferma contro muri, porte chiuse, enigmi, personaggi, generatori, barriere, altare e incudine. Gli oggetti a terra e le piastrelle invece si possono calpestare.
- **Porte:** camminare dentro una porta chiama `enter` **una volta per contatto**. Se la porta è aperta si cambia stanza, altrimenti compare il testo del rifiuto (A1, PT04).
- **Arrivo:** entrando da una porta si compare davanti a quella che riporta indietro.

### Trigger di movimento

Le piastrelle si giocano con i piedi, non con E. Dopo ogni passo, `update` chiama `floor_triggers`:
- **Piastrella:** il giocatore sta sulla piastrella che ha sotto il centro del corpo. Quando quella piastrella cambia, ed è una piastrella, si chiama `step_on`. Restare fermi, o muoversi sulla stessa piastrella, non la ripete.
- **Zona:** quando il centro del corpo esce dalla zona di un enigma, si chiama `leave_zone`.
- **Memoria:** `app` ricorda la piastrella e le zone del frame prima (`on_tile`, `zones`). Comparire in un punto (all'inizio, riprendendo, dopo una porta) non è camminarci: `settle_on_floor` aggiorna la memoria senza far scattare niente. I punti di arrivo sono comunque fuori dalle zone, e un test lo controlla.
- **Esiti:** `floor_action` li mostra senza fermare il giocatore. I rifiuti sono muti, perché camminare non è una richiesta; gli altri esiti suonano, compaiono nella striscia e si salvano. La vittoria apre il riquadro di testo.
- **E e le piastrelle:** le piastrelle non sono bersagli di E. Stando sopra una piastrella, E guarda intorno.

### Suoni

`sounds.py` fa gli effetti con onde quadre, come una console 8-bit, senza file audio. `EVENT_SOUNDS` dice quale suona per ogni esito delle piastrelle:

| Esito | Effetto |
|---|---|
| `tile_lit` | `blip`, una nota breve |
| `phase_complete` | `ding`, due note che salgono: il suono di conferma |
| `tiles_complete` | `fanfare`, quattro note |
| `tiles_reset` | `buzz`, il "BZZZ" grave dell'errore |

`main()` li prepara all'avvio con `sounds.load()`, nel formato del mixer. Se il computer non ha audio, il mixer non parte e `play` non fa niente: il gioco va avanti uguale.

### Interazione

- **HUD:** due righe.
  - Prima riga: il nome della stanza e "I: inventario".
  - Seconda riga: "E: <azione>" e le icone degli oggetti raccolti. Il bersaglio è la cosa più vicina entro `REACH` pixel; se nessuna cosa è a portata, l'indicatore mostra "Guarda intorno". In un gioco top-down è così che si mostrano le azioni disponibili (PT02). Se le azioni sono più d'una, l'indicatore mostra il nome della cosa.
  - La lista completa dei comandi è in fondo alla schermata del titolo.
- **E:** chiama `actions_for` sulla cosa più vicina, piastrelle escluse. Se c'è un'azione sola la esegue subito, se sono di più apre un mini-menu. Le azioni `irreversible` chiedono conferma, con "No" evidenziato. Se vicino non c'è niente, E descrive la stanza. Solo E fa agire: Invio e Spazio servono a chiudere i testi e a scegliere nei menu.
- **I:** mostra l'inventario, con descrizioni e indizi (`clues`).
- **Esc:** apre la pausa, con Continua, Ricomincia, Menu principale ed Esci. Non c'è "Salva", perché si salva già dopo ogni azione.

### Finale

La schermata dice chiaramente quale finale è ("Finale 1 di 2 — Tutti salvi"). Offre "Nuova partita", che passa da `start_new_game` e quindi chiede conferma.

## 9. Requisiti e verifica

| Requisito | Come lo soddisfa il design | Verifica | Milestone |
|---|---|---|---|
| **PT01** Start and resume | `menu_options`; `start_new_game` con conferma; `restore_state` | `test_pt01_*`, A4, A6 | M1, M2, M3 |
| **PT02** Explore | `things_here` e `actions_for`; "E: <azione>" nell'HUD; E senza bersagli descrive la stanza; ogni azione accettata ha un testo | `test_pt02_*` | M1, M4 |
| **PT03** Collect and use | Inventario con I; le due metà, fuse all'incudine, diventano la chiave che apre entrambe le porte finali; niente doppioni | A2, A3, `test_pt03_*` | M1, M4, M5 |
| **PT04** Apply consequences | A chi si dà la bacchetta decide il finale; la fusione cambia per sempre l'inventario; ogni rifiuto ha una spiegazione, anche la metà non fusa; ogni errore sulle piastrelle si vede, si legge e si sente | A5, `test_pt04_*` | M1, M5 |
| **PT05** Finish and replay | `ENDINGS` con titolo; dopo il finale ogni azione è rifiutata; schermata finale con "Nuova partita" | A5, `test_pt05_*` | M1, M4 |
| **R1** Azioni solo con stanza e condizioni giuste | Ogni azione verifica stanza e condizioni; un rifiuto restituisce lo stato intatto; la stiva è sbarrata finché non si ha la prima metà | `test_r1_*` | M1, M5 |
| **R2** Oggetti solo dove previsti, una volta, riutilizzabili | `room`, `appears_if` e `free_if`; `pick_up` rifiuta i doppioni; gli oggetti non si consumano, e le metà fuse non tornano | `test_r2_*`, A2, A3 | M1, M5 |
| **R3** Le scene ricordano i cambiamenti | Visibilità derivata; `done_text`; enigmi risolti disegnati come tali; il circuito completo e le piastrelle risolte restano tali | `test_r3_*`, A3 | M1, M4, M5 |
| **R4** Nuova partita azzera i progressi, non la storia; ogni finale è raggiungibile | `new_game` copia i dati; `story.py` non si modifica mai | `test_r4_*`, A5 | M1 |
| Ricordare scena, oggetti, decisioni e finale | I 4 campi dello stato | A4 | M1, M2 |
| Salvare dopo ogni azione accettata | `main.py` salva dopo ogni esito `ok` | `test_persistence_*`, checklist di M4 | M2, M4 |
| Le modifiche accettate sopravvivono al riavvio; quelle rifiutate non toccano i dati | Scrittura atomica; nessun salvataggio sui rifiuti | `test_persistence_*` | M2 |
| Prima versione: 5 scene, 2 oggetti, 2 finali, circa 10 minuti | Vedi §1 | `test_story_*`, checklist di M4 | M1, M5 |
| Enigma delle piastrelle: macchina a stati per 3 fasi, errore che fa ricominciare la fase, BZZZ e luci spente, vittoria che toglie la barriera | Vedi §4, §6 e §8 | `test_m5_*` in `test_engine.py`; trigger, suoni e lampeggio in `test_main.py`; `test_sounds.py` | M5 |

## 10. Scenari di accettazione

| Scenario | Passi | Cosa si verifica | Milestone |
|---|---|---|---|
| **A1** A locked route | Nuova partita, poi `enter` sulla porta del granchio e su quella dell'angelo | Rifiuto `locked` con spiegazione; il giocatore resta sul ponte, l'inventario non cambia, lo stato è identico | M1 |
| **A2** An unlocked route | Bacchetta, generatori (A e poi D), prima metà, piastrelle della stiva, seconda metà, fusione all'incudine, ritorno sul ponte, "usa chiave fusa" sulla porta del granchio, `enter` | Si arriva nella stanza del granchio, con la chiave fusa ancora nell'inventario | M1, M5 |
| **A3** No duplicate collection | Raccogli la bacchetta, vai in cabina, torna e riprova; poi lo stesso con le due metà | Rifiuto, e una sola copia di ciascun oggetto. Tornando in cabina o in stiva le metà non ci sono più, neanche dopo la fusione; riattivare un generatore o ricalpestare le piastrelle dà `already_done` | M1, M5 |
| **A4** Resume correctly | Bacchetta, chiave fusa, apertura della porta del granchio; poi salva e riapri con `load_game` e `restore_state` | Stanza, inventario e flag uguali. `door_status` e `actions_for` identici prima e dopo: stesse vie disponibili, porta dell'angelo ancora chiusa e ancora da aprire | M1 con giro JSON, M2 con il file |
| **A5** Two outcomes | Due partite nuove, una per finale | Si ottengono `saved` ed `explosion`. Dopo il finale ogni azione è rifiutata e lo stato non cambia, anche dopo aver ricaricato | M1 |
| **A6** Restart safely | Con progressi salvati, `start_new_game` prima senza conferma, poi con conferma | Senza conferma: stato identico e file intatto. Con conferma: ponte, inventario vuoto, flag iniziali, nessun finale, file sovrascritto | M1 e M2 |

Ogni scenario si dimostra due volte: con il test automatico (da `test_a1_*` a `test_a6_*`) e con la checklist manuale qui sotto, nel gioco vero.

### Checklist manuale

Avvia il gioco con `uv run python main.py` dentro `plot_twist/`. Per partire da zero cancella `savegame.json`.

| Scenario | Cosa fare | Cosa deve succedere |
|---|---|---|
| **A1** | Nuova partita. Cammina contro la porta a est (chela) e poi contro quella a ovest (ala). | Compare "È chiusa a chiave". Resti sul ponte e la seconda riga dell'HUD non mostra icone di oggetti. |
| **A2** | Raccogli la bacchetta (E). In cabina: E vicino al generatore A, poi vicino al generatore D. Raccogli la chiave dall'altare. Entra in stiva e cammina sulle piastrelle 1 2 3 4 5, poi 3 1, poi 5 2 4 3. Raccogli la seconda chiave dall'incudine, poi E vicino all'incudine e "Usa: Chiave centrale". Sul ponte: E sulla porta della chela, poi "Usa: Chiave fusa". Entra. | Dopo il generatore D compare "Il flusso elettrico è completo! La barriera si è dissolta!"; dopo l'ultima piastrella "Il sistema della stiva si sblocca! La barriera si è dissolta!". All'incudine compare il testo della fusione. Alla fine sei nella stanza del granchio, con la chiave fusa ancora nell'inventario (I). |
| **A3** | Torna in cabina dopo aver preso la prima metà, poi in stiva dopo aver preso la seconda. Prova E vicino all'altare, a un generatore e all'incudine; ricammina sulle piastrelle. | Né sull'altare né sull'incudine c'è un'altra metà. Il generatore risponde "Il circuito è completo: i generatori restano accesi"; le piastrelle restano accese e non suonano. Nell'inventario c'è una sola chiave fusa. |
| **A4** | A metà partita, dopo aver aperto una porta finale, chiudi la finestra. Riapri e scegli "Riprendi". | Ricompari all'ingresso della stessa stanza, con gli stessi oggetti. La porta aperta è ancora aperta, e l'altra si può ancora aprire con la chiave fusa. |
| **A5** | Gioca fino a dare la bacchetta al granchio. Poi, da una partita nuova, all'angelo. | Prima il testo dell'azione, poi la schermata finale ("Finale 1 di 2 — Tutti salvi" o "Finale 2 di 2 — La nave esplode"). Riprendendo la partita torni sulla schermata finale, e non si può più giocare. |
| **A6** | A metà partita, Esc e poi "Ricomincia". Rispondi "No". Rifallo e rispondi "Sì". | Con "No" la partita resta com'era. Con "Sì" sei sul ponte all'inizio, senza oggetti, con la scena d'apertura. |
| **Due porte** | Con la chiave fusa, apri la porta della chela, poi quella dell'ala, ed entra in tutte e due. | Nessuna delle due chiede conferma, si aprono entrambe e la chiave fusa resta nell'inventario. Dare la bacchetta invece chiede conferma. |
| **Cancello** | Nuova partita. Cammina contro la porta in basso, quella della stiva. Poi prendi la prima metà della chiave e riprova. | Prima compare il testo del cancello, con l'incavo a mezza chiave, e resti sul ponte. Con la prima metà, la porta non ha più le sbarre ed entri. |
| **Mezza chiave** | Con le due metà non ancora fuse, E sulla porta della chela e "Usa: Chiave centrale". Poi, con una metà sola, prova a usarla sull'incudine. | Sulla porta compare che la metà va fusa all'incudine, e la porta resta chiusa. Sull'incudine compare che manca l'altra metà. |
| **Piastrelle** | Con l'audio acceso, in stiva: cammina su 1 e 2, poi sulla 4. Rifai 1 2 3 4 5. Esci dalla zona, rientra e cammina su 5. Poi 3 1, e 5 2 4 3. | Ogni piastrella giusta si accende con un "blip". La 4 fa "BZZZ": le piastrelle lampeggiano di rosso e si spengono. Con la 5 si sente il "ding" e compare "Fase 2: Il Ritorno", con la 5 che resta accesa. Uscendo dalla zona si sente di nuovo "BZZZ" e la 5 si spegne. Alla fine c'è la fanfara, compare il messaggio di vittoria, la barriera intorno all'incudine sparisce e si raccoglie la seconda chiave. |
| **Generatori** | Nuova partita, entra in cabina. Attiva B. Esci e rientra. Prova a raggiungere la chiave. Poi attiva A e D. | Con B si accendono A e D e si spegne B: lampade e cavi cambiano subito, con un "Clic!" che non blocca. Rientrando i generatori sono di nuovo come all'inizio (A e D spenti, B e C accesi). Finché c'è la barriera la chiave non si raggiunge. Con A e D la barriera sparisce. |

## 11. Altri test

- **Integrità dei dati** (`test_story_*`):
  - gli id sono unici;
  - ogni riferimento a stanze, oggetti e flag esiste;
  - ogni porta ha la sua porta di ritorno;
  - ogni porta con `requires` ha un `choice_flag`, e ogni porta con `opens_with` ha il suo `barred_text`;
  - ogni enigma ha un `done_text`;
  - ogni generatore sta in un solo circuito, nella sua stessa stanza, e i flag che inverte esistono;
  - ogni piastrella sta in un solo enigma a pavimento, nella sua stessa stanza, e ogni fase comincia dalla piastrella con cui finisce quella prima;
  - nessun testo è vuoto.
- **PT02 e PT04:** in ogni stanza e in vari momenti della partita si provano tutte le azioni di `actions_for`, più alcune impossibili. Le azioni accettate hanno un testo, quelle rifiutate una spiegazione.
- **R1:** ogni rifiuto lascia identici stanza, inventario e flag.
- **R2:** nessuna metà della chiave si raccoglie finché c'è la sua barriera, né da un'altra stanza.
- **Enigma dei generatori (M5):**
  - la configurazione iniziale;
  - ogni generatore inverte sé stesso e i due vicini, e attivarlo due volte lo annulla;
  - partendo da ognuna delle 16 configurazioni e attivando ogni generatore, il circuito si completa se e solo se si accendono tutti e quattro;
  - rientrando in cabina i generatori tornano come all'inizio, ma un circuito completo resta completo, anche dopo il salvataggio;
  - la barriera tiene la chiave fuori portata da ogni punto in cui il giocatore può stare (test del layout).
- **Enigma delle piastrelle (M5):**
  - ogni fase, passo per passo, con il nome della fase dopo nel testo;
  - un errore in ciascuna delle tre fasi fa ricominciare solo quella fase;
  - tornare sulla piastrella accesa per ultima, o uscire dalla zona senza luci accese, non cambia niente;
  - uscire dalla zona, o dalla stiva, a metà fase la fa ricominciare;
  - provando ogni piastrella in ogni momento, l'unica soluzione più corta è quella della consegna, e da ogni momento si può ancora vincere;
  - un salvataggio a metà fase si riprende identico, e uno con un momento impossibile viene rifiutato;
  - la zona contiene solo le piastrelle, e da ogni piastrella si arriva a ogni altra senza calpestarne una terza (test del layout);
  - i trigger: ogni piastrella scatta una volta per arrivo, comparire non è camminare, le piastrelle non sono solide e non sono bersagli di E;
  - ogni esito ha il suo suono e il suo testo nella striscia, la vittoria apre il riquadro, ogni esito accettato si salva;
  - dopo un errore le piastrelle lampeggiano di rosso, poi si spengono (controllato sui pixel);
  - le onde quadre dei suoni, e il gioco muto ma funzionante senza audio (`test_sounds.py`).
- **R4:**
  - i dati della storia sono identici dopo due partite complete;
  - un `new_game()` fatto dopo una partita è uguale al primo;
  - entrambi i finali si raggiungono da `new_game()`, anche senza leggere l'indizio del barile.
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

**Stato: fatta nel codice.** I due enigmi sono veri (§4): gli interruttori collegati in cabina e le piastrelle in stiva. La chiave è divisa in due metà, una per enigma, e la stiva è sbarrata finché non si ha la prima.
- **Test:** 216 verdi. Tra questi c'è una partita completa giocata solo con i tasti, piastrelle comprese, camminandoci sopra.
- **Bug inseriti apposta:** vengono scoperti tutti i 15 dei generatori, i 40 delle piastrelle e dei suoni, e i 13 dell'incudine, della chiave fusa e dei personaggi più grandi. Vengono ancora scoperti anche quelli delle milestone precedenti: 23 nel motore, 9 nel salvataggio, 15 di M3, 13 di M4 e 11 di M6.
- **Nel gioco vero:** una partita registrata senza finestra, camminando, fino al finale. I suoni sono partiti nell'ordine giusto.
- **Manca:** la checklist manuale (§10) sul gioco vero, e misurare se chi non conosce le soluzioni ci mette circa 10 minuti.

Il piano:
- **Enigmi:** si sostituiscono le reazioni placeholder. Se servono meccaniche nuove (sequenze, codici) si aggiungono condizioni al formato della reazione, oppure una funzione al motore, sempre scrivendo prima il test.
- **Test:** il contratto "risolvere un enigma = impostare un flag" resta lo stesso. Nei test cambiano solo i passi che risolvono gli enigmi.
- **Durata:** si aggiungono cose da esaminare, fino a circa 10 minuti di gioco.

*Fatto quando*: i test sono verdi con gli enigmi veri, e chi non conosce la soluzione finisce in circa 10 minuti.

### M6 — Grafica 8-bit

**Stato: fatta.**
- **Test:** 137 verdi. I file di test di M1–M4 non sono cambiati; i test nuovi sono in `test_graphics.py`.
- **Bug inseriti apposta:** gli 11 nella grafica vengono tutti scoperti, e così quelli di M3 (15) e M4 (13).
- **Velocità:** circa 1 ms per frame, misurato senza schermo, contro i 16,7 ms che bastano per i 60 fps.
- **Suoni:** non ci sono, erano facoltativi.

Gli sprite e il font sono originali, disegnati come testo: si modificano cambiando le lettere in `sprites.py` e `pixel_font.py`.

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
- **Indizio:** è facoltativo. Il barile della stiva aiuta a scegliere la porta, ma non serve per finire.
- **Enigma dei generatori:**
  - sostituisce il cassetto placeholder della cabina, e la chiave è diventata la "Chiave centrale";
  - la bacchetta non serve più per la chiave, ma serve ancora per la stiva e per il finale;
  - "configurazione iniziale all'ingresso nella stanza" vuol dire che i generatori tornano come all'inizio ogni volta che si entra in cabina dal ponte. Riprendendo una partita invece si ritrovano come sono stati salvati, perché si riprende lo stato salvato (A4);
  - a circuito completo i generatori restano accesi e non si attivano più;
  - la chiave si vede sull'altare da subito, dietro la barriera: si può esaminare, ma non raccogliere.
- **Le due metà della chiave e l'incudine:**
  - le metà si chiamano come nelle consegne, "Chiave centrale" (cabina) e "Seconda chiave" (stiva); fuse diventano la "Chiave fusa";
  - l'incudine prende il posto dello scrigno, dietro la stessa barriera, con sopra la seconda metà. Si fonde usando una delle due metà sull'incudine;
  - fondendo, le due metà spariscono dall'inventario: è l'unico caso in cui un oggetto si trasforma. La chiave fusa invece non si consuma, e apre entrambe le porte;
  - le porte finali non si sigillano più a vicenda, quindi aprirle non chiede conferma: la scelta che decide il finale è solo a chi dare la bacchetta. Il motore sa ancora sigillare porte che condividono un flag (c'è un test), ma nessuna lo fa;
  - un salvataggio delle versioni precedenti, con il vecchio flag `chosen_door`, non si riprende più: va iniziata una nuova partita.
- **Granchio e angelo:** cambia solo l'aspetto. Il granchio occupa 2×2 caselle, quattro volte l'area di prima; l'angelo 1×2, il doppio. Fanno e dicono le stesse cose.
- **Il cancello della stiva:** sta sulla porta del ponte che porta in stiva, quindi sbarra tutta la stiva, barile compreso. Si apre da solo appena hai la prima metà della chiave, senza doverla usare. La consegna dice sia "finché il primo enigma non è risolto" sia "una volta ottenuto il pezzo della chiave": vale la seconda, che in pratica coincide.
- **Enigma delle piastrelle:**
  - la Fase 2 e la Fase 3 partono con la prima piastrella già accesa, quella su cui il giocatore sta;
  - è un errore anche calpestare una piastrella accesa prima nella stessa fase, ma non quella accesa per ultima: tornarci sopra è solo un passo indietro;
  - una piastrella sbagliata quando non ce n'è nessuna accesa fa comunque "BZZZ". Uscire dalla zona senza luci accese invece non fa niente, perché è solo camminare;
  - riprendendo una partita salvata a metà fase, le luci restano come erano: si riprende lo stato salvato (A4);
  - i suoni sono fatti nel codice; oltre a "BZZZ" e al suono di conferma della consegna c'è un "blip" a ogni passo giusto e una fanfara alla vittoria. Solo questo enigma ha suoni;
  - per dare un indizio, i nomi delle fasi della consegna sono incisi sull'incudine e annunciati a ogni cambio di fase.
