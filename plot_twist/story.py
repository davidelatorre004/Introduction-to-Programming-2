"""The story of Plot Twist: every room, item, door, object, ending and text of the game.

This file is only data. The rules that read it are in engine.py, and nothing here
changes while the game runs. Ids are English; what the player reads is Italian.
"""

# Where every new game starts.
START_ROOM = "deck"

# What the game remembers about the player's progress and choices, with the
# value each flag has at the start of a new game.
FLAGS = {
    # The four generators of the captain's cabin: True is on, False is off. The
    # puzzle starts with A off, B on, C on, D off, and goes back to that every
    # time the player walks into the cabin, until the circuit is complete.
    "generator_a": False,
    "generator_b": True,
    "generator_c": True,
    "generator_d": False,
    # All four generators were on at once: the barrier in the cabin has dissolved.
    "cabin_solved": False,
    # The numbered tiles of the hold: the phase being played (1, 2 or 3) and how
    # many tiles of its sequence are lit. Then all three phases are done: the
    # barrier around the chest has dissolved.
    "hold_phase": 1,
    "hold_step": 0,
    "hold_solved": False,
    # The hold puzzle is solved: the player has learned that the crab tells the truth.
    "crab_truthful": False,
    # Id of the final door the player opened. From then on the other one is sealed.
    "chosen_door": None,
}

# "outdoor" tells the screen to draw the sea around the room. "entry" is the tile
# (column, row) where the player appears when a game starts or resumes in the room.
# A room is 16 x 12 tiles, walls included: the floor goes from (1, 1) to (14, 10).
ROOMS = {
    "deck": {
        "name": "Ponte",
        "description": (
            "Il ponte di una nave alla deriva. Tutto intorno, solo oceano. "
            "Una porta dà sulla cabina del capitano e una sulla stiva; "
            "altre due hanno una serratura."
        ),
        "outdoor": True,
        "entry": (6, 5),
    },
    "cabin": {
        "name": "Cabina del capitano",
        "description": (
            "Carte nautiche sparse a terra e quattro generatori che ronzano ai lati di un quadrato, "
            "collegati da cavi. In fondo, una barriera di energia protegge un piccolo altare."
        ),
        "outdoor": False,
        "entry": (7, 9),
    },
    "hold": {
        "name": "Stiva",
        "description": (
            "Buio, casse rovesciate e odore di salsedine. Nel pavimento brillano cinque piastrelle "
            "numerate, dall'1 al 5. In fondo, uno scrigno avvolto da una barriera; "
            "in un angolo, un barile coperto di simboli."
        ),
        "outdoor": False,
        "entry": (7, 2),
    },
    "crab_room": {
        "name": "Stanza del granchio",
        "description": "Una stanza umida, piena di conchiglie. Un granchio enorme ti osserva in silenzio.",
        "outdoor": False,
        "entry": (2, 5),
    },
    "angel_room": {
        "name": "Stanza dell'angelo",
        "description": "Una stanza inondata di luce bianca. Al centro, un angelo ti sorride.",
        "outdoor": False,
        "entry": (13, 5),
    },
}

# Items the player can collect. An item lies in its room, on tile "pos", until it
# is picked up. If "appears_if" names a flag, it shows up only once that flag is true.
# If "free_if" names a flag, it can be seen but not picked up until that flag is true.
ITEMS = {
    "wand": {
        "name": "Bacchetta magica",
        "description": "Una bacchetta di legno scuro, tiepida al tatto. Sembra reagire a qualcosa di magico.",
        "room": "deck",
        "pos": (8, 6),
        "appears_if": None,
        "free_if": None,
        "pickup_text": "Raccogli la bacchetta magica. Una scintilla ti corre lungo il braccio.",
    },
    # The two halves of the key that opens the final doors.
    "key": {
        "name": "Chiave centrale",
        "description": "Metà di una chiave d'ottone, con l'impugnatura a forma di onda. Da sola non apre niente.",
        "room": "cabin",
        "pos": (7, 1),  # on the altar, behind the barrier
        "appears_if": None,
        "free_if": "cabin_solved",
        "pickup_text": (
            "Prendi la chiave centrale dall'altare: è solo metà di una chiave. "
            "Sotto coperta, il cancello della stiva cigola e si apre."
        ),
    },
    "second_key": {
        "name": "Seconda chiave",
        "description": "L'altra metà della chiave d'ottone. Combacia con la chiave centrale.",
        "room": "hold",
        "pos": (7, 10),  # in the chest, behind the barrier
        "appears_if": None,
        "free_if": "hold_solved",
        "pickup_text": (
            "Prendi la seconda chiave dallo scrigno. Combacia con la chiave centrale: "
            "insieme formano una chiave intera."
        ),
    },
}

# Doors, one per direction: each door is in one room and leads to another, from the
# middle of one wall ("side": N, S, E or W). The way back is on the opposite wall.
# - A door that "requires" items stays locked until one of them is used on it while
#   the player carries them all. Opening it writes the door's id in its
#   "choice_flag", and every other door sharing that flag is sealed forever. Only
#   locked doors use "locked_text", "sealed_text" and "open_text".
# - A door that "opens_with" an item is barred until the player carries that item,
#   and then it is simply open. "barred_text" says what bars it.
DOORS = {
    "deck_to_cabin": {
        "room": "deck", "to": "cabin", "side": "N",
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
    "deck_to_hold": {
        "room": "deck", "to": "hold", "side": "S",
        "requires": [], "choice_flag": None, "opens_with": "key",
        "locked_text": None, "sealed_text": None, "open_text": None,
        "barred_text": "Un cancello di ferro sbarra la porta della stiva. Al centro c'è un incavo a forma di mezza chiave.",
    },
    "deck_to_crab": {
        "room": "deck", "to": "crab_room", "side": "E",
        "requires": ["key", "second_key"], "choice_flag": "chosen_door", "opens_with": None,
        "locked_text": "Una porta con una chela incisa nel legno. È chiusa a chiave.",
        "sealed_text": "La serratura della porta con la chela si è fusa. Non si aprirà mai più.",
        "open_text": (
            "Unisci le due metà della chiave: combaciano. La chiave gira e la porta con la chela si apre. "
            "Dall'altra parte del ponte, la porta con l'ala si sigilla con uno schianto."
        ),
        "barred_text": None,
    },
    "deck_to_angel": {
        "room": "deck", "to": "angel_room", "side": "W",
        "requires": ["key", "second_key"], "choice_flag": "chosen_door", "opens_with": None,
        "locked_text": "Una porta con un'ala incisa nel legno. È chiusa a chiave.",
        "sealed_text": "La serratura della porta con l'ala si è fusa. Non si aprirà mai più.",
        "open_text": (
            "Unisci le due metà della chiave: combaciano. La chiave gira e la porta con l'ala si apre. "
            "Dall'altra parte del ponte, la porta con la chela si sigilla con uno schianto."
        ),
        "barred_text": None,
    },
    "cabin_to_deck": {
        "room": "cabin", "to": "deck", "side": "S",
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
    "hold_to_deck": {
        "room": "hold", "to": "deck", "side": "N",
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
    "crab_to_deck": {
        "room": "crab_room", "to": "deck", "side": "W",
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
    "angel_to_deck": {
        "room": "angel_room", "to": "deck", "side": "E",
        "requires": [], "choice_flag": None, "opens_with": None,
        "locked_text": None, "sealed_text": None, "open_text": None, "barred_text": None,
    },
}

# The things that stand in the rooms. Each one stands on tile "pos" (and the
# tiles "size" covers, if it is bigger than one) and blocks the way, except the
# tiles of the floor. "kind" says what it does:
# - "puzzle" and "character" react when the player uses an item on them. A
#   reaction either sets a flag ("set_flag" and "value") or ends the game
#   ("ending"), and always has a "text". "done_text" replaces "look_text" once a
#   puzzle is solved.
# - "switch" is a generator of a circuit (see CIRCUITS): activating it flips the
#   flags in "toggles", its own included, and shows "toggle_text".
# - "tile" is a numbered tile of a floor puzzle (see FLOOR_PUZZLES): the player
#   walks on it, and it lights up when stepped on in the right order.
# - "barrier" stands in the way until its "open_if" flag is true, then it is gone.
# - "altar" holds an item: the cabin's altar, the hold's chest.
# The barrel of the hold is still a simple puzzle: it only asks for the wand.
OBJECTS = {
    # The generators of the cabin, at the corners of a square: A top left, B top
    # right, C bottom left, D bottom right. Each one is wired to the two next to
    # it along the sides of the square, never to the one across.
    "generator_a": {
        "kind": "switch",
        "name": "Generatore A",
        "label": "A",
        "room": "cabin",
        "pos": (4, 4),
        "flag": "generator_a",
        "toggles": ["generator_a", "generator_b", "generator_c"],
        "toggle_text": "Clic! A, B e C cambiano stato.",
        "look_text": "Un generatore con una grossa leva. La targhetta dice «A».",
        "done_text": None,
        "reactions": {},
    },
    "generator_b": {
        "kind": "switch",
        "name": "Generatore B",
        "label": "B",
        "room": "cabin",
        "pos": (11, 4),
        "flag": "generator_b",
        "toggles": ["generator_b", "generator_a", "generator_d"],
        "toggle_text": "Clic! B, A e D cambiano stato.",
        "look_text": "Un generatore con una grossa leva. La targhetta dice «B».",
        "done_text": None,
        "reactions": {},
    },
    "generator_c": {
        "kind": "switch",
        "name": "Generatore C",
        "label": "C",
        "room": "cabin",
        "pos": (4, 7),
        "flag": "generator_c",
        "toggles": ["generator_c", "generator_a", "generator_d"],
        "toggle_text": "Clic! C, A e D cambiano stato.",
        "look_text": "Un generatore con una grossa leva. La targhetta dice «C».",
        "done_text": None,
        "reactions": {},
    },
    "generator_d": {
        "kind": "switch",
        "name": "Generatore D",
        "label": "D",
        "room": "cabin",
        "pos": (11, 7),
        "flag": "generator_d",
        "toggles": ["generator_d", "generator_b", "generator_c"],
        "toggle_text": "Clic! D, B e C cambiano stato.",
        "look_text": "Un generatore con una grossa leva. La targhetta dice «D».",
        "done_text": None,
        "reactions": {},
    },
    # The barrier fed by the generators, in front of the altar and around it.
    "barrier": {
        "kind": "barrier",
        "name": "Barriera di energia",
        "room": "cabin",
        "pos": (6, 1),
        "size": (3, 2),
        "open_if": "cabin_solved",
        "look_text": "Una barriera di energia crepita intorno all'altare. Sembra alimentata dai generatori.",
        "done_text": None,
        "reactions": {},
    },
    "altar": {
        "kind": "altar",
        "name": "Altare",
        "room": "cabin",
        "pos": (7, 1),
        "look_text": "Un piccolo altare di pietra, contro la parete in fondo alla cabina.",
        "done_text": None,
        "reactions": {},
    },
    # The numbered tiles of the hold, in a row across the floor, one tile apart:
    # the player can walk around them, inside the zone, to skip from one to another.
    "tile_1": {
        "kind": "tile",
        "name": "Piastrella 1",
        "label": "1",
        "room": "hold",
        "pos": (3, 5),
        "look_text": "Una piastrella di metallo con inciso il numero 1.",
        "done_text": None,
        "reactions": {},
    },
    "tile_2": {
        "kind": "tile",
        "name": "Piastrella 2",
        "label": "2",
        "room": "hold",
        "pos": (5, 5),
        "look_text": "Una piastrella di metallo con inciso il numero 2.",
        "done_text": None,
        "reactions": {},
    },
    "tile_3": {
        "kind": "tile",
        "name": "Piastrella 3",
        "label": "3",
        "room": "hold",
        "pos": (7, 5),
        "look_text": "Una piastrella di metallo con inciso il numero 3.",
        "done_text": None,
        "reactions": {},
    },
    "tile_4": {
        "kind": "tile",
        "name": "Piastrella 4",
        "label": "4",
        "room": "hold",
        "pos": (9, 5),
        "look_text": "Una piastrella di metallo con inciso il numero 4.",
        "done_text": None,
        "reactions": {},
    },
    "tile_5": {
        "kind": "tile",
        "name": "Piastrella 5",
        "label": "5",
        "room": "hold",
        "pos": (11, 5),
        "look_text": "Una piastrella di metallo con inciso il numero 5.",
        "done_text": None,
        "reactions": {},
    },
    # The barrier fed by the tiles, around the chest against the bottom wall.
    "hold_barrier": {
        "kind": "barrier",
        "name": "Barriera di energia",
        "room": "hold",
        "pos": (6, 9),
        "size": (3, 2),
        "open_if": "hold_solved",
        "look_text": (
            "Una barriera di energia avvolge lo scrigno. Sul bordo dello scrigno si legge: "
            "«L'Onda, Il Ritorno, Il Cortocircuito.»"
        ),
        "done_text": None,
        "reactions": {},
    },
    "chest": {
        "kind": "altar",
        "name": "Scrigno",
        "room": "hold",
        "pos": (7, 10),
        "look_text": "Uno scrigno di legno cerchiato di ferro.",
        "done_text": None,
        "reactions": {},
    },
    "hold_puzzle": {
        "kind": "puzzle",
        "name": "Barile coperto di simboli",
        "room": "hold",
        "pos": (12, 9),
        "look_text": "I simboli sul barile pulsano piano, come se aspettassero qualcosa.",
        "done_text": "I simboli sul barile formano una frase: «Il granchio non mente mai.»",
        "reactions": {
            "wand": {
                "set_flag": "crab_truthful",
                "value": True,
                "text": "Tocchi il barile con la bacchetta e i simboli si ricompongono: «Il granchio non mente mai.»",
            },
        },
    },
    "crab": {
        "kind": "character",
        "name": "Granchio",
        "room": "crab_room",
        "pos": (10, 5),
        "look_text": "«Dammi la bacchetta e porterò questa nave in salvo. Tutti quanti.»",
        "done_text": None,
        "reactions": {
            "wand": {
                "ending": "saved",
                "text": "Porgi la bacchetta al granchio, che la stringe tra le chele.",
            },
        },
    },
    "angel": {
        "kind": "character",
        "name": "Angelo",
        "room": "angel_room",
        "pos": (5, 5),
        "look_text": "«Affidami la bacchetta. Con me sarete tutti al sicuro.»",
        "done_text": None,
        "reactions": {
            "wand": {
                "ending": "explosion",
                "text": "Porgi la bacchetta all'angelo. Il suo sorriso si allarga.",
            },
        },
    },
}

# Circuits of generators. When every switch of a circuit is on at the same time,
# the circuit is complete: "solved_flag" becomes true and "solved_text" is shown.
# From then on its switches stay on. Until then, they go back to their starting
# value (in FLAGS) every time the player walks into "room".
CIRCUITS = {
    "cabin_circuit": {
        "room": "cabin",
        "switches": ["generator_a", "generator_b", "generator_c", "generator_d"],
        "solved_flag": "cabin_solved",
        "solved_text": "Il flusso elettrico è completo! La barriera si è dissolta!",
    },
}

# Floor puzzles: numbered tiles to walk on in a given order, one phase after the
# other. Each phase is a sequence of "steps" (tile ids):
# - walking onto the next tile of the sequence lights it up ("lit_text");
# - at the end of a phase, the next one starts from the tile the player stands
#   on, which stays lit ("phase_text"); after the last one, "solved_flag" becomes
#   true and "solved_text" is shown;
# - walking onto any other tile ("wrong_text"), or out of the "zone" around the
#   tiles ("left_text"), switches the lights off: the phase starts over from its
#   first tile. Stepping back onto the tile lit last changes nothing.
# "phase_flag" holds the phase being played, from 1; "step_flag" how many tiles
# of its sequence are lit. The "zone" (column, row, width and height in tiles) is
# for main.py: the engine only hears that the player walked out of it.
FLOOR_PUZZLES = {
    "hold_tiles": {
        "room": "hold",
        "zone": (2, 4, 11, 3),
        "phases": [
            {"name": "L'Onda", "steps": ["tile_1", "tile_2", "tile_3", "tile_4", "tile_5"]},
            {"name": "Il Ritorno", "steps": ["tile_5", "tile_3", "tile_1"]},
            {"name": "Il Cortocircuito", "steps": ["tile_1", "tile_5", "tile_2", "tile_4", "tile_3"]},
        ],
        "phase_flag": "hold_phase",
        "step_flag": "hold_step",
        "solved_flag": "hold_solved",
        # Short texts: they show in the banner while the player keeps walking.
        "lit_text": "Clic! Piastrella {label} accesa.",
        "phase_text": "Ding! Fase {number}: {name}.",
        "wrong_text": "BZZZ! Piastrella sbagliata.",
        "left_text": "BZZZ! Sei uscito dalle piastrelle.",
        "solved_text": "Il sistema della stiva si sblocca! La barriera si è dissolta!",
    },
}

# The endings. "good" lets the final screen pick its colors.
ENDINGS = {
    "saved": {
        "title": "Tutti salvi",
        "text": [
            "Il granchio batte la bacchetta sul ponte e il mare si calma.",
            "All'alba, all'orizzonte, compare una costa.",
            "La nave attracca: tutti a bordo sono salvi.",
        ],
        "good": True,
    },
    "explosion": {
        "title": "La nave esplode",
        "text": [
            "L'angelo spezza la bacchetta in due.",
            "Una luce accecante, poi un boato.",
            "Della nave resta solo fumo sull'acqua.",
        ],
        "good": False,
    },
}

# Clues shown in the inventory once their flag is true.
CLUES = {
    "crab_truthful": "Il granchio non mente mai.",
}

# Texts that do not belong to a single room, item, door or object.
MESSAGES = {
    # The opening scene, shown when a new game starts.
    "intro": (
        "Ti svegli sul ponte di una nave alla deriva. Non ricordi come ci sei arrivato. "
        "Accanto a te, a terra, brilla una bacchetta."
    ),
    # The question asked before a new game replaces existing progress.
    "confirm_restart": "C'è già una partita salvata. Vuoi ricominciare da capo? I progressi andranno persi.",
    # Explanations of refused actions.
    "game_over": "La storia è finita: puoi rivedere il finale o iniziare una nuova partita.",
    "not_here": "Non è qui.",
    "already_have": "È già nel tuo inventario.",
    "no_item": "Non hai quell'oggetto.",
    "already_open": "È già aperta.",
    "already_done": "L'hai già fatto.",
    "nothing_happens": "Non succede niente.",
    "guarded": "La barriera ti impedisce di prenderla.",
    "circuit_done": "Il circuito è completo: i generatori restano accesi.",
    "missing_item": "Da sola non gira: a questa chiave manca l'altra metà.",
    "already_lit": "La piastrella è già accesa.",
    "tiles_done": "Le piastrelle restano accese: il sistema della stiva è sbloccato.",
    # What an open door shows when examined.
    "door_open": "Una porta aperta verso: {room}.",
    # Labels of the actions offered by the E key.
    "label_pick_up": "Raccogli: {item}",
    "label_enter": "Entra: {room}",
    "label_look_around": "Guarda intorno",
    "label_examine": "Esamina",
    "label_talk": "Parla",
    "label_use": "Usa: {item}",
    "label_give": "Dai: {item}",
    "label_activate": "Attiva: {name}",
    # The window title and the menus.
    "title": "Plot Twist",
    "subtitle": "Un mistero in mezzo al mare",
    "menu_new_game": "Nuova partita",
    "menu_resume": "Riprendi",
    "menu_quit": "Esci",
    "menu_continue": "Continua",
    "menu_restart": "Ricomincia",
    "menu_main_menu": "Menu principale",
    "menu_yes": "Sì",
    "menu_no": "No",
    "pause": "Pausa",
    "hint_inventory": "I: inventario",
    # The controls, at the bottom of the title screen: one line each.
    "controls_1": "Frecce o WASD: muoviti · E: interagisci",
    "controls_2": "I: inventario · Esc: menu",
    "ending_number": "Finale {number} di {total}",
    # What E does here, shown in the bar at the top.
    "prompt": "E: {action}",
    # How a door is called in that hint.
    "door": "Porta",
    # Asked before an action that cannot be undone.
    "confirm_choice": "«{action}»: sei sicuro? Non si potrà tornare indietro.",
    # The inventory screen.
    "inventory": "Inventario",
    "inventory_empty": "Non hai ancora raccolto niente.",
    "clues": "Indizi",
    "close_hint": "I o Esc per chiudere",
    # Shown if the save file cannot be written (for example, the disk is full).
    "save_failed": "Non riesco a salvare la partita: i progressi da qui in poi potrebbero andare persi.",
}
