# Plot Twist — come giocare

Un breve gioco 8-bit: ti svegli sul ponte di una nave alla deriva, con una bacchetta magica a terra lì vicino. Esplori la nave, risolvi un enigma e alla fine scegli a chi affidare la bacchetta. Ci sono due finali.

È una versione provvisoria: l'enigma della stiva è ancora un segnaposto.

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
| Esc | Il menu di pausa: Continua, Ricomincia, Menu principale, Esci |
| Su, giù e Invio (o E) | Scegliere nei menu |

Qualche aiuto:
- **Cosa fa E:** te lo dice la barra in alto, sulla seconda riga, per esempio "E: Raccogli: Bacchetta magica". Se vicino non c'è niente, E descrive la stanza.
- **Più azioni possibili:** E apre un piccolo menu, per esempio Esamina, "Usa: …", "Dai: …".
- **Porte:** per passare basta camminarci contro. Se una porta è chiusa, te lo dice.
- **Scelte definitive:** il gioco chiede conferma, con "No" già selezionato. Per confermare scegli "Sì".

## 5. Lo scopo (senza spoiler)

- Dal ponte si va in quattro stanze:
  - in alto, la cabina del capitano;
  - in basso, la stiva;
  - a destra e a sinistra, due porte chiuse a chiave.
- Esplora, raccogli quello che trovi e scopri come aprire le porte chiuse.
- Puoi aprire **una sola** delle due porte: l'altra si sigilla per sempre. Dietro ognuna c'è qualcuno che vuole la tua bacchetta, e a chi la dai decide il finale.
- **Indizio per la cabina:** i quattro generatori sono collegati da cavi, e attivarne uno cambia anche quelli collegati. Devi accenderli tutti insieme.

## 6. Il salvataggio

- **Automatico:** il gioco salva da solo dopo ogni azione, quindi puoi chiudere la finestra quando vuoi.
- **Riprendi:** dal menu iniziale torni all'ingresso della stanza dove eri, con gli stessi oggetti e le stesse scelte.
- **Nuova partita:** se c'è già una partita salvata, chiede conferma prima di cancellarla.
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
   - Ogni generatore, quando lo attivi, inverte sé stesso e i due vicini lungo i lati del quadrato.
   - Attiva **A** e poi **D**: si accendono tutti e quattro e la barriera si dissolve.
   - Prendi la Chiave centrale dall'altare.

   Se esci prima di finire, i generatori tornano come all'inizio.
3. Facoltativo: entra nella stiva, dalla porta in basso, e usa la bacchetta sul barile. Scopri un indizio, che poi rileggi nell'inventario.
4. Torna sul ponte. Vicino alla porta a destra, quella con la chela, premi E, scegli "Usa: Chiave centrale" e poi "Sì". Entra.
5. Vicino al granchio premi E, scegli "Dai: Bacchetta magica" e poi "Sì": **Finale 1 di 2 — Tutti salvi**.

Per l'altro finale, in una nuova partita apri la porta a sinistra, quella con l'ala, e dai la bacchetta all'angelo: **Finale 2 di 2 — La nave esplode**.

</details>
