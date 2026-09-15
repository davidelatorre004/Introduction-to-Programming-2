# -*- coding: utf-8 -*-
"""
PAGANTE - Surf & Split
=======================
App con interfaccia grafica (Tkinter) per splittare le spese di un viaggio
tra amici, in pieno stile surfista.

Logica di split (dal workflow "Pagante Payment Split Flow"):

    Nuovo pagamento -> [pagante, importo] -> chi e' coinvolto nella spesa?
        - Solo il pagante  -> spesa individuale, nessuno split
        - Tutto il crew    -> quota = importo / n_partecipanti
        - Split parziale   -> quota = importo / n_selezionati
    -> aggiorna i balance -> salva

Ogni tavola da surf mostra DUE numeri:
    QUOTA  = quanto di spesa e' stato allocato a quella persona (sempre >= 0).
             La somma delle quote = totale speso nel viaggio.
    SALDO  = credito/debito netto (pagante in credito per quanto ha anticipato
             agli altri, beneficiari in debito per la loro quota).
             La somma dei saldi = 0.

Dati tenuti solo in memoria: alla chiusura si riparte dai viaggi demo.
Nessuna dipendenza esterna: basta Python 3 con Tkinter.
"""

import math
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

# ---------------------------------------------------------------------------
# PALETTE OCEANICA
# ---------------------------------------------------------------------------
DEEP    = "#05445E"   # blu oceano profondo
OCEAN   = "#0A6E8A"   # blu oceano
AQUA    = "#189AB4"   # azzurro acqua
WATER   = "#75E6DA"   # acqua bassa
FOAM    = "#DFF4F3"   # schiuma / sfondo
SAND    = "#F7E5C6"   # sabbia
SAND_D  = "#DFC49A"   # sabbia bagnata (bordi)
SUNSET  = "#FF7B54"   # arancione tramonto (pulsanti)
SUNSET_D= "#E85F38"   # arancione hover
SUN     = "#FFB627"   # giallo sole
CORAL   = "#D64545"   # rosso corallo (debito)
PALM    = "#1E8F73"   # verde palma (credito)
MINT    = "#CFF0E4"   # tavola in credito
BLUSH   = "#FFDCD2"   # tavola in debito
INK     = "#04303F"   # testo scuro
WHITE   = "#FFFFFF"

FONT = "Segoe UI"

CUR = "$"


def money(v: float) -> str:
    """Formatta un importo con la valuta."""
    return f"{v:,.2f}{CUR}".replace(",", " ")


def signed(v: float) -> str:
    """Formatta un saldo con segno esplicito (+/-)."""
    if abs(v) < 0.005:
        return f"0.00{CUR}"
    return f"{'+' if v > 0 else '-'}{abs(v):,.2f}{CUR}".replace(",", " ")


# ---------------------------------------------------------------------------
# MODELLO DATI
# ---------------------------------------------------------------------------
class Payment:
    """Un singolo pagamento registrato nel viaggio."""

    TOTAL = "total"        # split su tutto il crew
    PARTIAL = "partial"    # split su un sottoinsieme
    SOLO = "solo"          # spesa individuale del pagante

    def __init__(self, payer, amount, description, beneficiaries, when=None):
        self.payer = payer
        self.amount = float(amount)
        self.description = description or "Spesa"
        self.beneficiaries = list(beneficiaries)
        self.when = when or datetime.now().strftime("%d/%m %H:%M")

    @property
    def share(self):
        """Quota individuale = importo / numero di beneficiari."""
        return self.amount / len(self.beneficiaries)

    def kind(self, crew_size):
        if len(self.beneficiaries) == 1 and self.beneficiaries[0] == self.payer:
            return self.SOLO
        if len(self.beneficiaries) == crew_size:
            return self.TOTAL
        return self.PARTIAL

    def kind_label(self, crew_size):
        k = self.kind(crew_size)
        if k == self.SOLO:
            return "🏄 Spesa personale"
        if k == self.TOTAL:
            return f"🌊 Split totale ({len(self.beneficiaries)})"
        return f"🔱 Split parziale ({len(self.beneficiaries)})"

    def advanced(self):
        """Quanto il pagante ha anticipato per gli altri (credito netto)."""
        return self.amount - (self.share if self.payer in self.beneficiaries else 0.0)


class Trip:
    """Un viaggio: un crew di amici e la lista dei pagamenti."""

    def __init__(self, name, emoji, participants, payments=None):
        self.name = name
        self.emoji = emoji
        self.participants = list(participants)
        self.payments = list(payments or [])

    # --- calcoli ---------------------------------------------------------
    def quotas(self):
        """Quanto di spesa e' stato allocato a ciascuno (sempre >= 0)."""
        q = {p: 0.0 for p in self.participants}
        for pay in self.payments:
            s = pay.share
            for b in pay.beneficiaries:
                if b in q:
                    q[b] += s
        return q

    def net(self):
        """Saldo netto credito(+)/debito(-). La somma fa sempre 0."""
        n = {p: 0.0 for p in self.participants}
        for pay in self.payments:
            if pay.payer in n:
                n[pay.payer] += pay.amount
            s = pay.share
            for b in pay.beneficiaries:
                if b in n:
                    n[b] -= s
        return n

    def paid_out(self):
        """Quanto ha materialmente tirato fuori di tasca ciascuno."""
        p = {x: 0.0 for x in self.participants}
        for pay in self.payments:
            if pay.payer in p:
                p[pay.payer] += pay.amount
        return p

    def total(self):
        return sum(p.amount for p in self.payments)

    def settlements(self):
        """Chi deve passare quanto a chi, con il minor numero di giri."""
        n = self.net()
        debtors = sorted([[k, -v] for k, v in n.items() if v < -0.01],
                         key=lambda x: -x[1])
        creditors = sorted([[k, v] for k, v in n.items() if v > 0.01],
                           key=lambda x: -x[1])
        out, i, j = [], 0, 0
        while i < len(debtors) and j < len(creditors):
            amt = min(debtors[i][1], creditors[j][1])
            out.append((debtors[i][0], creditors[j][0], amt))
            debtors[i][1] -= amt
            creditors[j][1] -= amt
            if debtors[i][1] < 0.01:
                i += 1
            if creditors[j][1] < 0.01:
                j += 1
        return out


def demo_trips():
    """Un paio di viaggi gia' pronti su spot da surf famosi."""
    t1 = Trip("Pipeline", "🌺", ["Kai Moana", "Luna Serra", "Tobia Rossi", "Aitana Vega"])
    t1.payments = [
        Payment("Kai Moana", 240.00, "Affitto shack fronte spiaggia",
                ["Kai Moana", "Luna Serra", "Tobia Rossi", "Aitana Vega"], "02/09 09:15"),
        Payment("Luna Serra", 68.40, "Spesa al mercato",
                ["Kai Moana", "Luna Serra", "Tobia Rossi", "Aitana Vega"], "02/09 11:40"),
        Payment("Tobia Rossi", 90.00, "Noleggio tavole (2 gg)",
                ["Tobia Rossi", "Aitana Vega"], "03/09 08:05"),
        Payment("Aitana Vega", 35.00, "Muta nuova tutta sua",
                ["Aitana Vega"], "03/09 16:20"),
        Payment("Kai Moana", 52.00, "Poke bowl al tramonto",
                ["Kai Moana", "Luna Serra", "Tobia Rossi"], "03/09 19:30"),
    ]

    t2 = Trip("Nazaré", "🌊", ["Marco Onda", "Sofia Brisa", "Diego Malibu"])
    t2.payments = [
        Payment("Sofia Brisa", 180.00, "Benzina + pedaggi furgone",
                ["Marco Onda", "Sofia Brisa", "Diego Malibu"], "05/09 07:00"),
        Payment("Marco Onda", 96.60, "Cena al porto",
                ["Marco Onda", "Sofia Brisa", "Diego Malibu"], "05/09 21:10"),
        Payment("Diego Malibu", 45.00, "Wax e leash di scorta",
                ["Marco Onda", "Diego Malibu"], "06/09 10:25"),
    ]

    t3 = Trip("Uluwatu", "🌴", ["Nico Reef", "Emma Tide", "Yuri Barrel", "Chiara Sunset", "Bruno Kelp"])
    t3.payments = [
        Payment("Nico Reef", 310.00, "Villa con piscina (3 notti)",
                ["Nico Reef", "Emma Tide", "Yuri Barrel", "Chiara Sunset", "Bruno Kelp"], "07/09 14:00"),
        Payment("Emma Tide", 74.50, "Scooter a noleggio",
                ["Emma Tide", "Yuri Barrel", "Chiara Sunset"], "07/09 18:45"),
    ]
    return [t1, t2, t3]


# ---------------------------------------------------------------------------
# WIDGET / HELPER GRAFICI
# ---------------------------------------------------------------------------
def _hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def vgradient(cv, x0, y0, x1, y1, c1, c2):
    """Disegna un gradiente verticale a strisce su un Canvas."""
    r1, g1, b1 = _hex2rgb(c1)
    r2, g2, b2 = _hex2rgb(c2)
    h = max(1, int(y1 - y0))
    for i in range(h):
        t = i / h
        col = "#%02x%02x%02x" % (int(r1 + (r2 - r1) * t),
                                 int(g1 + (g2 - g1) * t),
                                 int(b1 + (b2 - b1) * t))
        cv.create_line(x0, y0 + i, x1, y0 + i, fill=col)


def wave(cv, w, base, amp, period, phase, color, bottom):
    """Un'onda sinusoidale riempita fino al fondo del canvas."""
    pts = []
    x = 0
    while x <= w + 12:
        pts.extend([x, base + amp * math.sin(x / period + phase)])
        x += 12
    pts.extend([w + 12, bottom, -12, bottom])
    cv.create_polygon(pts, fill=color, outline="", smooth=True)


def surf_button(parent, text, command, bg=SUNSET, fg=WHITE, hover=SUNSET_D,
                font_size=11, bold=True, padx=18, pady=9):
    """Pulsante piatto in stile surf con effetto hover."""
    b = tk.Button(parent, text=text, command=command,
                  bg=bg, fg=fg, activebackground=hover, activeforeground=fg,
                  font=(FONT, font_size, "bold" if bold else "normal"),
                  relief="flat", bd=0, padx=padx, pady=pady,
                  cursor="hand2", highlightthickness=0)
    b.bind("<Enter>", lambda e: b.config(bg=hover))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b


def surf_entry(parent, width=24, font_size=11):
    return tk.Entry(parent, width=width, font=(FONT, font_size),
                    bg=WHITE, fg=INK, relief="flat", bd=0,
                    insertbackground=INK,
                    highlightthickness=2, highlightbackground=SAND_D,
                    highlightcolor=AQUA)


def card(parent, bg=SAND, border=SAND_D):
    return tk.Frame(parent, bg=bg, highlightthickness=2,
                    highlightbackground=border, highlightcolor=border)


class ScrollFrame(tk.Frame):
    """Contenitore scrollabile verticalmente. Usa .body come genitore."""

    def __init__(self, parent, bg=FOAM):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.body = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.body.bind("<Configure>", self._on_body)
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(self._win, width=e.width))
        # la rotellina agisce solo quando il mouse e' dentro
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._wheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")

    def _on_body(self, _=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _wheel(self, event):
        if self.canvas.bbox("all") is None:
            return
        _, y0, _, y1 = self.canvas.bbox("all")
        if (y1 - y0) <= self.canvas.winfo_height():
            return
        self.canvas.yview_scroll(int(-event.delta / 120), "units")


def draw_surfboard(cv, x, y, w, h, fill, outline, band=None):
    """Sagoma di tavola da surf stretta e affusolata (nose in alto, tail in basso)."""
    pts = [
        x + w * 0.50, y,                  # nose appuntito
        x + w * 0.72, y + h * 0.10,
        x + w * 0.95, y + h * 0.34,
        x + w * 1.00, y + h * 0.52,
        x + w * 0.94, y + h * 0.74,
        x + w * 0.74, y + h * 0.94,
        x + w * 0.62, y + h,              # tail squadrato
        x + w * 0.38, y + h,
        x + w * 0.26, y + h * 0.94,
        x + w * 0.06, y + h * 0.74,
        x + w * 0.00, y + h * 0.52,
        x + w * 0.05, y + h * 0.34,
        x + w * 0.28, y + h * 0.10,
    ]
    cv.create_polygon(pts, fill=fill, outline=outline, width=2, smooth=True)
    # stringer centrale
    cv.create_line(x + w * 0.5, y + h * 0.09, x + w * 0.5, y + h * 0.93,
                   fill=outline, width=1)
    # fasce decorative
    if band:
        for t in (0.42, 0.50):
            cv.create_line(x + w * 0.10, y + h * t, x + w * 0.90, y + h * t,
                           fill=band, width=4)
    # pinna
    cv.create_polygon(x + w * 0.50, y + h * 0.93,
                      x + w * 0.62, y + h * 1.06,
                      x + w * 0.50, y + h * 1.02,
                      fill=outline, outline="")


# ---------------------------------------------------------------------------
# APP
# ---------------------------------------------------------------------------
class SurfSplitApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("🏄 PAGANTE — Surf & Split")
        self.geometry("1200x820")
        self.minsize(1040, 700)
        self.configure(bg=FOAM)

        self.trips = demo_trips()
        self.current = None      # viaggio aperto
        self.me = None           # "chi sei" nel viaggio aperto

        self._init_styles()

        self.container = tk.Frame(self, bg=FOAM)
        self.container.pack(fill="both", expand=True)

        self.show_home()

    def _init_styles(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("Surf.TCombobox", fieldbackground=WHITE, background=SAND,
                     foreground=INK, arrowcolor=DEEP, bordercolor=SAND_D,
                     lightcolor=SAND_D, darkcolor=SAND_D, padding=5)
        st.map("Surf.TCombobox", fieldbackground=[("readonly", WHITE)],
               foreground=[("readonly", INK)])
        st.configure("Surf.Vertical.TScrollbar", background=WATER,
                     troughcolor=FOAM, bordercolor=FOAM,
                     arrowcolor=DEEP, darkcolor=WATER, lightcolor=WATER)
        st.configure("TScrollbar", background=WATER, troughcolor=FOAM,
                     bordercolor=FOAM, arrowcolor=DEEP)

    # -- gestione schermate ------------------------------------------------
    def _clear(self):
        self.unbind_all("<MouseWheel>")
        for w in self.container.winfo_children():
            w.destroy()

    # =====================================================================
    #  BANNER
    # =====================================================================
    def _banner(self, parent, title, subtitle, height=140, back=None):
        cv = tk.Canvas(parent, height=height, bg=DEEP, highlightthickness=0, bd=0)
        cv.pack(fill="x")

        def redraw(_=None):
            cv.delete("all")
            w = cv.winfo_width() or 1200
            h = height
            vgradient(cv, 0, 0, w, h + 2, "#0E5C7A", AQUA)      # cielo/oceano
            # il sole si sposta a sinistra se c'e' il pulsante "Torna a riva"
            sx = w - (330 if back else 110)
            cv.create_oval(sx - 30, 14, sx + 30, 74, fill=SUN, outline="")
            wave(cv, w, h * 0.56, 13, 88, 0.0, OCEAN, h + 8)
            wave(cv, w, h * 0.70, 11, 64, 1.6, AQUA, h + 8)
            wave(cv, w, h * 0.84, 8, 48, 3.1, WATER, h + 8)
            cv.create_text(34, h * 0.30, text=title, anchor="w",
                           font=(FONT, 26, "bold"), fill=WHITE)
            cv.create_text(36, h * 0.30 + 30, text=subtitle, anchor="w",
                           font=(FONT, 11), fill=FOAM)

        cv.bind("<Configure>", redraw)

        if back:
            b = surf_button(parent, "⬅  Torna a riva", back, bg=DEEP, hover=OCEAN,
                            font_size=10, padx=14, pady=6)
            b.place(in_=cv, relx=1.0, y=height - 34, x=-24, anchor="ne")
        return cv

    # =====================================================================
    #  SCHERMATA HOME
    # =====================================================================
    def show_home(self):
        self._clear()
        self.current, self.me = None, None
        root = tk.Frame(self.container, bg=FOAM)
        root.pack(fill="both", expand=True)

        self._banner(root, "🏄  PAGANTE",
                     "Spartisci il conto, cavalca l'onda  🤙  🌊  🌴")

        top = tk.Frame(root, bg=FOAM)
        top.pack(fill="x", padx=28, pady=(20, 6))
        tk.Label(top, text="🌴  I TUOI SURF TRIP", bg=FOAM, fg=DEEP,
                 font=(FONT, 16, "bold")).pack(side="left")
        surf_button(top, "🌊  NUOVA ONDA — crea un viaggio",
                    self.show_new_trip, font_size=12, padx=22, pady=11).pack(side="right")

        tk.Frame(root, bg=WATER, height=3).pack(fill="x", padx=28, pady=(8, 0))

        sf = ScrollFrame(root, bg=FOAM)
        sf.pack(fill="both", expand=True, padx=22, pady=14)

        if not self.trips:
            tk.Label(sf.body, text="Mare piatto…  nessun viaggio ancora. 🏝️\n"
                                   "Premi «NUOVA ONDA» e parti!",
                     bg=FOAM, fg=OCEAN, font=(FONT, 13), justify="center").pack(pady=60)
            return

        for trip in self.trips:
            self._trip_card(sf.body, trip)

    def _trip_card(self, parent, trip):
        c = card(parent)
        c.pack(fill="x", padx=6, pady=8)

        strip = tk.Frame(c, bg=AQUA, width=8)
        strip.pack(side="left", fill="y")

        inner = tk.Frame(c, bg=SAND)
        inner.pack(side="left", fill="both", expand=True, padx=16, pady=14)

        head = tk.Frame(inner, bg=SAND)
        head.pack(fill="x")
        tk.Label(head, text=f"{trip.emoji}  {trip.name}", bg=SAND, fg=DEEP,
                 font=(FONT, 16, "bold")).pack(side="left")
        tk.Label(head, text=f"🏄 {len(trip.participants)} surfisti", bg=SAND,
                 fg=OCEAN, font=(FONT, 10, "bold")).pack(side="left", padx=14)

        tk.Label(inner, text="Crew:  " + " · ".join(trip.participants),
                 bg=SAND, fg=INK, font=(FONT, 10), anchor="w",
                 wraplength=760, justify="left").pack(fill="x", pady=(8, 2))

        tk.Label(inner,
                 text=f"💰 Cassa comune: {money(trip.total())}     "
                      f"📜 {len(trip.payments)} pagamenti registrati",
                 bg=SAND, fg=OCEAN, font=(FONT, 10, "bold"),
                 anchor="w").pack(fill="x", pady=(2, 0))

        right = tk.Frame(c, bg=SAND)
        right.pack(side="right", fill="y", padx=18)
        surf_button(right, "CAVALCA  🤙", lambda t=trip: self.open_trip(t),
                    font_size=12, padx=20, pady=12).pack(expand=True)

    # =====================================================================
    #  SCHERMATA NUOVO VIAGGIO
    # =====================================================================
    def show_new_trip(self):
        self._clear()
        root = tk.Frame(self.container, bg=FOAM)
        root.pack(fill="both", expand=True)

        self._banner(root, "🌊  NUOVA ONDA",
                     "Dai un nome allo spot e chiama il crew",
                     height=120, back=self.show_home)

        wrap = tk.Frame(root, bg=FOAM)
        wrap.pack(fill="both", expand=True, padx=40, pady=24)

        # --- nome spot ---
        box1 = card(wrap)
        box1.pack(fill="x", pady=(0, 18))
        tk.Label(box1, text="🏝️  NOME DELLO SPOT", bg=SAND, fg=DEEP,
                 font=(FONT, 12, "bold")).pack(anchor="w", padx=18, pady=(14, 4))
        name_e = surf_entry(box1, width=44, font_size=13)
        name_e.pack(anchor="w", padx=18, pady=(0, 16), ipady=6)
        name_e.focus_set()

        # --- crew ---
        box2 = card(wrap)
        box2.pack(fill="both", expand=True)
        tk.Label(box2, text="🏄  IL CREW  (minimo 2 surfisti)", bg=SAND, fg=DEEP,
                 font=(FONT, 12, "bold")).pack(anchor="w", padx=18, pady=(14, 4))

        addrow = tk.Frame(box2, bg=SAND)
        addrow.pack(fill="x", padx=18, pady=(0, 10))
        p_e = surf_entry(addrow, width=30, font_size=12)
        p_e.pack(side="left", ipady=5)

        listwrap = tk.Frame(box2, bg=SAND)
        listwrap.pack(fill="both", expand=True, padx=18, pady=(0, 16))

        crew = []

        def render_crew():
            for w in listwrap.winfo_children():
                w.destroy()
            if not crew:
                tk.Label(listwrap, text="Nessuno a bordo… aggiungi i tuoi compagni d'onda 🤙",
                         bg=SAND, fg=OCEAN, font=(FONT, 10, "italic")).pack(anchor="w")
                return
            for i, n in enumerate(crew):
                chip = tk.Frame(listwrap, bg=WATER, highlightthickness=1,
                                highlightbackground=AQUA)
                chip.pack(side="left", padx=4, pady=4)
                tk.Label(chip, text=f"🏄 {n}", bg=WATER, fg=DEEP,
                         font=(FONT, 10, "bold")).pack(side="left", padx=(10, 4), pady=5)
                tk.Button(chip, text="✕", command=lambda k=i: (crew.pop(k), render_crew()),
                          bg=WATER, fg=CORAL, activebackground=WATER,
                          relief="flat", bd=0, cursor="hand2",
                          font=(FONT, 9, "bold")).pack(side="left", padx=(0, 8))

        def add_p(_=None):
            n = p_e.get().strip()
            if not n:
                return
            if n in crew:
                messagebox.showwarning("Ehi!", f"«{n}» è già sulla tavola. 🤙")
                return
            crew.append(n)
            p_e.delete(0, "end")
            render_crew()

        p_e.bind("<Return>", add_p)
        surf_button(addrow, "➕  Aggiungi al crew", add_p, bg=AQUA, hover=OCEAN,
                    font_size=10, padx=14, pady=7).pack(side="left", padx=10)
        render_crew()

        # --- azioni ---
        def create():
            name = name_e.get().strip()
            if not name:
                messagebox.showwarning("Manca il nome", "Dai un nome allo spot! 🏝️")
                return
            if len(crew) < 2:
                messagebox.showwarning("Crew troppo piccolo",
                                       "Servono almeno 2 surfisti per splittare. 🏄🏄")
                return
            t = Trip(name, "🏄", crew)
            self.trips.insert(0, t)
            self.open_trip(t)

        bar = tk.Frame(wrap, bg=FOAM)
        bar.pack(fill="x", pady=18)
        surf_button(bar, "🤙  VARA IL VIAGGIO", create,
                    font_size=13, padx=26, pady=12).pack(side="left")
        surf_button(bar, "Annulla", self.show_home, bg=SAND_D, hover="#CBB187",
                    fg=INK, font_size=11).pack(side="left", padx=12)

    # =====================================================================
    #  SCHERMATA VIAGGIO — "DIARIO DI BORDO"
    # =====================================================================
    def open_trip(self, trip):
        self.current = trip
        self.me = trip.participants[0]
        self._render_trip()

    def _render_trip(self):
        self._clear()
        trip = self.current
        root = tk.Frame(self.container, bg=FOAM)
        root.pack(fill="both", expand=True)

        self._banner(root, f"{trip.emoji}  {trip.name.upper()}",
                     "📖 Diario di bordo — ogni onda, ogni conto",
                     height=126, back=self.show_home)

        # ---- riga info crew ----
        info = tk.Frame(root, bg=DEEP)
        info.pack(fill="x")
        row = tk.Frame(info, bg=DEEP)
        row.pack(fill="x", padx=28, pady=10)

        tk.Label(row, text=f"🏄  CREW: {len(trip.participants)} surfisti",
                 bg=DEEP, fg=SUN, font=(FONT, 11, "bold")).pack(side="left")
        tk.Label(row, text="  ·  " + " · ".join(trip.participants),
                 bg=DEEP, fg=FOAM, font=(FONT, 10)).pack(side="left")
        tk.Label(row, text=f"💰 Cassa: {money(trip.total())}",
                 bg=DEEP, fg=WATER, font=(FONT, 11, "bold")).pack(side="right")

        # ---- "chi sei" ----
        merow = tk.Frame(root, bg=OCEAN)
        merow.pack(fill="x")
        mr = tk.Frame(merow, bg=OCEAN)
        mr.pack(fill="x", padx=28, pady=7)
        tk.Label(mr, text="🤙  Tu sei:", bg=OCEAN, fg=WHITE,
                 font=(FONT, 10, "bold")).pack(side="left")
        me_var = tk.StringVar(value=self.me)
        me_cb = ttk.Combobox(mr, textvariable=me_var, values=trip.participants,
                             state="readonly", width=24, style="Surf.TCombobox")
        me_cb.pack(side="left", padx=10)

        def change_me(_=None):
            self.me = me_var.get()
            self._render_trip()

        me_cb.bind("<<ComboboxSelected>>", change_me)

        # ---- corpo: colonna sinistra (scroll) + pannello destro ----
        body = tk.Frame(root, bg=FOAM)
        body.pack(fill="both", expand=True)

        left = ScrollFrame(body, bg=FOAM)
        left.pack(side="left", fill="both", expand=True, padx=(18, 6), pady=14)

        right = tk.Frame(body, bg=FOAM, width=360)
        right.pack(side="right", fill="y", padx=(6, 18), pady=14)
        right.pack_propagate(False)

        self._section_boards(left.body, trip)
        self._section_settle(left.body, trip)
        self._section_history(left.body, trip)
        self._panel_new_payment(right, trip)

    # ---- sezione TAVOLE / BALANCE ---------------------------------------
    def _section_boards(self, parent, trip):
        tk.Label(parent, text="🏄  LE TAVOLE DEL CREW  —  balance di ognuno",
                 bg=FOAM, fg=DEEP, font=(FONT, 14, "bold")).pack(anchor="w", pady=(2, 2))
        tk.Label(parent,
                 text="QUOTA = spesa allocata a quella persona   ·   "
                      "SALDO = credito (+) o debito (−) verso il crew",
                 bg=FOAM, fg=OCEAN, font=(FONT, 9, "italic")).pack(anchor="w", pady=(0, 10))

        quotas, nets, paid = trip.quotas(), trip.net(), trip.paid_out()

        grid = tk.Frame(parent, bg=FOAM)
        grid.pack(fill="x", pady=(0, 18))

        COLS = 3
        for i, p in enumerate(trip.participants):
            r, c = divmod(i, COLS)
            self._board_card(grid, p, quotas[p], nets[p], paid[p]).grid(
                row=r, column=c, padx=5, pady=5, sticky="nw")

    def _board_card(self, parent, person, quota, net, paid_out):
        """Riquadro sabbia con il balance di un surfista + tavola illustrata."""
        if net > 0.005:
            accent, badge, board = PALM, "IN CRESTA", MINT
        elif net < -0.005:
            accent, badge, board = CORAL, "SOTTO L'ONDA", BLUSH
        else:
            accent, badge, board = OCEAN, "IN PARI", WATER

        is_me = (person == self.me)
        c = tk.Frame(parent, bg=SAND, highlightthickness=3 if is_me else 2,
                     highlightbackground=SUN if is_me else SAND_D,
                     highlightcolor=SUN if is_me else SAND_D,
                     width=244, height=256)
        c.pack_propagate(False)

        tk.Frame(c, bg=accent, height=7).pack(fill="x")

        row = tk.Frame(c, bg=SAND)
        row.pack(fill="both", expand=True, padx=10, pady=9)

        # --- tavola da surf disegnata ---
        cv = tk.Canvas(row, width=52, height=168, bg=SAND,
                       highlightthickness=0, bd=0)
        cv.pack(side="left", padx=(2, 10))
        draw_surfboard(cv, 6, 4, 40, 152, board, DEEP, band=accent)

        # --- testi ---
        col = tk.Frame(row, bg=SAND)
        col.pack(side="left", fill="both", expand=True)

        name = person if len(person) <= 17 else person.split()[0]
        tk.Label(col, text=name, bg=SAND, fg=DEEP, font=(FONT, 12, "bold"),
                 anchor="w").pack(fill="x")

        sub = tk.Frame(col, bg=SAND)
        sub.pack(fill="x", pady=(0, 4))
        tk.Label(sub, text=badge, bg=SAND, fg=accent,
                 font=(FONT, 8, "bold"), anchor="w").pack(side="left")
        if is_me:
            tag = tk.Frame(sub, bg=SUN)
            tag.pack(side="left", padx=6)
            tk.Label(tag, text="TU", bg=SUN, fg=DEEP,
                     font=(FONT, 7, "bold")).pack(padx=5, pady=1)

        tk.Frame(col, bg=SAND_D, height=1).pack(fill="x", pady=3)

        tk.Label(col, text="QUOTA SPESA", bg=SAND, fg=OCEAN,
                 font=(FONT, 7, "bold"), anchor="w").pack(fill="x")
        tk.Label(col, text=money(quota), bg=SAND, fg=DEEP,
                 font=(FONT, 15, "bold"), anchor="w").pack(fill="x")

        tk.Frame(col, bg=SAND_D, height=1).pack(fill="x", pady=3)

        tk.Label(col, text="SALDO NETTO", bg=SAND, fg=OCEAN,
                 font=(FONT, 7, "bold"), anchor="w").pack(fill="x")
        tk.Label(col, text=signed(net), bg=SAND, fg=accent,
                 font=(FONT, 15, "bold"), anchor="w").pack(fill="x")

        tk.Label(col, text=f"di tasca sua: {money(paid_out)}", bg=SAND, fg=INK,
                 font=(FONT, 8), anchor="w").pack(fill="x", pady=(5, 0))
        return c

    # ---- sezione PAREGGIO CONTI -----------------------------------------
    def _section_settle(self, parent, trip):
        tk.Label(parent, text="🤙  CHI PASSA IL CONTO A CHI",
                 bg=FOAM, fg=DEEP, font=(FONT, 14, "bold")).pack(anchor="w", pady=(2, 8))

        box = card(parent, bg=WATER, border=AQUA)
        box.pack(fill="x", pady=(0, 18))
        s = trip.settlements()
        if not s:
            tk.Label(box, text="🌴  Tutti in pari, mare calmo. Nessuno deve niente a nessuno!",
                     bg=WATER, fg=DEEP, font=(FONT, 11, "bold")).pack(anchor="w",
                                                                      padx=16, pady=14)
        else:
            for d, c, a in s:
                line = tk.Frame(box, bg=WATER)
                line.pack(fill="x", padx=16, pady=6)
                tk.Label(line, text=f"▼ {d}", bg=WATER, fg=CORAL,
                         font=(FONT, 11, "bold")).pack(side="left")
                tk.Label(line, text="   passa   ", bg=WATER, fg=DEEP,
                         font=(FONT, 10)).pack(side="left")
                tk.Label(line, text=money(a), bg=WATER, fg=DEEP,
                         font=(FONT, 12, "bold")).pack(side="left")
                tk.Label(line, text="   a   ", bg=WATER, fg=DEEP,
                         font=(FONT, 10)).pack(side="left")
                tk.Label(line, text=f"▲ {c}", bg=WATER, fg=PALM,
                         font=(FONT, 11, "bold")).pack(side="left")

    # ---- sezione STORICO -------------------------------------------------
    def _section_history(self, parent, trip):
        tk.Label(parent, text="📜  DIARIO DI BORDO  —  storico dei pagamenti",
                 bg=FOAM, fg=DEEP, font=(FONT, 14, "bold")).pack(anchor="w", pady=(2, 8))

        if not trip.payments:
            e = card(parent)
            e.pack(fill="x", pady=(0, 20))
            tk.Label(e, text="Nessuna onda cavalcata finora. 🏄  "
                             "Registra il primo pagamento qui a fianco →",
                     bg=SAND, fg=OCEAN, font=(FONT, 11)).pack(padx=16, pady=18)
            return

        n = len(trip.participants)
        for idx in range(len(trip.payments) - 1, -1, -1):   # più recente in cima
            pay = trip.payments[idx]
            kind = pay.kind(n)
            accent = {Payment.SOLO: SUN, Payment.TOTAL: AQUA,
                      Payment.PARTIAL: SUNSET}[kind]

            c = card(parent)
            c.pack(fill="x", pady=6)
            tk.Frame(c, bg=accent, width=8).pack(side="left", fill="y")

            inner = tk.Frame(c, bg=SAND)
            inner.pack(side="left", fill="both", expand=True, padx=14, pady=12)

            r1 = tk.Frame(inner, bg=SAND)
            r1.pack(fill="x")
            tk.Label(r1, text=f"💸  {pay.description}", bg=SAND, fg=DEEP,
                     font=(FONT, 12, "bold")).pack(side="left")
            tk.Label(r1, text=f"   {money(pay.amount)}", bg=SAND, fg=SUNSET_D,
                     font=(FONT, 12, "bold")).pack(side="left")
            tk.Label(r1, text=pay.when, bg=SAND, fg=OCEAN,
                     font=(FONT, 9)).pack(side="right")

            r2 = tk.Frame(inner, bg=SAND)
            r2.pack(fill="x", pady=(6, 4))
            tk.Label(r2, text=f"🏄 Pagante: {pay.payer}", bg=SAND, fg=INK,
                     font=(FONT, 10, "bold")).pack(side="left")
            tk.Label(r2, text=f"   |   {pay.kind_label(n)}", bg=SAND, fg=accent,
                     font=(FONT, 10, "bold")).pack(side="left")
            if kind != Payment.SOLO:
                tk.Label(r2, text=f"   |   {money(pay.share)} a testa",
                         bg=SAND, fg=OCEAN, font=(FONT, 10)).pack(side="left")

            chips = tk.Frame(inner, bg=SAND)
            chips.pack(fill="x", pady=(4, 0))
            tk.Label(chips, text="Split:", bg=SAND, fg=OCEAN,
                     font=(FONT, 9, "bold")).pack(side="left", padx=(0, 6))
            for b in pay.beneficiaries:
                ch = tk.Frame(chips, bg=FOAM, highlightthickness=1,
                              highlightbackground=WATER)
                ch.pack(side="left", padx=3)
                tk.Label(ch, text=f"{b}  {money(pay.share)}", bg=FOAM, fg=DEEP,
                         font=(FONT, 9)).pack(padx=8, pady=3)

            adv = pay.advanced()
            if adv > 0.005:
                tk.Label(inner,
                         text=f"↳ {pay.payer} ha anticipato {money(adv)} per gli altri "
                              f"(credito)",
                         bg=SAND, fg=PALM, font=(FONT, 9, "italic")).pack(anchor="w",
                                                                          pady=(6, 0))
            else:
                tk.Label(inner,
                         text="↳ spesa 100% a carico del pagante, nessun credito",
                         bg=SAND, fg=OCEAN, font=(FONT, 9, "italic")).pack(anchor="w",
                                                                           pady=(6, 0))

            side = tk.Frame(c, bg=SAND)
            side.pack(side="right", fill="y", padx=10)
            tk.Button(side, text="🗑", command=lambda k=idx: self._del_payment(k),
                      bg=SAND, fg=CORAL, activebackground=SAND_D, relief="flat",
                      bd=0, cursor="hand2", font=(FONT, 12)).pack(expand=True)

        tk.Frame(parent, bg=FOAM, height=20).pack()

    def _del_payment(self, idx):
        pay = self.current.payments[idx]
        if messagebox.askyesno("Cancella onda",
                               f"Elimino «{pay.description}» ({money(pay.amount)})?"):
            self.current.payments.pop(idx)
            self._render_trip()

    # ---- PANNELLO NUOVO PAGAMENTO ---------------------------------------
    def _panel_new_payment(self, parent, trip):
        panel = card(parent, bg=SAND, border=SUNSET)
        panel.pack(fill="both", expand=True)

        head = tk.Frame(panel, bg=SUNSET)
        head.pack(fill="x", side="top")
        tk.Label(head, text="🌊  NUOVA ONDA", bg=SUNSET, fg=WHITE,
                 font=(FONT, 14, "bold")).pack(pady=9)

        # il pulsante viene impacchettato SUBITO in basso, cosi' resta
        # sempre visibile anche se il form sopra e' lungo
        footer = tk.Frame(panel, bg=SAND)
        footer.pack(fill="x", side="bottom")

        # area scrollabile per il form
        form_area = ScrollFrame(panel, bg=SAND)
        form_area.pack(fill="both", expand=True, side="top")
        panel_body = form_area.body

        pad = {"padx": 14}

        # --- pagante ---
        tk.Label(panel_body, text="CHI HA PAGATO?", bg=SAND, fg=DEEP,
                 font=(FONT, 10, "bold")).pack(anchor="w", pady=(10, 0), **pad)
        payer_var = tk.StringVar(value=self.me or trip.participants[0])
        ttk.Combobox(panel_body, textvariable=payer_var, values=trip.participants,
                     state="readonly", style="Surf.TCombobox").pack(
            fill="x", pady=(2, 8), **pad)

        # --- importo ---
        tk.Label(panel_body, text=f"IMPORTO TOTALE ({CUR})", bg=SAND, fg=DEEP,
                 font=(FONT, 10, "bold")).pack(anchor="w", **pad)
        amount_e = surf_entry(panel_body, font_size=13)
        amount_e.pack(fill="x", pady=(2, 8), ipady=4, **pad)

        # --- descrizione ---
        tk.Label(panel_body, text="PER COSA?", bg=SAND, fg=DEEP,
                 font=(FONT, 10, "bold")).pack(anchor="w", **pad)
        desc_e = surf_entry(panel_body, font_size=11)
        desc_e.pack(fill="x", pady=(2, 9), ipady=3, **pad)

        tk.Frame(panel_body, bg=SAND_D, height=2).pack(fill="x", padx=14, pady=(0, 8))

        # --- chi e' coinvolto ---
        tk.Label(panel_body, text="CHI È COINVOLTO NELLA SPESA?", bg=SAND, fg=DEEP,
                 font=(FONT, 10, "bold")).pack(anchor="w", **pad)

        mode = tk.StringVar(value="total")
        checks_frame = tk.Frame(panel_body, bg=FOAM, highlightthickness=1,
                                highlightbackground=WATER)
        check_vars = {}

        def radio(txt, val, sub):
            f = tk.Frame(panel_body, bg=SAND)
            f.pack(fill="x", padx=14, pady=(2, 0))
            tk.Radiobutton(f, text=txt, variable=mode, value=val, command=toggle,
                           bg=SAND, fg=INK, activebackground=SAND,
                           selectcolor=WATER, font=(FONT, 10, "bold"),
                           anchor="w", bd=0, highlightthickness=0,
                           cursor="hand2").pack(anchor="w")
            tk.Label(f, text="        " + sub, bg=SAND, fg=OCEAN,
                     font=(FONT, 8, "italic")).pack(anchor="w")

        def toggle():
            if mode.get() == "partial":
                checks_frame.pack(fill="x", padx=14, pady=(8, 0))
            else:
                checks_frame.pack_forget()

        radio("Tutto il crew", "total",
              f"split totale: importo ÷ {len(trip.participants)}")
        radio("Split parziale", "partial",
              "scegli tu chi partecipa alla spesa")
        radio("Solo il pagante", "solo",
              "spesa personale: nessuno split, resta 100% sua")

        for p in trip.participants:
            v = tk.BooleanVar(value=False)
            check_vars[p] = v
            tk.Checkbutton(checks_frame, text=p, variable=v,
                           bg=FOAM, fg=INK, activebackground=FOAM,
                           selectcolor=WHITE, font=(FONT, 10),
                           anchor="w", bd=0, highlightthickness=0,
                           cursor="hand2").pack(anchor="w", padx=8, pady=1)
        tk.Label(checks_frame, text="(il pagante può esserci o no)", bg=FOAM,
                 fg=OCEAN, font=(FONT, 8, "italic")).pack(anchor="w", padx=8, pady=(0, 6))

        tk.Frame(panel_body, bg=SAND, height=12).pack()

        # --- submit ---
        def submit(_=None):
            raw = amount_e.get().strip().replace(",", ".").replace(CUR, "")
            try:
                amount = float(raw)
            except ValueError:
                messagebox.showwarning("Importo strano",
                                       "Scrivi un importo valido, tipo 24.50 🤙")
                return
            if amount <= 0:
                messagebox.showwarning("Importo strano",
                                       "L'importo deve essere maggiore di zero. 🌊")
                return

            payer = payer_var.get()
            m = mode.get()
            if m == "total":
                bens = list(trip.participants)
            elif m == "solo":
                bens = [payer]
            else:
                bens = [p for p, v in check_vars.items() if v.get()]
                if not bens:
                    messagebox.showwarning("Crew vuoto",
                                           "Seleziona almeno un partecipante "
                                           "per lo split parziale. 🏄")
                    return

            desc = desc_e.get().strip() or "Spesa"
            trip.payments.append(Payment(payer, amount, desc, bens))
            self._render_trip()

        amount_e.bind("<Return>", submit)
        desc_e.bind("<Return>", submit)

        tk.Frame(footer, bg=SAND_D, height=2).pack(fill="x")
        surf_button(footer, "🤙  CAVALCA IL PAGAMENTO", submit,
                    font_size=12, pady=13).pack(fill="x", padx=14, pady=13)


if __name__ == "__main__":
    SurfSplitApp().mainloop()
