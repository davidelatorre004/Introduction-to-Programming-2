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
            "Da qui si va nella cabina del capitano e nella stiva; "
            "altre due porte sono chiuse a chiave."
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
            "Buio, casse rovesciate e odore di salsedine. "
            "In un angolo, un barile coperto di simboli."
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
    "key": {
        "name": "Chiave centrale",
        "description": "Una chiave d'ottone con l'impugnatura a forma di onda. Era custodita sull'altare della cabina.",
        "room": "cabin",
        "pos": (7, 1),  # on the altar, behind the barrier
        "appears_if": None,
        "free_if": "cabin_solved",
        "pickup_text": "Prendi la chiave centrale dall'altare.",
    },
}

# Doors, one per direction: each door is in one room and leads to another, from the
# middle of one wall ("side": N, S, E or W). The way back is on the opposite wall.
# A door that "requires" an item stays locked until that item is used on it.
# Opening it writes the door's id in its "choice_flag", and every other door
# sharing that flag is sealed forever. Only locked doors use the three texts.
DOORS = {
    "deck_to_cabin": {
        "room": "deck", "to": "cabin", "side": "N",
        "requires": None, "choice_flag": None,
        "locked_text": None, "sealed_text": None, "open_text": None,
    },
    "deck_to_hold": {
        "room": "deck", "to": "hold", "side": "S",
        "requires": None, "choice_flag": None,
        "locked_text": None, "sealed_text": None, "open_text": None,
    },
    "deck_to_crab": {
        "room": "deck", "to": "crab_room", "side": "E",
        "requires": "key", "choice_flag": "chosen_door",
        "locked_text": "Una porta con una chela incisa nel legno. È chiusa a chiave.",
        "sealed_text": "La serratura della porta con la chela si è fusa. Non si aprirà mai più.",
        "open_text": (
            "La chiave gira e la porta con la chela si apre. Dall'altra parte del ponte, "
            "la porta con l'ala si sigilla con uno schianto."
        ),
    },
    "deck_to_angel": {
        "room": "deck", "to": "angel_room", "side": "W",
        "requires": "key", "choice_flag": "chosen_door",
        "locked_text": "Una porta con un'ala incisa nel legno. È chiusa a chiave.",
        "sealed_text": "La serratura della porta con l'ala si è fusa. Non si aprirà mai più.",
        "open_text": (
            "La chiave gira e la porta con l'ala si apre. Dall'altra parte del ponte, "
            "la porta con la chela si sigilla con uno schianto."
        ),
    },
    "cabin_to_deck": {
        "room": "cabin", "to": "deck", "side": "S",
        "requires": None, "choice_flag": None,
        "locked_text": None, "sealed_text": None, "open_text": None,
    },
    "hold_to_deck": {
        "room": "hold", "to": "deck", "side": "N",
        "requires": None, "choice_flag": None,
        "locked_text": None, "sealed_text": None, "open_text": None,
    },
    "crab_to_deck": {
        "room": "crab_room", "to": "deck", "side": "W",
        "requires": None, "choice_flag": None,
        "locked_text": None, "sealed_text": None, "open_text": None,
    },
    "angel_to_deck": {
        "room": "angel_room", "to": "deck", "side": "E",
        "requires": None, "choice_flag": None,
        "locked_text": None, "sealed_text": None, "open_text": None,
    },
}

# The things that stand in the rooms. Each one stands on tile "pos" (and the
# tiles "size" covers, if it is bigger than one) and blocks the way. "kind" says
# what it does:
# - "puzzle" and "character" react when the player uses an item on them. A
#   reaction either sets a flag ("set_flag" and "value") or ends the game
#   ("ending"), and always has a "text". "done_text" replaces "look_text" once a
#   puzzle is solved.
# - "switch" is a generator of a circuit (see CIRCUITS): activating it flips the
#   flags in "toggles", its own included, and shows "toggle_text".
# - "barrier" stands in the way until its "open_if" flag is true, then it is gone.
# - "altar" is only there to be looked at, and to hold an item.
# PLACEHOLDER: the hold puzzle only asks for the wand. Its real version is still to come.
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
    "hold_puzzle": {
        "kind": "puzzle",
        "name": "Barile coperto di simboli",
        "room": "hold",
        "pos": (11, 7),
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
