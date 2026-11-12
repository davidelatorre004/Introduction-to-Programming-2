# Plot Twist — come giocare

Un breve gioco 8-bit, in inglese: ti svegli sul ponte di una nave alla deriva, con una bacchetta magica a terra lì vicino. Esplori la nave, risolvi due enigmi per rimettere insieme una chiave e alla fine scegli a chi affidare la bacchetta. Ci sono due finali.

Il gioco ha qualche effetto sonoro: tieni l'audio acceso.

Cosa è cambiato in ogni versione, in inglese: [CHANGELOG.md](CHANGELOG.md), con una pagina per versione nella cartella [versions](versions/).

## 1. Cosa ti serve

- **uv**, lo strumento che installa Python e pygame al posto tuo. Se l'hai già usato per il corso, sei a posto. Altrimenti installalo:
  - su Mac o Linux, nel terminale:
    ```
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
  - su Windows, in PowerShell:
    ```
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

  Poi chiudi e riapri il terminale.
- **Python** non serve installarlo a mano: se manca, uv scarica da solo la versione giusta (3.12).

## 2. Scarica il gioco

Il gioco è sul branch `claude/funny-ramanujan-ffrx60`. **Su `main` non c'è.** Il repository è privato: GitHub ti chiederà di accedere con il tuo account.

**Con git.** Nel terminale, dalla cartella dove vuoi mettere il gioco (va bene anche quella in cui si apre il terminale):
```
git clone -b claude/funny-ramanujan-ffrx60 https://github.com/davidelatorre004/Introduction-to-Programming-2.git
```
Si crea la cartella `Introduction-to-Programming-2`, già sul branch giusto.

Se invece il repository ce l'hai già sul computer, entra nella sua cartella e prendi il branch:
```
git fetch origin
git checkout claude/funny-ramanujan-ffrx60
```

**Senza git:**
1. Apri la [pagina del branch su GitHub](https://github.com/davidelatorre004/Introduction-to-Programming-2/tree/claude/funny-ramanujan-ffrx60).
2. Clicca il pulsante verde **Code**, poi **Download ZIP**.
3. Estrai lo ZIP.

## 3. Avvia il gioco

Dal terminale, entra nella cartella `plot_twist` (quella con `main.py`) e lancia il gioco. Se hai appena fatto `git clone`:
```
cd Introduction-to-Programming-2/plot_twist
uv run python main.py
```

Su Windows c'è una scorciatoia: apri la cartella `plot_twist` in Esplora file, scrivi `powershell` nella barra dell'indirizzo e premi Invio. Si apre PowerShell già in quella cartella.

La prima volta uv installa pygame: ci vuole qualche secondo. Poi si apre la finestra del gioco. Se i tasti non rispondono, clicca una volta sulla finestra.

## 4. I comandi

| Tasto | Cosa fa |
|---|---|
| Frecce o WASD | Muoverti |
| E | Interagire con ciò che hai vicino. Nei riquadri di testo, andare avanti |
| I | Aprire e chiudere l'inventario |
| Q | Lasciare a terra l'ultimo oggetto che hai preso, dove ti trovi. Chiunque può riprenderlo con E |
| Spazio | Usare l'abilità del personaggio (solo nelle partite a due, una volta per partita) |
| F11 | Schermo intero, e di nuovo F11 per tornare alla finestra |
| Esc | Il menu di pausa: Continue, Restart, Main menu, Quit |
| Su, giù e Invio (o E) | Scegliere nei menu |

Qualche aiuto:
- **Cosa fa E:** te lo dice la barra in alto, sulla seconda riga, per esempio "E: Pick up: Magic wand". E agisce solo su ciò che conta per la storia: vicino ai mobili (barili, casse, lanterne...) o lontano da tutto non fa nulla. Gli appunti appesi invece si leggono.
- **Più azioni possibili:** E apre un piccolo menu, per esempio Examine, "Use: …", "Give: …".
- **Porte:** per passare basta camminarci contro. Se una porta è chiusa, te lo dice.
- **Scelte definitive:** il gioco chiede conferma, con "No" già selezionato. Per confermare scegli "Yes".

### In due, su due computer

Si gioca in due su due computer collegati alla stessa rete (lo stesso Wi‑Fi). Ognuno ha il suo schermo e si muove per conto suo.

1. Sul primo computer: **New game**, poi **Host game for 2**, poi scegli il personaggio. Lo schermo mostra "Your address: …", per esempio `192.168.1.23`.
2. Sul secondo computer: **Join game**, scrivi quell'indirizzo (solo cifre e punti) e premi Invio.
3. La partita parte su tutti e due gli schermi.

Qualche aiuto:
- Ognuno ha il suo inventario. Per dare un oggetto all'altro, avvicinati a lui e premi E: "Give to partner: …".
- Esc apre il menu, ma il gioco non si ferma, perché l'altro continua a giocare. Main menu o Quit chiudono la partita per tutti e due.
- Il gioco si salva solo sul computer che ospita la partita. Per riprenderla, su quel computer scegli **Resume**; poi l'altro rientra con Join game.
- Se il secondo computer non trova la partita, controlla che i due computer siano sulla stessa rete. Controlla anche che il firewall del primo lasci entrare il gioco (porta 50555).

**I personaggi.** All'inizio scegli tra quattro personaggi. Da soli cambia solo l'aspetto. In due ognuno sceglie il suo sul proprio schermo (chi entra non può prendere quello dell'host), e ognuno ha un'abilità:

| Personaggio | Abilità |
|---|---|
| Wizard (Mago) | Spazio: il granchio resta stordito e fermo per 5 secondi, in qualunque stanza sia |
| Nurse (Infermiera) | Sempre attiva: rialza un compagno a terra in 1 secondo invece di 4 |
| Ghost (Fantasma) | Spazio: per 5 secondi il granchio non ti vede e va dall'altro giocatore. Se l'altro è a terra o fuori, il granchio scappa lontano da te |
| Flash | Spazio: uno scatto di 5 caselle nella direzione in cui guardi. Si ferma contro gli ostacoli e attraversa porte aperte e portali |

L'abilità con Spazio funziona una volta sola per partita: in basso a sinistra c'è scritto finché è disponibile. Se la usi mentre il granchio è ancora una statua, è sprecata.

**Il granchio (solo in due).** Appena risolvete la cabina, la statua del granchio sul ponte va in pezzi e ne esce il granchio, che vi dà la caccia. Le macerie restano lì fino alla fine.
- Insegue il giocatore più vicino ed è più lento di voi. Se nella sua stanza non c'è nessuno, vi segue attraverso le porte aperte.
- Se vi tocca, finite a terra e non potete muovervi. Il compagno ha un minuto per rialzarvi: deve stare vicino a voi e tenere premuto **E** per 4 secondi (la barra verde mostra quanto manca).
- Se nessuno vi rialza in tempo, siete fuori fino alla fine della partita, e i vostri oggetti passano al compagno. Da fuori guardate il compagno giocare.
- Se il granchio vi prende tutti e due, anche quando uno è già fuori, la partita è persa: è il terzo finale, "Caught by the crab".
- Una strategia: uno tiene occupato il granchio, l'altro risolve gli enigmi.
- Quando fondete le due metà della chiave, il granchio torna di pietra e svanisce in una nuvola di polvere.

## 5. Lo scopo (senza spoiler)

- Dal ponte si va in quattro stanze:
  - in alto, la cabina del capitano;
  - in basso, la stiva, chiusa da un cancello;
  - a destra e a sinistra, due porte chiuse a chiave.
- La chiave delle porte chiuse è spezzata in due metà: ogni enigma ne nasconde una. Le metà da sole non girano: vanno fuse su un'incudine, che compare solo dopo aver aiutato il dottore dell'infermeria.
- Con la chiave fusa si aprono tutte e due le porte. Dietro ognuna c'è qualcuno che vuole la tua bacchetta, e a chi la dai decide il finale.
- **Indizio per la cabina:** gli otto generatori sono collegati da cavi in un anello, e attivarne uno cambia anche i due vicini. Devi accenderli tutti insieme.
- **Indizio per l'infermeria:** il rimedio del dottore si fa con quattro fialette, in un ordine preciso. La prima è in infermeria; quando la raccogli, le altre compaiono in giro per la nave: cercale. Gli appunti del dottore dicono l'ordine.
- **La miniera:** il portale in fondo al corridoio porta in una miniera. In fondo alla miniera un secondo portale riporta sulla nave, ma solo all'andata.
- **Indizio per la stiva:** le cinque piastrelle numerate si calpestano, in tre prove una dopo l'altra. Una piastrella sbagliata, o uscire dalla grata intorno, fa ricominciare la prova in corso: "BZZZ!". I nomi delle prove sono incisi sulla barriera intorno all'altare in fondo alla stiva: esaminala.

## 6. Il salvataggio

- **Automatico:** il gioco salva da solo dopo ogni azione, quindi puoi chiudere la finestra quando vuoi.
- **Resume:** dal menu iniziale torni all'ingresso della stanza dove eri, con gli stessi oggetti e le stesse scelte.
- **New game:** se c'è già una partita salvata, chiede conferma prima di cancellarla.
- **Ripartire da zero:** in alternativa puoi cancellare il file `plot_twist/savegame.json`.

## 7. Se qualcosa non va

| Problema | Soluzione |
|---|---|
| `uv: command not found`, o "uv non è riconosciuto" | Installa uv (punto 1), poi chiudi e riapri il terminale |
| `'origin' does not appear to be a git repository`, o `pathspec ... did not match` | Non sei nella cartella del repository: scaricalo con `git clone` (punto 2), oppure entra nella sua cartella |
| `can't open file 'main.py'` | Non sei nella cartella giusta: entra in `plot_twist` |
| Non trovi la cartella `plot_twist` | Sei su `main`: fai `git checkout claude/funny-ramanujan-ffrx60` |
| La finestra non si vede | Cercala dietro le altre finestre, o nel Dock su Mac |

Per far girare i test automatici, dentro `plot_twist`:
```
uv run pytest
```

## 8. La soluzione

<details>
<summary>Attenzione, spoiler: clicca per vederla</summary>

1. Sul ponte, raccogli la bacchetta magica: vai sopra di lei e premi E.
2. Entra in cabina, dalla porta in alto.
   - Ogni generatore, quando lo attivi, inverte sé stesso e i due vicini nell'anello A, B, C, D, E, F, G, H.
   - Attiva **A** e poi **C**: si accendono tutti e otto e la barriera si dissolve.
   - Prendi la chiave dall'altare: è la "Central key".

   Se esci prima di finire, i generatori tornano come all'inizio.
3. Con la prima metà della chiave, il cancello della stiva si apre da solo. Entra dalla porta in basso.
   - Facoltativo: usa la bacchetta sul barile. Scopri un indizio, che poi rileggi nell'inventario.
   - Cammina sulle piastrelle, passando dalle corsie della grata per saltare quelle che non servono:
     - **The Wave:** 1, 2, 3, 4, 5;
     - **The Return**, partendo dalla 5 su cui sei: 3, 1;
     - **The Short Circuit**, partendo dalla 1 su cui sei: 5, 2, 4, 3.
   - La barriera sparisce: prendi la "Second key" dall'altare.
4. Dalla stiva entra in infermeria (porta a sinistra) e raccogli la fialetta verde. Le altre tre compaiono:
   - la **blu** nel corridoio, dalla porta in basso dell'infermeria;
   - la **rossa** in cambusa, a sinistra della cabina;
   - la **oro** in timoneria, dalla porta in alto della cabina.
5. Torna in infermeria. Vicino al calderone premi E e versa, in quest'ordine: **verde, rossa, oro, blu**. Se sbagli il calderone si svuota, ma le fialette restano a te: ricomincia dalla verde.
6. Raccogli il rimedio dal calderone e dallo al dottore ("Give: Remedy"). L'incudine compare al centro della stanza vuota a destra della cabina, tra scintille rosse: vicino all'incudine premi E e scegli "Use: Central key" (o la seconda). Le due metà diventano la "Fused key".
7. Torna sul ponte. Vicino alla porta a destra, quella con la chela, premi E e scegli "Use: Fused key". Entra.
8. Vicino al granchio premi E, scegli "Give: Magic wand" e poi "Yes": **Ending 1 of 2 — Everyone saved**.

Per l'altro finale apri anche la porta a sinistra, quella con l'ala (la chiave fusa apre tutte e due), e dai la bacchetta all'angelo: **Ending 2 of 2 — The ship explodes**.

Facoltativo: dal corridoio, alla fine, entra nel portale e arrivi nella miniera. Lì c'è un cuore di cristallo. Si usa nel momento in cui lo raccogli e poi sparisce: in due, rialza subito il compagno a terra o riporta in gioco quello eliminato (ricompare accanto a te). Se nessuno ne ha bisogno, o se giochi da solo, è sprecato: ce n'è uno solo per partita. Il portale in fondo alla miniera ti porta dritto in timoneria; quello della timoneria non riporta indietro.

</details>
