"""The story of Plot Twist: every room, item, door, object, ending and text of the game.

This file is only data. The rules that read it are in engine.py, and nothing here
changes while the game runs. Ids are English; what the player reads is Italian.
"""

# Where every new game starts.
START_ROOM = "deck"

# What the game remembers about the player's progress and choices, with the
# value each flag has at the start of a new game.
FLAGS = {
    # The cabin puzzle is solved: the key appears in the cabin.
    "cabin_solved": False,
    # The hold puzzle is solved: the player has learned that the crab tells the truth.
    "crab_truthful": False,
    # Id of the final door the player opened. From then on the other one is sealed.
    "chosen_door": None,
}

# "outdoor" tells the screen to draw the sea around the room.
ROOMS = {
    "deck": {
        "name": "Ponte",
        "description": (
            "Il ponte di una nave alla deriva. Tutto intorno, solo oceano. "
            "Da qui si va nella cabina del capitano e nella stiva; "
            "altre due porte sono chiuse a chiave."
        ),
        "outdoor": True,
    },
    "cabin": {
        "name": "Cabina del capitano",
        "description": (
            "Carte nautiche sparse a terra e una lanterna spenta. "
            "Sulla scrivania, un cassetto chiuso da un sigillo che brilla."
        ),
        "outdoor": False,
    },
    "hold": {
        "name": "Stiva",
        "description": (
            "Buio, casse rovesciate e odore di salsedine. "
            "In un angolo, un barile coperto di simboli."
        ),
        "outdoor": False,
    },
    "crab_room": {
        "name": "Stanza del granchio",
        "description": "Una stanza umida, piena di conchiglie. Un granchio enorme ti osserva in silenzio.",
        "outdoor": False,
    },
    "angel_room": {
        "name": "Stanza dell'angelo",
        "description": "Una stanza inondata di luce bianca. Al centro, un angelo ti sorride.",
        "outdoor": False,
    },
}

# Items the player can collect. An item lies in its room until it is picked up.
# If "appears_if" names a flag, the item shows up only once that flag is true.
ITEMS = {
    "wand": {
        "name": "Bacchetta magica",
        "description": "Una bacchetta di legno scuro, tiepida al tatto. Sembra reagire a qualcosa di magico.",
        "room": "deck",
        "appears_if": None,
        "pickup_text": "Raccogli la bacchetta magica. Una scintilla ti corre lungo il braccio.",
    },
    "key": {
        "name": "Chiave d'ottone",
        "description": "Una chiave d'ottone con l'impugnatura a forma di onda.",
        "room": "cabin",
        "appears_if": "cabin_solved",
        "pickup_text": "Prendi la chiave d'ottone.",
    },
}

# Doors, one per direction: each door is in one room and leads to another.
# A door that "requires" an item stays locked until that item is used on it.
# Opening it writes the door's id in its "choice_flag", and every other door
# sharing that flag is sealed forever. Only locked doors use the three texts.
DOORS = {
    "deck_to_cabin": {
        "room": "deck", "to": "cabin",
        "requires": None, "choice_flag": None,
        "locked_text": None, "sealed_text": None, "open_text": None,
    },
    "deck_to_hold": {
        "room": "deck", "to": "hold",
        "requires": None, "choice_flag": None,
        "locked_text": None, "sealed_text": None, "open_text": None,
    },
    "deck_to_crab": {
        "room": "deck", "to": "crab_room",
        "requires": "key", "choice_flag": "chosen_door",
        "locked_text": "Una porta con una chela incisa nel legno. È chiusa a chiave.",
        "sealed_text": "La serratura della porta con la chela si è fusa. Non si aprirà mai più.",
        "open_text": (
            "La chiave gira e la porta con la chela si apre. Dall'altra parte del ponte, "
            "la porta con l'ala si sigilla con uno schianto."
        ),
    },
    "deck_to_angel": {
        "room": "deck", "to": "angel_room",
        "requires": "key", "choice_flag": "chosen_door",
        "locked_text": "Una porta con un'ala incisa nel legno. È chiusa a chiave.",
        "sealed_text": "La serratura della porta con l'ala si è fusa. Non si aprirà mai più.",
        "open_text": (
            "La chiave gira e la porta con l'ala si apre. Dall'altra parte del ponte, "
            "la porta con la chela si sigilla con uno schianto."
        ),
    },
    "cabin_to_deck": {
        "room": "cabin", "to": "deck",
        "requires": None, "choice_flag": None,
        "locked_text": None, "sealed_text": None, "open_text": None,
    },
    "hold_to_deck": {
        "room": "hold", "to": "deck",
        "requires": None, "choice_flag": None,
        "locked_text": None, "sealed_text": None, "open_text": None,
    },
    "crab_to_deck": {
        "room": "crab_room", "to": "deck",
        "requires": None, "choice_flag": None,
        "locked_text": None, "sealed_text": None, "open_text": None,
    },
    "angel_to_deck": {
        "room": "angel_room", "to": "deck",
        "requires": None, "choice_flag": None,
        "locked_text": None, "sealed_text": None, "open_text": None,
    },
}

# Puzzles and characters: things that react when the player uses an item on them.
# A reaction either sets a flag ("set_flag" and "value") or ends the game
# ("ending"), and always has a "text" for the player. "done_text" replaces
# "look_text" once a puzzle is solved.
# PLACEHOLDER: for now both puzzles only ask for the wand. The real ones come in M5.
OBJECTS = {
    "cabin_puzzle": {
        "kind": "puzzle",
        "name": "Cassetto sigillato",
        "room": "cabin",
        "look_text": "Un cassetto chiuso da un sigillo luminoso. Non c'è serratura: forse serve la magia.",
        "done_text": "Il cassetto è aperto. Del sigillo non resta traccia.",
        "reactions": {
            "wand": {
                "set_flag": "cabin_solved",
                "value": True,
                "text": "Punti la bacchetta sul sigillo: si spezza e il cassetto si apre. Dentro c'è una chiave!",
            },
        },
    },
    "hold_puzzle": {
        "kind": "puzzle",
        "name": "Barile coperto di simboli",
        "room": "hold",
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
}
