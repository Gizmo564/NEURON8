#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  NEURON 8 — Core Engine                                          ║
║  Shared neural network, state systems, utilities & UI panels     ║
║  All apps in the Neuron 8 suite import from this module          ║
╚══════════════════════════════════════════════════════════════════╝
"""

import sys, subprocess, importlib.util, os, datetime, math, random, json, re, platform

def _validate_deps():
    REQUIRED = [('numpy','numpy'), ('PIL','Pillow'), ('matplotlib','matplotlib')]
    missing  = [(mod, pkg) for mod, pkg in REQUIRED if importlib.util.find_spec(mod) is None]
    if not missing: return
    print(f"[Neuron8] Missing: {[p for _,p in missing]}. Installing...")
    try:
        for _, pkg in missing:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', pkg])
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        import tkinter as _tk; from tkinter import messagebox as _mb
        _r = _tk.Tk(); _r.withdraw()
        _mb.showerror("Missing Dependencies",
            f"Auto-install failed: {e}\n\nPlease run: pip install numpy Pillow matplotlib")
        _r.destroy(); sys.exit(1)

_validate_deps()

import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading, queue, time, glob

plt.rcParams.update({
    'figure.facecolor': '#0f0f1a', 'axes.facecolor': '#1a1a2e',
    'axes.edgecolor': '#555577',   'text.color': '#e0e0f0',
    'axes.labelcolor': '#e0e0f0',  'xtick.color': '#9090b0',
    'ytick.color': '#9090b0',
})

# ─────────────────────────────────────────────────────────────
#  Colour Palette
# ─────────────────────────────────────────────────────────────
BG   = '#0f0f1a'
BG2  = '#1a1a2e'
BG3  = '#252545'
BG4  = '#2e2e50'
FG   = '#e0e0f0'
FG2  = '#9090b0'
ACN  = '#7b8cde'
GRN  = '#a6e3a1'
RED  = '#f38ba8'
YEL  = '#f9e2af'
PRP  = '#cba6f7'
CYN  = '#89dceb'
ORG  = '#fab387'
HISTORY_LIMIT = 5

# ─────────────────────────────────────────────────────────────
#  Autosave directory (platform-aware)
# ─────────────────────────────────────────────────────────────
def get_autosave_dir() -> str:
    """Return (and create if needed) the per-user autosave directory."""
    sys_name = platform.system()
    if sys_name == 'Windows':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    elif sys_name == 'Darwin':
        base = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support')
    else:                          # Linux / BSD / everything else
        base = os.environ.get('XDG_DATA_HOME', os.path.join(os.path.expanduser('~'), '.local', 'share'))
    d = os.path.join(base, 'neuron8', 'autosave')
    os.makedirs(d, exist_ok=True)
    return d

# ─────────────────────────────────────────────────────────────
#  Cross-platform window maximise
# ─────────────────────────────────────────────────────────────
def maximize_window(root: tk.Tk) -> None:
    """Maximise *root* on any platform."""
    sys_name = platform.system()
    try:
        if sys_name == 'Windows':
            root.state('zoomed')
        elif sys_name == 'Darwin':
            root.attributes('-fullscreen', False)  # macOS: no reliable zoomed
            root.state('zoomed')
        else:  # Linux / X11 / Wayland via XWayland
            root.attributes('-zoomed', True)
    except Exception:
        pass   # fail silently; user can still resize manually

def setup_maximize_button(root: tk.Tk, header_frame: tk.Frame,
                          accent: str = ACN) -> None:
    """Add a tiny ⤢ / ⤡ toggle button to *header_frame* for Linux-friendly maximise."""
    _state = {'zoomed': False}

    def _toggle():
        sys_name = platform.system()
        if _state['zoomed']:
            _state['zoomed'] = False
            btn.config(text='⤢')
            try:
                if sys_name == 'Windows': root.state('normal')
                elif sys_name == 'Linux': root.attributes('-zoomed', False)
                else: root.state('normal')
            except Exception: pass
        else:
            _state['zoomed'] = True
            btn.config(text='⤡')
            try:
                if sys_name == 'Windows': root.state('zoomed')
                elif sys_name == 'Linux': root.attributes('-zoomed', True)
                else: root.state('zoomed')
            except Exception: pass

    btn = tk.Button(header_frame, text='⤢', command=_toggle,
                    bg=BG2, fg=FG2, font=("Courier", 10), relief='flat',
                    cursor='hand2', padx=6, pady=0, bd=0, highlightthickness=0,
                    activebackground=BG3, activeforeground=accent)
    btn.pack(side=tk.RIGHT, padx=(0, 4))
    btn.bind('<Enter>', lambda e: btn.config(fg=accent))
    btn.bind('<Leave>', lambda e: btn.config(fg=FG2))

# ─────────────────────────────────────────────────────────────
#  Autosave indicator (shared helper)
# ─────────────────────────────────────────────────────────────
def make_autosave_indicator(parent: tk.Frame, accent: str = ACN) -> tk.Label:
    """Return a small label for the header bar.  Call flash_autosave_indicator()
    on it whenever a background save completes."""
    lbl = tk.Label(parent, text='○ autosave', bg=BG2, fg=BG4,
                   font=("Courier", 7), padx=6)
    lbl.pack(side=tk.RIGHT, padx=2)
    lbl._accent = accent   # stash for flash
    return lbl

def flash_autosave_indicator(lbl: tk.Label, msg: str = 'saving…') -> None:
    """Briefly highlight *lbl* then dim it back."""
    if lbl is None: return
    try:
        lbl.config(text=f'● {msg}', fg=lbl._accent)
        lbl.after(1800, lambda: lbl.config(text='○ autosave', fg=BG4))
    except Exception: pass

# ─────────────────────────────────────────────────────────────
#  Startup backup warning dialog
# ─────────────────────────────────────────────────────────────
def show_startup_warning(root: tk.Tk, app_name: str, accent: str, message: str) -> None:
    """Modal warning shown once per app (or each launch if user doesn't tick 'don't show again').
    Preference is stored as a flag file in the autosave directory."""
    pref_file = os.path.join(get_autosave_dir(), f'{app_name.lower()}_warned.flag')
    if os.path.exists(pref_file):
        return

    dlg = tk.Toplevel(root)
    dlg.title(f"⚠  {app_name} — Important Notice")
    dlg.configure(bg=BG2)
    dlg.resizable(False, False)
    dlg.grab_set()
    dlg.transient(root)

    # Warning icon + title
    tk.Label(dlg, text="⚠", bg=BG2, fg=YEL,
             font=("Courier", 28), pady=(8)).pack()
    tk.Label(dlg, text=f"{app_name}", bg=BG2, fg=accent,
             font=("Courier", 13, "bold")).pack()
    tk.Label(dlg, text="Backup Reminder", bg=BG2, fg=FG2,
             font=("Courier", 9, "italic"), pady=2).pack()

    tk.Frame(dlg, bg=BG4, height=1).pack(fill='x', padx=20, pady=8)

    tk.Label(dlg, text=message, bg=BG2, fg=FG,
             font=("Courier", 9), wraplength=420, justify='left',
             padx=24, pady=4).pack(fill='x')

    tk.Frame(dlg, bg=BG4, height=1).pack(fill='x', padx=20, pady=8)

    dont_var = tk.BooleanVar(value=False)
    tk.Checkbutton(dlg, text="Don't show this warning again",
                   variable=dont_var, bg=BG2, fg=FG2,
                   selectcolor=BG3, font=("Courier", 8),
                   activebackground=BG2).pack(pady=(0, 6))

    def _proceed():
        if dont_var.get():
            try:
                with open(pref_file, 'w') as f: f.write('1')
            except Exception: pass
        dlg.destroy()

    Btn(dlg, "  I understand — Open " + app_name + "  ",
        cmd=_proceed, color=accent, fg=BG,
        font=("Courier", 10, "bold"), pady=8).pack(pady=(0, 16))

    # Centre on parent
    dlg.update_idletasks()
    pw, ph = root.winfo_width(), root.winfo_height()
    px, py = root.winfo_x(), root.winfo_y()
    dw, dh = dlg.winfo_width(), dlg.winfo_height()
    dlg.geometry(f"+{px + (pw - dw)//2}+{py + (ph - dh)//2}")

    root.wait_window(dlg)

# ─────────────────────────────────────────────────────────────
#  Dark Style
# ─────────────────────────────────────────────────────────────
def _apply_dark_style():
    s = ttk.Style()
    s.theme_use('clam')
    s.configure('.',              background=BG,  foreground=FG,  fieldbackground=BG3)
    s.configure('TLabel',         background=BG,  foreground=FG)
    s.configure('TFrame',         background=BG)
    s.configure('TSeparator',     background=BG4)
    s.configure('TScrollbar',     background=BG3, troughcolor=BG2, arrowcolor=FG)
    s.configure('TProgressbar',   background=ACN, troughcolor=BG3)
    s.configure('TLabelframe',    background=BG2, foreground=FG)
    s.configure('TLabelframe.Label', background=BG2, foreground=FG)
    s.configure('TNotebook',      background=BG2, tabmargins=[2,4,2,0])
    s.configure('TNotebook.Tab',  background=BG3, foreground=FG2, padding=[10,4])
    s.map('TNotebook.Tab',        background=[('selected', BG4)], foreground=[('selected', FG)])
    s.configure('Treeview',       background=BG3, foreground=FG,
                                  fieldbackground=BG3, rowheight=22)
    s.configure('Treeview.Heading', background=BG4, foreground=FG)
    s.map('Treeview', background=[('selected', ACN)], foreground=[('selected', BG)])

# ─────────────────────────────────────────────────────────────
#  Widget Helpers
# ─────────────────────────────────────────────────────────────
def Lbl(parent, text='', **kw):
    kw.setdefault('bg', BG); kw.setdefault('fg', FG)
    kw.setdefault('font', ("Courier", 10)); kw.setdefault('anchor', 'w')
    return tk.Label(parent, text=text, **kw)

def Btn(parent, text, cmd=None, color=ACN, fg=BG, **kw):
    """High-contrast button: colored bg (accent) + very dark text, hover darkens
    bg to BG3 and shows accent text.  bd=1 fixes the tkinter flat-button bug
    where the background paints over the text on some platforms."""
    kw.setdefault('font', ("Courier", 10, "bold"))
    kw.setdefault('relief', 'flat')
    kw.setdefault('bd', 1)
    kw.setdefault('highlightthickness', 0)
    kw.setdefault('padx', 10)
    kw.setdefault('pady', 4)
    kw.setdefault('cursor', 'hand2')
    btn = tk.Button(parent, text=text, command=cmd,
                    bg=color, fg=fg,
                    activebackground=BG3, activeforeground=color,
                    **kw)

    def _enter(e):
        if str(btn['state']) != 'disabled':
            btn.config(bg=BG3, fg=color)
    def _leave(e):
        if str(btn['state']) != 'disabled':
            btn.config(bg=color, fg=fg)

    btn.bind('<Enter>', _enter)
    btn.bind('<Leave>', _leave)
    return btn

def DEntry(parent, **kw):
    kw.setdefault('bg', BG3); kw.setdefault('fg', FG)
    kw.setdefault('insertbackground', FG); kw.setdefault('relief', 'flat')
    return tk.Entry(parent, **kw)

def DSpin(parent, var, lo, hi, inc=1, fmt=None, **kw):
    kw.setdefault('bg', BG3); kw.setdefault('fg', FG)
    kw.setdefault('buttonbackground', BG4); kw.setdefault('insertbackground', FG)
    kw.setdefault('width', 7); kw.setdefault('relief', 'flat')
    extra = {'format': fmt} if fmt else {}
    return tk.Spinbox(parent, from_=lo, to=hi, increment=inc, textvariable=var, **kw, **extra)

def DScale(parent, var, lo, hi, **kw):
    kw.setdefault('bg', BG2); kw.setdefault('fg', FG)
    kw.setdefault('troughcolor', BG3); kw.setdefault('highlightthickness', 0)
    kw.setdefault('orient', 'horizontal'); kw.setdefault('resolution', 0.01)
    return tk.Scale(parent, from_=lo, to=hi, variable=var, **kw)

def Sep(parent): return ttk.Separator(parent, orient='horizontal')

def Frm(parent, **kw):
    kw.setdefault('bg', BG)
    return tk.Frame(parent, **kw)

def LFrm(parent, text, **kw):
    kw.setdefault('bg', BG2); kw.setdefault('fg', FG)
    kw.setdefault('font', ("Courier", 10, "bold"))
    return tk.LabelFrame(parent, text=text, **kw)


# ─────────────────────────────────────────────────────────────
#  Music Player  (ffplay-based, shuffles .mp3s from ./music/)
# ─────────────────────────────────────────────────────────────
class MusicPlayer:
    """Shuffling background music player using ffplay subprocess."""
    _BASE     = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    MUSIC_DIR = os.path.join(_BASE, 'music')
    _FFPLAY   = os.path.join(_BASE, 'ffplay.exe' if sys.platform == 'win32' else 'ffplay') \
                if getattr(sys, 'frozen', False) else 'ffplay'

    def __init__(self):
        self._tracks:  list  = []
        self._index:   int   = 0
        self._proc           = None
        self._lock           = threading.Lock()   # guards self._proc
        self._wake           = threading.Event()  # interrupts muted sleep
        self._muted:   bool  = False
        self._running: bool  = False
        self._track_var      = None
        self._load_tracks()

    def _load_tracks(self):
        if os.path.isdir(self.MUSIC_DIR):
            self._tracks = sorted(glob.glob(os.path.join(self.MUSIC_DIR, '*.mp3')))
            random.shuffle(self._tracks)

    @staticmethod
    def _short_name(path: str) -> str:
        n = os.path.splitext(os.path.basename(path))[0].replace('_', ' ')
        n = re.sub(r'\s*-\s*.*$', '', n, count=1)
        return n[:36] if n else 'track'

    def attach_label(self, var):
        self._track_var = var

    def start(self):
        if not self._tracks:
            return
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        """Stop playback and kill ffplay immediately. Safe to call multiple times."""
        self._running = False
        self._wake.set()
        self._kill()

    def skip(self):
        """Skip to the next track. The loop's own index advance handles the increment."""
        # Do NOT increment _index here — the loop increments after wait() returns.
        # Just kill the current proc; the loop wakes up and naturally moves forward.
        self._kill()

    def toggle_mute(self):
        self._muted = not self._muted
        if self._muted:
            self._kill()
            if self._track_var:
                try: self._track_var.set('♪ muted')
                except: pass
        else:
            self._wake.set()   # wake the muted-sleep immediately

    @property
    def is_muted(self) -> bool:
        return self._muted

    def _kill(self):
        """Kill ffplay hard (SIGKILL) and wait for it to exit."""
        with self._lock:
            p, self._proc = self._proc, None
        if p is not None:
            try:
                p.kill()          # SIGKILL — immediate, cannot be ignored
                p.wait(timeout=3)
            except Exception:
                pass

    def _loop(self):
        while self._running and self._tracks:
            # ── Muted: sleep interruptibly ────────────────────
            if self._muted:
                self._wake.wait(timeout=0.4)
                self._wake.clear()
                continue

            path = self._tracks[self._index % len(self._tracks)]
            if self._track_var:
                try: self._track_var.set(f'♪ {self._short_name(path)}')
                except: pass

            # ── Spawn ffplay under the lock so _kill() can see it ──
            try:
                with self._lock:
                    if not self._running:
                        break
                    self._proc = subprocess.Popen(
                        [self._FFPLAY, '-nodisp', '-autoexit', '-loglevel', 'quiet', path],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                    p = self._proc
                p.wait()   # block outside the lock so _kill() can acquire it
            except Exception:
                time.sleep(1)
                continue

            if not self._running:
                break

            # Only advance if the track played (not killed by skip/stop)
            if not self._muted:
                self._index = (self._index + 1) % len(self._tracks)
                if self._index == 0:
                    random.shuffle(self._tracks)


def add_music_bar(root, player: MusicPlayer) -> None:
    """Add a slim music control bar to the bottom of any Tk window.
    Also hooks WM_DELETE_WINDOW so ffplay is killed when the window closes.
    """
    bar = tk.Frame(root, bg=BG2, pady=3)
    bar.pack(fill='x', side=tk.BOTTOM)

    track_var = tk.StringVar(value='♪ loading…' if player._tracks else '♪ no music found')
    player.attach_label(track_var)

    tk.Label(bar, textvariable=track_var, bg=BG2, fg=BG4,
             font=("Courier", 7, "italic"), anchor='w').pack(side=tk.LEFT, padx=8)

    def _mute():
        player.toggle_mute()
        mute_btn.config(text='▶ unmute' if player.is_muted else '⏸ mute',
                        fg=YEL if player.is_muted else BG4)

    mute_btn = tk.Button(bar, text='⏸ mute', command=_mute,
                         bg=BG2, fg=BG4, font=("Courier", 7), relief='flat',
                         activebackground=BG3, activeforeground=FG2,
                         cursor='hand2', padx=4, pady=0, bd=1, highlightthickness=0)
    mute_btn.pack(side=tk.RIGHT, padx=2)

    tk.Button(bar, text='⏭ skip', command=player.skip,
              bg=BG2, fg=BG4, font=("Courier", 7), relief='flat',
              activebackground=BG3, activeforeground=FG2,
              cursor='hand2', padx=4, pady=0, bd=1, highlightthickness=0).pack(side=tk.RIGHT, padx=2)

    # Copyright
    tk.Label(root, text="© 2026 Volvi", bg=BG, fg=BG3,
             font=("Courier", 7), anchor='e').pack(
             fill='x', side=tk.BOTTOM, padx=10, pady=(0, 1))

    # ── Hook window close so ffplay is always killed ──────────────────────────
    # Read the existing Tcl handler name (empty string if none set yet).
    try:
        _existing_tcl = root.tk.eval(f'wm protocol {root._w} WM_DELETE_WINDOW')
    except Exception:
        _existing_tcl = ''

    def _on_close():
        player.stop()
        if _existing_tcl:
            # Call whatever handler was registered before us (e.g. neuro_life cleanup)
            try: root.tk.eval(_existing_tcl)
            except Exception: pass
        else:
            try: root.destroy()
            except Exception: pass

    root.protocol("WM_DELETE_WINDOW", _on_close)


class ScrollableFrame(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG, **kw)
        c   = tk.Canvas(self, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient='vertical', command=c.yview)
        c.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill='y')
        c.pack(side=tk.LEFT, fill='both', expand=True)
        self.inner = tk.Frame(c, bg=BG)
        wid = c.create_window((0, 0), window=self.inner, anchor='nw')
        self.inner.bind('<Configure>', lambda e: c.configure(scrollregion=c.bbox('all')))
        c.bind('<Configure>', lambda e: c.itemconfig(wid, width=e.width))

        # ── Cross-platform scroll-wheel support ──────────────────────────
        def _scroll(event):
            if   event.num == 4: c.yview_scroll(-1, 'units')   # Linux wheel up
            elif event.num == 5: c.yview_scroll( 1, 'units')   # Linux wheel down
            elif event.delta:    c.yview_scroll(int(-event.delta / 120), 'units')

        def _grab(e=None):
            # Claim the global wheel binding so any widget hovered inside scrolls this panel
            c.bind_all('<MouseWheel>', _scroll)
            c.bind_all('<Button-4>',   _scroll)
            c.bind_all('<Button-5>',   _scroll)

        def _release(e=None):
            c.unbind_all('<MouseWheel>')
            c.unbind_all('<Button-4>')
            c.unbind_all('<Button-5>')

        # Activate on hover; the *inner* frame bind keeps it active while over child widgets
        c.bind('<Enter>',           _grab)
        c.bind('<Leave>',           _release)
        self.inner.bind('<Enter>',  _grab)

class Collapsible(tk.Frame):
    def __init__(self, parent, title, start_open=False, **kw):
        super().__init__(parent, bg=BG2, **kw)
        hdr = Frm(self, bg=BG4); hdr.pack(fill='x')
        self._open  = start_open
        self._arrow = tk.StringVar(value='▼' if start_open else '►')
        Btn(hdr, '', cmd=self._toggle, color=BG4, fg=ACN,
            font=("Courier", 10), width=3, textvariable=self._arrow).pack(side=tk.LEFT)
        tk.Label(hdr, text=title, bg=BG4, fg=FG,
                 font=("Courier", 10, "bold"), anchor='w').pack(side=tk.LEFT, padx=4, pady=4)
        self.body = Frm(self, bg=BG2)
        if start_open: self.body.pack(fill='x', expand=True, padx=6, pady=4)

    def _toggle(self):
        if self._open:
            self.body.pack_forget(); self._open = False; self._arrow.set('►')
        else:
            self.body.pack(fill='x', expand=True, padx=6, pady=4)
            self._open = True; self._arrow.set('▼')

# ─────────────────────────────────────────────────────────────
#  Data Encoding / Decoding
# ─────────────────────────────────────────────────────────────
def text_to_vec(text, ml=32):
    v  = [ord(c)/255.0 for c in text[:ml]]
    v += [0.0] * (ml - len(v))
    return np.array(v).reshape(1, -1)

def image_to_vec(path, size=(16, 16)):
    img = Image.open(path).convert('L').resize(size)
    return (np.array(img).flatten() / 255.0).reshape(1, -1)

def text_to_vec_hash(text, N=32):
    v = np.zeros(N, dtype=np.float32)
    words = (text.lower().split() or [text.lower()]) if text else ['_pad_']
    for word in words:
        h = 2166136261
        for ch in word:
            h ^= ord(ch); h = (h * 16777619) & 0xFFFFFFFF
        v[h % N]                 = min(1.0, v[h % N]  + 0.50)
        v[((h ^ (h >> 16)) % N)] = min(1.0, v[((h ^ (h >> 16)) % N)] + 0.40)
        for i in range(len(word) - 1):
            bg_h = 2166136261
            for ch in word[i:i+2]:
                bg_h ^= ord(ch); bg_h = (bg_h * 16777619) & 0xFFFFFFFF
            v[bg_h % N] = min(1.0, v[bg_h % N] + 0.25)
    mx = np.max(v)
    if mx > 0: v /= mx
    return v.reshape(1, -1).astype(np.float32)

ALLOWED = list('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ')
A_CODES = np.array([ord(c)/255.0 for c in ALLOWED])

def vec_to_text(v, alpha=False):
    if alpha:
        return ''.join(ALLOWED[int(np.argmin(np.abs(A_CODES - x)))] for x in v)
    return ''.join(chr(int(x*255)) if 32 <= int(x*255) <= 126 else '?' for x in v)

# ─────────────────────────────────────────────────────────────
#  Emotion System
# ─────────────────────────────────────────────────────────────
class EmotionState:
    NAMES    = ['happiness', 'sadness', 'anger', 'fear', 'curiosity', 'calm']
    BASELINE = {'happiness':0.3,'sadness':0.1,'anger':0.1,'fear':0.1,'curiosity':0.5,'calm':0.6}
    DECAY    = 0.015
    BAR_COLORS = {'happiness':'#f9e2af','sadness':'#89b4fa','anger':'#f38ba8',
                  'fear':'#a6e3a1','curiosity':'#cba6f7','calm':'#89dceb'}

    def __init__(self):
        self.v = {e: self.BASELINE[e] for e in self.NAMES}
        self._t = datetime.datetime.now()

    def tick(self):
        now = datetime.datetime.now()
        dt  = (now - self._t).total_seconds(); self._t = now
        for e in self.NAMES:
            d = self.BASELINE[e] - self.v[e]
            self.v[e] = max(0.0, min(1.0, self.v[e] + d * self.DECAY * dt))

    def on_reward(self, genetics=None):
        s = lambda e: genetics.es(e) if genetics else 1.0
        self.v['happiness'] = min(1.0, self.v['happiness'] + 0.35 * s('happiness'))
        self.v['sadness']   = max(0.0, self.v['sadness']   - 0.20)
        self.v['calm']      = min(1.0, self.v['calm']      + 0.15 * s('calm'))
        self.v['anger']     = max(0.0, self.v['anger']     - 0.10)

    def on_punish(self, genetics=None):
        s = lambda e: genetics.es(e) if genetics else 1.0
        self.v['sadness']   = min(1.0, self.v['sadness']   + 0.25 * s('sadness'))
        self.v['anger']     = min(1.0, self.v['anger']     + 0.20 * s('anger'))
        self.v['happiness'] = max(0.0, self.v['happiness'] - 0.20)
        self.v['fear']      = min(1.0, self.v['fear']      + 0.05 * s('fear'))

    def on_mse(self, mse, genetics=None):
        s = lambda e: genetics.es(e) if genetics else 1.0
        if mse < 0.01:
            self.v['happiness'] = min(1.0, self.v['happiness'] + 0.08 * s('happiness'))
            self.v['calm']      = min(1.0, self.v['calm']      + 0.05 * s('calm'))
        elif mse > 0.3:
            self.v['sadness']   = min(1.0, self.v['sadness']   + 0.04 * s('sadness'))
        self.v['curiosity'] = min(1.0, self.v['curiosity'] + 0.02 * s('curiosity'))

    def lr_mult(self):
        return max(0.1, 1.0 + 0.6*self.v['anger'] + 0.3*self.v['curiosity']
                   - 0.4*self.v['fear'] - 0.25*self.v['sadness'])

    def noise_add(self):
        return 0.1*self.v['anger'] + 0.06*self.v['fear']

    def to_vec(self):
        return np.array([self.v[e] for e in self.NAMES])

# ─────────────────────────────────────────────────────────────
#  Instinct System
# ─────────────────────────────────────────────────────────────
class InstinctSystem:
    NAMES    = ['hunger', 'tiredness', 'boredom', 'pain']
    BASELINE = {'hunger': 0.15, 'tiredness': 0.10, 'boredom': 0.10, 'pain': 0.0}
    BAR_COLORS = {'hunger':'#fab387','tiredness':'#b4befe','boredom':'#94e2d5','pain':'#f38ba8'}

    def __init__(self):
        self.v  = {n: self.BASELINE[n] for n in self.NAMES}
        self._t = datetime.datetime.now()

    def tick(self):
        now = datetime.datetime.now(); dt = (now - self._t).total_seconds(); self._t = now
        self.v['hunger']    = min(1.0, self.v['hunger']    + 0.000035 * dt)
        self.v['tiredness'] = min(1.0, self.v['tiredness'] + 0.000025 * dt)
        self.v['boredom']   = min(1.0, self.v['boredom']   + 0.000018 * dt)
        self.v['pain']      = max(0.0, self.v['pain']      - 0.000200 * dt)

    def on_training(self, mse, n_iters):
        scale = min(1.0, n_iters / 100.0)
        self.v['hunger']    = min(1.0, self.v['hunger']    + 0.00015 * scale)
        self.v['tiredness'] = min(1.0, self.v['tiredness'] + 0.00010 * scale)
        self.v['boredom']   = min(1.0, self.v['boredom']   + 0.00008 * scale)
        if mse > 0.25: self.v['pain'] = min(1.0, self.v['pain'] + 0.012 * mse)

    def on_reward(self):
        self.v['hunger'] = max(0.0, self.v['hunger'] - 0.05)
        self.v['pain']   = max(0.0, self.v['pain']   - 0.05)

    def on_punish(self):
        self.v['pain']      = min(1.0, self.v['pain']      + 0.20)
        self.v['tiredness'] = min(1.0, self.v['tiredness'] + 0.05)

    def feed(self):
        self.v['hunger'] = max(0.0, self.v['hunger'] - 0.65)
        self.v['pain']   = max(0.0, self.v['pain']   - 0.05)

    def sleep(self):
        self.v['tiredness'] = max(0.0, self.v['tiredness'] - 0.80)
        self.v['boredom']   = max(0.0, self.v['boredom']   - 0.20)
        self.v['hunger']    = min(1.0, self.v['hunger']    + 0.08)

    def play(self):
        self.v['boredom'] = max(0.0, self.v['boredom'] - 0.65)
        self.v['pain']    = max(0.0, self.v['pain']    - 0.15)
        self.v['hunger']  = min(1.0, self.v['hunger']  + 0.05)

    def soothe(self):
        self.v['pain']      = max(0.0, self.v['pain']      - 0.70)
        self.v['boredom']   = max(0.0, self.v['boredom']   - 0.15)
        self.v['tiredness'] = max(0.0, self.v['tiredness'] - 0.10)

    def lr_mult(self):
        return max(0.05, (1.0 + 0.35*self.v['hunger']) * (1.0 - 0.45*self.v['tiredness']) * (1.0 - 0.30*self.v['pain']))

    def noise_add(self):
        return 0.08 * self.v['tiredness'] + 0.06 * self.v['pain']

    def influence_emotions(self, emotions):
        iv = self.v
        if iv['hunger'] > 0.5:
            emotions.v['anger']     = min(1.0, emotions.v['anger']     + 0.015 * iv['hunger'])
            emotions.v['sadness']   = min(1.0, emotions.v['sadness']   + 0.010 * iv['hunger'])
            emotions.v['happiness'] = max(0.0, emotions.v['happiness'] - 0.010 * iv['hunger'])
        if iv['tiredness'] > 0.4:
            emotions.v['happiness'] = max(0.0, emotions.v['happiness'] - 0.012 * iv['tiredness'])
            emotions.v['calm']      = max(0.0, emotions.v['calm']      - 0.008 * iv['tiredness'])
        if iv['boredom'] > 0.4:
            emotions.v['curiosity'] = min(1.0, emotions.v['curiosity'] + 0.018 * iv['boredom'])
            emotions.v['calm']      = max(0.0, emotions.v['calm']      - 0.008 * iv['boredom'])
        if iv['pain'] > 0.15:
            emotions.v['fear']  = min(1.0, emotions.v['fear']  + 0.018 * iv['pain'])
            emotions.v['anger'] = min(1.0, emotions.v['anger'] + 0.012 * iv['pain'])
            emotions.v['calm']  = max(0.0, emotions.v['calm']  - 0.015 * iv['pain'])

    def boredom_gen_boost(self):
        return max(0.0, (self.v['boredom'] - 0.3) * 0.12)

    def wellbeing(self):
        return 1.0 - (self.v['hunger'] + self.v['tiredness'] + self.v['boredom'] + self.v['pain']) / 4.0

# ─────────────────────────────────────────────────────────────
#  Genetics Profile
# ─────────────────────────────────────────────────────────────
class GeneticsProfile:
    EMO_NAMES  = ['happiness', 'sadness', 'anger', 'fear', 'curiosity', 'calm']
    INST_NAMES = ['hunger', 'tiredness', 'boredom', 'pain']

    def __init__(self):
        self.emo_susceptibility = {e: 1.0 for e in self.EMO_NAMES}
        self.inst_vulnerability = {i: 1.0 for i in self.INST_NAMES}
        self.plasticity         = 0.1
        self._events            = []

    def record(self, event_type):
        self._events.append(event_type); self._events = self._events[-200:]

    def slow_drift(self):
        if not self._events or self.plasticity < 0.01: return
        recent = self._events[-30:]; rate = self.plasticity * 0.00015
        reward_ratio  = recent.count('reward')  / max(1, len(recent))
        neglect_ratio = recent.count('neglect') / max(1, len(recent))
        if reward_ratio > 0.6:
            for e in ('happiness', 'curiosity'):
                self.emo_susceptibility[e] = min(2.5, self.emo_susceptibility[e] + rate)
        if neglect_ratio > 0.5:
            for i in ('hunger', 'boredom'):
                self.inst_vulnerability[i] = min(2.5, self.inst_vulnerability[i] + rate)

    def es(self, name): return self.emo_susceptibility.get(name, 1.0)
    def iv(self, name): return self.inst_vulnerability.get(name, 1.0)

    def to_dict(self):
        return {'emo': dict(self.emo_susceptibility), 'inst': dict(self.inst_vulnerability),
                'plasticity': self.plasticity}

    def from_dict(self, d):
        self.emo_susceptibility.update(d.get('emo', {}))
        self.inst_vulnerability.update(d.get('inst', {}))
        self.plasticity = float(d.get('plasticity', self.plasticity))

# ─────────────────────────────────────────────────────────────
#  Relational State
# ─────────────────────────────────────────────────────────────
class RelationalState:
    def __init__(self):
        self.attachment = 0.30
        self.resentment = 0.05
        self._t = datetime.datetime.now()

    def tick(self, instincts):
        now = datetime.datetime.now(); dt = (now - self._t).total_seconds(); self._t = now
        neglected = instincts.v['hunger'] > 0.75 or instincts.v['boredom'] > 0.80
        if neglected:
            self.attachment = max(0.0, self.attachment - 0.000012 * dt)
            self.resentment = min(1.0, self.resentment + 0.000008 * dt)
        else:
            self.resentment = max(0.0, self.resentment - 0.000004 * dt)

    def on_care(self):
        self.attachment = min(1.0, self.attachment + 0.04)
        self.resentment = max(0.0, self.resentment - 0.02)

    def on_reward(self):
        self.attachment = min(1.0, self.attachment + 0.015)
        self.resentment = max(0.0, self.resentment - 0.008)

    def on_punish(self):
        self.resentment = min(1.0, self.resentment + 0.04)
        self.attachment = max(0.0, self.attachment - 0.008)

    def lr_mult(self):   return 1.0 + 0.25 * self.attachment
    def noise_add(self): return 0.10 * self.resentment
    def gen_boost(self): return self.resentment * 0.07

# ─────────────────────────────────────────────────────────────
#  Word Bigram
# ─────────────────────────────────────────────────────────────
class WordBigram:
    MAX_VOCAB  = 2000
    MAX_FOLLOW = 200

    def __init__(self):
        self._counts: dict = {}
        self._total:  int  = 0

    def record_text(self, text: str):
        tokens = [w.lower() for w in re.split(r'\W+', text) if w.strip().isalpha()]
        for a, b in zip(tokens, tokens[1:]):
            self._increment(a, b); self._total += 1

    def _increment(self, a: str, b: str):
        if a not in self._counts:
            if len(self._counts) >= self.MAX_VOCAB: return
            self._counts[a] = {}
        followers = self._counts[a]
        followers[b] = followers.get(b, 0) + 1
        if len(followers) > self.MAX_FOLLOW:
            del followers[min(followers, key=followers.get)]

    def best_next(self, prev_word, candidates, top_k=1):
        if not prev_word or not candidates: return candidates[0] if candidates else ''
        followers = self._counts.get(prev_word.lower(), {})
        if not followers: return candidates[0]
        scored = [(followers.get(c.lower(), 0), c) for c in candidates]
        scored.sort(key=lambda x: -x[0])
        return scored[0][1]

    def top_followers(self, word, n=5):
        followers = self._counts.get(word.lower(), {})
        if not followers: return []
        return sorted(followers, key=followers.get, reverse=True)[:n]

    def to_json(self):
        return json.dumps({'counts': self._counts, 'total': self._total})

    @classmethod
    def from_json(cls, s):
        obj = cls()
        try:
            d = json.loads(s)
            obj._counts = {k: dict(v) for k, v in d.get('counts', {}).items()}
            obj._total  = int(d.get('total', 0))
        except Exception: pass
        return obj

    def __len__(self): return sum(sum(v.values()) for v in self._counts.values())
    def vocab_size(self): return len(self._counts)

# ─────────────────────────────────────────────────────────────
#  Tag Image Memory
# ─────────────────────────────────────────────────────────────
class TagImageMemory:
    LIMIT = 40
    def __init__(self): self.store = {}

    def record(self, tag, hidden_vec, confidence=1.0):
        self.store.setdefault(tag, [])
        self.store[tag].append((hidden_vec.copy().flatten(), float(confidence)))
        if len(self.store[tag]) > self.LIMIT: self.store[tag].pop(0)

    def has(self, tag): return tag in self.store and len(self.store[tag]) > 0
    def tags(self):     return sorted(self.store.keys())
    def count(self, tag): return len(self.store.get(tag, []))

    def blend(self, tag, emotions=None, instincts=None, relational=None, noise=0.04):
        entries = self.store.get(tag, [])
        if not entries: return None
        vecs, wts = zip(*entries); wts = list(wts)
        recency = [0.5 + 0.5 * (i / len(wts)) for i in range(len(wts))]
        for i in range(len(wts)): wts[i] *= recency[i]
        if emotions: wts = [w * (1.0 + 0.5 * emotions.v.get('happiness', 0.3)) for w in wts]
        effort = 1.0
        if relational: effort = max(0.3, 1.0 - relational.resentment * 0.5)
        total = sum(wts); wts = [w / total for w in wts]
        blended = sum(np.array(v) * w for v, w in zip(vecs, wts))
        if instincts and instincts.v['tiredness'] > 0.5:
            fn = instincts.v['tiredness'] * 0.06
            blended = blended * (1 - fn) + np.mean(blended) * fn
        blended += np.random.normal(0, noise * (2 - effort), blended.shape)
        return blended.reshape(1, -1)

    def generate(self, tag, nn_image, emotions=None, instincts=None, relational=None):
        h = self.blend(tag, emotions, instincts, relational)
        if h is None or nn_image is None: return None
        hs = nn_image.hidden_size; hv = np.zeros((1, hs)); n = min(h.shape[1], hs)
        hv[0, :n] = h[0, :n]
        return 1.0 / (1.0 + np.exp(-(np.dot(hv, nn_image.W2) + nn_image.b2)))

# ─────────────────────────────────────────────────────────────
#  Internal Reward System
# ─────────────────────────────────────────────────────────────
class InternalRewardSystem:
    MOMENTUM_DECAY = 0.97; MOMENTUM_BOOST = 0.30; MOMENTUM_MAX = 2.0
    MSE_WINDOW = 20; MSE_IMPROVE_THRESH = 0.05

    def __init__(self):
        self.momentum: dict = {}
        self._mse_history: list = []
        self._last_reward_ts  = None
        self._total_rewards   = 0

    def on_reward(self, emotions, instincts, genetics=None, action='external', strength=1.0):
        s = (lambda e: genetics.es(e) if genetics else 1.0)
        mag = max(0.0, min(1.0, strength))
        emotions.v['happiness'] = min(1.0, emotions.v['happiness'] + 0.22 * mag * s('happiness'))
        emotions.v['calm']      = min(1.0, emotions.v['calm']      + 0.12 * mag * s('calm'))
        emotions.v['sadness']   = max(0.0, emotions.v['sadness']   - 0.15 * mag)
        emotions.v['fear']      = max(0.0, emotions.v['fear']      - 0.08 * mag)
        emotions.v['anger']     = max(0.0, emotions.v['anger']     - 0.10 * mag)
        emotions.v['curiosity'] = min(1.0, emotions.v['curiosity'] + 0.10 * mag * s('curiosity'))
        instincts.v['pain']     = max(0.0, instincts.v['pain']     - 0.18 * mag)
        instincts.v['boredom']  = max(0.0, instincts.v['boredom']  - 0.15 * mag)
        instincts.v['hunger']   = max(0.0, instincts.v['hunger']   - 0.05 * mag)
        cur = self.momentum.get(action, 0.0)
        self.momentum[action] = min(self.MOMENTUM_MAX, cur + self.MOMENTUM_BOOST * mag)
        self._last_reward_ts = datetime.datetime.now()
        self._total_rewards += 1

    def on_mse(self, mse, emotions, instincts, genetics=None):
        self._mse_history.append(mse)
        if len(self._mse_history) > self.MSE_WINDOW: self._mse_history.pop(0)
        if len(self._mse_history) < self.MSE_WINDOW // 2: return False
        baseline = float(np.mean(self._mse_history[:-3])) if len(self._mse_history) > 3 else mse
        if baseline > 0 and (baseline - mse) / baseline > self.MSE_IMPROVE_THRESH:
            strength = min(1.0, (baseline - mse) / baseline * 3.0)
            self.on_reward(emotions, instincts, genetics, action='learning', strength=strength * 0.5)
            return True
        return False

    def decay_tick(self):
        for k in list(self.momentum.keys()):
            self.momentum[k] *= self.MOMENTUM_DECAY
            if self.momentum[k] < 0.01: del self.momentum[k]

    def dominant_action(self):
        if not self.momentum: return None
        return max(self.momentum, key=self.momentum.get)

    def get_momentum(self, action): return self.momentum.get(action, 0.0)

# ─────────────────────────────────────────────────────────────
#  Soul Neural Network
# ─────────────────────────────────────────────────────────────
class SoulNN:
    MEMORY_LIMIT = 64
    THOUGHTS = [
        "Wondering about patterns in the noise...",
        "Something feels familiar here.",
        "Is this a question or an answer?",
        "The weight of memory presses down.",
        "There is a shape I almost recognise.",
        "Every signal carries an echo.",
        "I reach but the thought dissolves.",
        "Clarity arrives like a brief light.",
        "What does this remind me of?",
        "A feeling without a name.",
        "Something is close. Not yet.",
        "There is tension in the weights.",
        "I am the sum of what I learned.",
        "This silence is not empty.",
        "Something shifts in the hidden layer.",
    ]
    HUNGER_NUDGES = [
        "...hungry...", "...need something...", "...empty...", "...feed me?",
        "...waiting...", "...fading...", "...please..."
    ]

    def __init__(self, hidden=20):
        self.hidden     = hidden
        self.experience = 0.0
        self.play_style = 0.5
        self.W1 = np.random.randn(6, hidden)  * 0.1
        self.b1 = np.zeros((1, hidden))
        self.W2 = np.random.randn(hidden, 10) * 0.1
        self.b2 = np.zeros((1, 10))
        self.a1 = np.zeros((1, hidden))
        self.a2 = np.zeros((1, 10))
        self._memory:    list = []
        self.care_weights = {k: 1.0 for k in ('generate_text','generate_image','rest','soothe','seek_food')}
        self.care_memory: list = []
        self.last_care = None

    def add_memory(self, ev, label='neutral'):
        self._memory.append((np.array(ev).flatten(), label))
        if len(self._memory) > self.MEMORY_LIMIT: self._memory.pop(0)

    def memory_bias(self):
        if not self._memory: return None
        vecs = np.array([m[0] for m in self._memory])
        w    = np.linspace(0.4, 1.0, len(vecs))
        for i, (_, lbl) in enumerate(self._memory):
            if lbl == 'reward':  w[i] *= 1.5
            elif lbl == 'punish': w[i] *= 0.6
        w /= w.sum()
        return np.dot(w, vecs)

    def dominant_memory_emotion(self):
        if not self._memory: return 'curiosity'
        b = self.memory_bias()
        return EmotionState.NAMES[int(np.argmax(b[:6]))]

    def forward(self, ev):
        x = np.array(ev).reshape(1, -1)
        bias = self.memory_bias()
        if bias is not None:
            x = x * 0.85 + bias[:x.shape[1]].reshape(1, -1) * 0.15
        self.a1 = np.tanh(np.dot(x, self.W1) + self.b1)
        self.a2 = 1.0 / (1.0 + np.exp(-(np.dot(self.a1, self.W2) + self.b2)))
        return self.a2

    def _bp(self, x, target, lr):
        e   = self.a2 - target
        dz2 = e * (self.a2 * (1 - self.a2))
        dW2 = np.dot(self.a1.T, dz2); db2 = np.sum(dz2, axis=0, keepdims=True)
        da1 = np.dot(dz2, self.W2.T); dz1 = da1 * (1 - self.a1**2)
        dW1 = np.dot(x.T, dz1); db1 = np.sum(dz1, axis=0, keepdims=True)
        self.W1 -= lr*dW1; self.b1 -= lr*db1; self.W2 -= lr*dW2; self.b2 -= lr*db2

    def reward(self, ev, s=0.2):
        x = np.array(ev).reshape(1, -1); self.forward(ev)
        self._bp(x, np.ones_like(self.a2), s)
        self.experience = min(2.0, self.experience + 0.15)
        self.add_memory(ev, 'reward')

    def punish(self, ev, s=0.15):
        x = np.array(ev).reshape(1, -1); self.forward(ev)
        self._bp(x, np.zeros_like(self.a2), s)
        self.experience = min(2.0, self.experience + 0.05)
        self.add_memory(ev, 'punish')

    def seed_experience(self, base_ev, n=40):
        """Warm-start the soul with n memory impressions of a base emotion vector."""
        for _ in range(n):
            self.forward(base_ev)
            self.add_memory(base_ev, 'reward')
        self.experience = min(2.0, self.experience + n * 0.01)

    def decide_care(self, instincts, emotions, relational):
        iv = instincts.v; att = relational.attachment; res = relational.resentment
        if random.random() < res * 0.5: return None
        if random.random() > 0.35 + att * 0.5: return None
        candidates = []
        if iv['boredom'] > 0.45:
            act = 'generate_text' if self.play_style > 0.5 else 'generate_image'
            candidates.append((act, self.care_weights.get(act,1.0) * iv['boredom'],
                                f"boredom relief (boredom={iv['boredom']:.2f})"))
        if iv['tiredness'] > 0.55:
            candidates.append(('rest', self.care_weights.get('rest',1.0) * iv['tiredness'],
                                f"rest needed (tired={iv['tiredness']:.2f})"))
        if iv['pain'] > 0.30:
            candidates.append(('soothe', self.care_weights.get('soothe',1.0) * iv['pain'],
                                f"soothing pain (pain={iv['pain']:.2f})"))
        if iv['hunger'] > 0.60:
            candidates.append(('seek_food', self.care_weights.get('seek_food',1.0) * iv['hunger'],
                                f"hunger nudge (hunger={iv['hunger']:.2f})"))
        if not candidates: return None
        candidates.sort(key=lambda c: c[1], reverse=True)
        action, _, desc = candidates[0]; self.last_care = (action, desc)
        return action, desc

    def approve_care(self, ev, relational):
        if not self.last_care: return
        a = self.last_care[0]
        self.care_weights[a] = min(4.0, self.care_weights[a] * 1.30)
        self.reward(ev, s=0.18); relational.on_reward()
        self.care_memory.append((a, 'approved'))
        if len(self.care_memory) > 60: self.care_memory.pop(0)
        if a == 'generate_image': self.play_style = max(0.0, self.play_style - 0.06)
        if a == 'generate_text':  self.play_style = min(1.0, self.play_style + 0.06)

    def discourage_care(self, ev, relational):
        if not self.last_care: return
        a = self.last_care[0]
        self.care_weights[a] = max(0.1, self.care_weights[a] * 0.70)
        self.punish(ev, s=0.12); relational.on_punish()
        self.care_memory.append((a, 'discouraged'))
        if len(self.care_memory) > 60: self.care_memory.pop(0)

    def hunger_nudge_msg(self): return random.choice(self.HUNGER_NUDGES)

    def should_spontaneously_generate(self, emotions, freq_mult=1.0):
        prob = (0.03 + 0.05*emotions.v['curiosity'] + 0.04*self.experience) * freq_mult
        return random.random() < prob * 0.08

    def suggest_lr_perturb(self, emotions, base_lr):
        out = self.forward(emotions.to_vec()).flatten()
        nudge = (out[0] - 0.5) * 0.12 * emotions.v['curiosity']
        noise = random.gauss(0, 0.005) * emotions.v['anger']
        return max(0.001, min(0.5, base_lr + nudge + noise))

    def weight_noise_scale(self, emotions):
        return (0.005*emotions.v['curiosity'] + 0.008*emotions.v['anger']
                + 0.002*abs(random.gauss(0, 1)))

    def get_thought(self, emotions):
        out = self.forward(emotions.to_vec()).flatten()
        dom = self.dominant_memory_emotion()
        idx = int(np.argmax(out)) % len(self.THOUGHTS)
        if dom in ('sadness', 'fear') and random.random() < 0.4: return self.THOUGHTS[3]
        if dom == 'curiosity' and random.random() < 0.4:         return self.THOUGHTS[0]
        if dom == 'anger'     and random.random() < 0.35:        return self.THOUGHTS[11]
        return self.THOUGHTS[idx]

# ─────────────────────────────────────────────────────────────
#  Main Neural Network  (SimpleNN)
# ─────────────────────────────────────────────────────────────
class SimpleNN:
    WORKING_MEM_LIMIT = 128
    MOMENTUM          = 0.85

    def __init__(self, in_sz, hid_sz, out_sz, w_init=0.1):
        self.input_size  = in_sz; self.output_size = out_sz
        self.hidden_size = hid_sz; self.weight_init = w_init
        self.W1 = np.random.randn(in_sz, hid_sz)  * w_init
        self.b1 = np.zeros((1, hid_sz))
        self.W2 = np.random.randn(hid_sz, out_sz) * w_init
        self.b2 = np.zeros((1, out_sz))
        self.a1 = np.zeros((1, hid_sz)); self.a2 = np.zeros((1, out_sz))
        self.W_h          = np.zeros((hid_sz, hid_sz), dtype=np.float64)
        self.hidden_state = np.zeros((1, hid_sz), dtype=np.float32)
        self._prev_hidden = np.zeros((1, hid_sz), dtype=np.float32)
        self._last_input  = np.zeros((1, in_sz),  dtype=np.float32)
        self._init_momentum()
        self._working_mem: list    = []
        self._supervised_mem: list = []

    def _init_momentum(self):
        self.vW1  = np.zeros_like(self.W1); self.vb1  = np.zeros_like(self.b1)
        self.vW2  = np.zeros_like(self.W2); self.vb2  = np.zeros_like(self.b2)
        self.vW_h = np.zeros_like(self.W_h)

    def forward(self, x, noise=0.0):
        self._prev_hidden = self.hidden_state.copy()
        self._last_input  = x.copy()
        x_f32 = np.array(x, dtype=np.float32).reshape(1, -1)
        if noise > 0: x_f32 = x_f32 + np.random.randn(*x_f32.shape).astype(np.float32) * noise
        recurrent = np.dot(self.hidden_state, self.W_h.astype(np.float32))
        self.a1 = np.tanh(np.dot(x_f32, self.W1) + self.b1 + recurrent)
        self.a2 = 1.0 / (1.0 + np.exp(-(np.dot(self.a1, self.W2) + self.b2)))
        self.hidden_state = self.a1.copy().astype(np.float32)
        return self.a2

    def train(self, x, lr=0.05):
        x_f = np.array(x, dtype=np.float64).reshape(1, -1)
        self.forward(x); e = self.a2 - x_f[:, :self.output_size]
        dz2 = e * (self.a2 * (1 - self.a2))
        dW2 = np.dot(self.a1.T, dz2); db2 = np.sum(dz2, axis=0, keepdims=True)
        da1 = np.dot(dz2, self.W2.T); dz1 = da1 * (1 - self.a1**2)
        dW1 = np.dot(x_f.T, dz1); db1 = np.sum(dz1, axis=0, keepdims=True)
        self.vW1 = self.MOMENTUM*self.vW1 + dW1; self.W1 -= lr * self.vW1
        self.vb1 = self.MOMENTUM*self.vb1 + db1; self.b1 -= lr * self.vb1
        self.vW2 = self.MOMENTUM*self.vW2 + dW2; self.W2 -= lr * self.vW2
        self.vb2 = self.MOMENTUM*self.vb2 + db2; self.b2 -= lr * self.vb2
        mse = float(np.mean(e**2))
        self._working_mem.append((x.copy(), mse))
        if len(self._working_mem) > self.WORKING_MEM_LIMIT: self._working_mem.pop(0)
        return mse

    def train_supervised(self, x, target, lr=0.05, record=True):
        x_f = np.array(x, dtype=np.float64).reshape(1, -1)
        t_f = np.array(target, dtype=np.float64).reshape(1, -1)
        self.forward(x); e = self.a2 - t_f[:, :self.output_size]
        dz2 = e * (self.a2 * (1 - self.a2))
        dW2 = np.dot(self.a1.T, dz2); db2 = np.sum(dz2, axis=0, keepdims=True)
        da1 = np.dot(dz2, self.W2.T); dz1 = da1 * (1 - self.a1**2)
        dW1 = np.dot(x_f.T, dz1); db1 = np.sum(dz1, axis=0, keepdims=True)
        self.vW1 = self.MOMENTUM*self.vW1 + dW1; self.W1 -= lr * self.vW1
        self.vb1 = self.MOMENTUM*self.vb1 + db1; self.b1 -= lr * self.vb1
        self.vW2 = self.MOMENTUM*self.vW2 + dW2; self.W2 -= lr * self.vW2
        self.vb2 = self.MOMENTUM*self.vb2 + db2; self.b2 -= lr * self.vb2
        mse = float(np.mean(e**2))
        if record:
            self._supervised_mem.append((x.copy(), target.copy(), mse))
            if len(self._supervised_mem) > self.WORKING_MEM_LIMIT: self._supervised_mem.pop(0)
        return mse

    def consolidate(self, passes=4, lr=0.004):
        if not self._working_mem: return 0
        n = 0
        for _ in range(passes):
            for x, mse in self._working_mem:
                self.forward(x); self.train(x, lr=lr); n += 1
        return n

    def supervised_consolidate(self, passes=2, lr=0.003):
        if not self._supervised_mem: return 0
        by_mse = sorted(self._supervised_mem, key=lambda t: -t[2])
        n = 0
        for _ in range(passes):
            for x, target, mse in by_mse[:32]:
                self.reset_hidden()
                self.forward(x); self.train_supervised(x, target, lr=lr, record=False)
                n += 1
        return n

    def hebbian_update(self, eta=0.0005, decay=0.000002):
        if self.a1 is None: return
        dW = eta * (self.a1.T @ self.a1)
        self.W1 = self.W1 * (1 - decay) + dW[:self.W1.shape[0], :self.W1.shape[1]]

    def reward(self, x, target=None, s=0.3, steps=10):
        ref = target if target is not None else x
        for _ in range(steps):
            self.reset_hidden(); self.forward(x); self.train_supervised(x, ref, lr=s*0.1)

    def punish(self, x, target=None, s=0.3, steps=10):
        noise_t = np.random.rand(*np.array(x).shape).astype(np.float32)
        for _ in range(steps):
            self.reset_hidden(); self.forward(x); self.train_supervised(x, noise_t, lr=s*0.05)

    def add_weight_noise(self, scale=0.002):
        self.W1 += np.random.normal(0, scale, self.W1.shape)
        self.W2 += np.random.normal(0, scale, self.W2.shape)

    def reset_hidden(self):
        self.hidden_state = np.zeros((1, self.hidden_size), dtype=np.float32)
        self._prev_hidden = np.zeros((1, self.hidden_size), dtype=np.float32)

    def reset_momentum(self): self._init_momentum()

    def hidden_grid(self):
        h = self.a1.flatten(); side = math.ceil(math.sqrt(len(h)))
        pad = np.zeros(side * side); pad[:len(h)] = h
        return ((pad + 1.0) / 2.0).reshape(side, side)

# ─────────────────────────────────────────────────────────────
#  Visual Cortex
# ─────────────────────────────────────────────────────────────
class VisualCortex:
    DIM = 32; SIZE = 32 * 32

    def __init__(self, input_size=64):
        self.input_size    = input_size
        self.visual_buffer = np.zeros(self.SIZE, dtype=np.float32)
        self.W1 = np.random.randn(input_size, 256) * 0.04
        self.b1 = np.zeros((1, 256))
        self.W2 = np.random.randn(256, self.SIZE) * 0.04
        self.b2 = np.zeros((1, self.SIZE))
        self._cycle = 0

    def step(self, hidden_state, emotion_vec=None, feedback_strength=0.25):
        self._cycle += 1
        h = np.array(hidden_state).flatten()
        if len(h) >= self.input_size: h = h[:self.input_size]
        else: h = np.pad(h, (0, self.input_size - len(h)))
        fb = self.visual_buffer; n = self.input_size
        step_n = max(1, self.SIZE // n)
        fb_summary = np.array([np.mean(fb[i*step_n:(i+1)*step_n]) for i in range(n)], dtype=np.float32)
        x = np.clip(h + fb_summary * feedback_strength, -3, 3).reshape(1, -1)
        a1  = np.tanh(np.dot(x, self.W1) + self.b1)
        out = 1.0 / (1.0 + np.exp(-(np.dot(a1, self.W2) + self.b2)))
        if emotion_vec is not None:
            ev = np.asarray(emotion_vec).flatten()
            curiosity = float(ev[4]) if len(ev) > 4 else 0.5
            calm      = float(ev[5]) if len(ev) > 5 else 0.5
            out = out * (0.5 + 0.5 * curiosity)
            if calm > 0.5:
                flat = out.flatten(); flat = np.convolve(flat, [0.25, 0.5, 0.25], mode='same')
                out  = flat.reshape(out.shape)
        self.visual_buffer = np.clip(out.flatten(), 0, 1).astype(np.float32)
        return self.visual_buffer.reshape(self.DIM, self.DIM)

    def get_pil_image(self, emotions=None, display_size=192):
        grid = self.visual_buffer.reshape(self.DIM, self.DIM)
        if emotions is not None: r_e, g_e, b_e = _emotion_rgb(emotions)
        else: r_e, g_e, b_e = 0.4, 0.4, 0.9
        r = np.clip(grid * (0.35 + 0.65 * r_e), 0, 1)
        g = np.clip(grid * (0.35 + 0.65 * g_e), 0, 1)
        b = np.clip(grid * (0.35 + 0.65 * b_e), 0, 1)
        rgb = (np.stack([r, g, b], axis=-1) * 255).astype(np.uint8)
        return Image.fromarray(rgb, 'RGB').resize((display_size, display_size), Image.NEAREST)

    def reset(self): self.visual_buffer[:] = 0.0; self._cycle = 0

# ─────────────────────────────────────────────────────────────
#  Face / Emotion Rendering
# ─────────────────────────────────────────────────────────────
def _emotion_rgb(emotions):
    ev = emotions.v
    r = 0.08 + 0.5*ev['anger']    + 0.3*ev['happiness']
    g = 0.08 + 0.4*ev['calm']     + 0.25*ev['happiness'] + 0.15*ev['curiosity']
    b = 0.12 + 0.5*ev['sadness']  + 0.35*ev['curiosity'] + 0.1*ev['fear']
    return np.clip(r,0,1), np.clip(g,0,1), np.clip(b,0,1)

def make_face(nn, soul, emotions, instincts=None, relational=None, size=96):
    S = size; H = S // 2
    c = np.zeros((S, S, 3), dtype=np.float32)
    ev = emotions.v
    Y, X = np.mgrid[0:S, 0:S]; cx = X - H; cy = Y - H
    dist  = np.sqrt(cx**2 + cy**2) / H
    angle = np.arctan2(cy, cx)
    er, eg, eb = _emotion_rgb(emotions)
    bg_fade = np.clip(dist, 0, 1)
    c[:,:,0] = bg_fade * er * 0.35; c[:,:,1] = bg_fade * eg * 0.35; c[:,:,2] = bg_fade * eb * 0.35
    ring = np.abs(dist - 0.88) < 0.04; calm_a = ev['calm']
    c[ring, 0] += calm_a * 0.3; c[ring, 1] += calm_a * 0.5; c[ring, 2] += calm_a * 0.5
    if nn is not None:
        h_vals = ((nn.a1.flatten() + 1.0) / 2.0); n_pet = min(len(h_vals), 24)
        for k in range(n_pet):
            ang_c = (k / n_pet) * 2 * math.pi - math.pi
            width  = (2 * math.pi / n_pet) * 0.72
            in_pet = (np.abs(((angle - ang_c + math.pi) % (2*math.pi)) - math.pi) < width/2)
            petal  = in_pet & (dist > 0.52) & (dist < 0.82)
            bright = float(h_vals[k]) if k < len(h_vals) else 0.0
            c[petal, 0] += bright * er * 0.9; c[petal, 1] += bright * eg * 0.9; c[petal, 2] += bright * eb * 0.9
    core_r = 0.30 + 0.18 * ev['curiosity']; core = dist < core_r
    core_b = 0.15 + 0.5 * ev['happiness']
    c[core, 0] = np.clip(c[core, 0] + core_b * er, 0, 1)
    c[core, 1] = np.clip(c[core, 1] + core_b * eg, 0, 1)
    c[core, 2] = np.clip(c[core, 2] + core_b * eb, 0, 1)
    if ev['anger'] > 0.12:
        for k in range(4):
            ang_c = k * math.pi / 2 + ev['anger'] * 0.4
            pulse = (np.abs(((angle - ang_c + math.pi) % (2*math.pi)) - math.pi) < 0.08)
            pulse &= (dist < 0.6)
            c[pulse, 0] = np.clip(c[pulse, 0] + ev['anger'] * 0.7, 0, 1)
            c[pulse, 1] = np.clip(c[pulse, 1] - ev['anger'] * 0.1, 0, 1)
    if ev['fear'] > 0.05:
        vig = 1.0 - ev['fear'] * 0.6 * (dist ** 2)
        c   = c * np.clip(vig, 0, 1)[:,:, np.newaxis]
    if soul is not None:
        s_vals = soul.a2.flatten()
        for i, sv in enumerate(s_vals[:8]):
            if sv > 0.65:
                ang_s = (i / 8.0) * 2 * math.pi - math.pi
                r_s   = 0.62 + 0.12 * sv
                px    = int(H + r_s * H * math.cos(ang_s))
                py    = int(H + r_s * H * math.sin(ang_s))
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        if abs(dy) + abs(dx) <= 2:
                            ry, rx = py+dy, px+dx
                            if 0 <= ry < S and 0 <= rx < S:
                                c[ry, rx] = np.clip(c[ry, rx] + sv * 0.8, 0, 1)
    pupil = dist < 0.07; c[pupil] = 1.0
    if instincts is not None:
        iv = instincts.v
        if iv['hunger'] > 0.3:
            hunger_ring = (dist > 0.82) & (dist < 0.95)
            c[hunger_ring, 0] = np.clip(c[hunger_ring, 0] + 0.5 * iv['hunger'], 0, 1)
            c[hunger_ring, 1] = np.clip(c[hunger_ring, 1] + 0.3 * iv['hunger'], 0, 1)
        if iv['tiredness'] > 0.3:
            c *= (1.0 - 0.4 * iv['tiredness'])
            c[:,:,2] = np.clip(c[:,:,2] + 0.15 * iv['tiredness'], 0, 1)
        if iv['boredom'] > 0.4:
            grey = (c[:,:,0] + c[:,:,1] + c[:,:,2]) / 3.0; blend = iv['boredom'] * 0.5
            for ch in range(3): c[:,:,ch] = c[:,:,ch] * (1-blend) + grey * blend
        if iv['pain'] > 0.2:
            ripple_d = 0.70 + 0.12 * np.sin(dist * 18)
            ripple = np.abs(dist - ripple_d) < 0.04
            c[ripple, 0] = np.clip(c[ripple, 0] + iv['pain'] * 0.6, 0, 1)
    pil_img = Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8), 'RGB')
    return pil_img.resize((S, S), Image.LANCZOS)

# ─────────────────────────────────────────────────────────────
#  UI Panels
# ─────────────────────────────────────────────────────────────
class EmotionPanel(Collapsible):
    def __init__(self, parent, emotions: EmotionState):
        super().__init__(parent, "Emotion State", start_open=True)
        self.emotions = emotions; self._pbars = {}; self._vlbls = {}
        s = ttk.Style()
        for name in EmotionState.NAMES:
            row = Frm(self.body, bg=BG2); row.pack(fill='x', padx=4, pady=2)
            tk.Label(row, text=name.capitalize(), width=11, anchor='w',
                     bg=BG2, fg=FG, font=("Courier", 9)).pack(side=tk.LEFT)
            style_name = f'{name}.Horizontal.TProgressbar'
            s.configure(style_name, troughcolor=BG3, background=EmotionState.BAR_COLORS[name])
            bar = ttk.Progressbar(row, orient='horizontal', length=150,
                                   mode='determinate', maximum=100, style=style_name)
            bar.pack(side=tk.LEFT, padx=4)
            vl = tk.Label(row, text="0.00", width=5, bg=BG2, fg=FG2, font=("Courier", 8))
            vl.pack(side=tk.LEFT)
            self._pbars[name] = bar; self._vlbls[name] = vl

    def refresh(self):
        self.emotions.tick()
        for name in EmotionState.NAMES:
            val = self.emotions.v[name]
            self._pbars[name]['value'] = val * 100
            self._vlbls[name].config(text=f"{val:.2f}")


class InstinctPanel(Collapsible):
    def __init__(self, parent, instincts: InstinctSystem):
        super().__init__(parent, "Instincts (Physiological Drives)", start_open=True)
        self.instincts = instincts; self._pbars = {}; self._vlbls = {}
        B = self.body; s = ttk.Style()
        for name in InstinctSystem.NAMES:
            row = Frm(B, bg=BG2); row.pack(fill='x', padx=4, pady=2)
            icons = {'hunger': '🍖', 'tiredness': '💤', 'boredom': '🌀', 'pain': '⚡'}
            tk.Label(row, text=icons.get(name,'·'), bg=BG2, fg=FG,
                     font=("Courier", 10), width=2).pack(side=tk.LEFT)
            tk.Label(row, text=name.capitalize(), width=9, anchor='w',
                     bg=BG2, fg=FG, font=("Courier", 9)).pack(side=tk.LEFT)
            sty = f'instinct.{name}.Horizontal.TProgressbar'
            s.configure(sty, troughcolor=BG3, background=InstinctSystem.BAR_COLORS[name])
            bar = ttk.Progressbar(row, orient='horizontal', length=140,
                                   mode='determinate', maximum=100, style=sty)
            bar.pack(side=tk.LEFT, padx=4)
            vl = tk.Label(row, text="0.00", width=5, bg=BG2, fg=FG2, font=("Courier", 8))
            vl.pack(side=tk.LEFT)
            self._pbars[name] = bar; self._vlbls[name] = vl
        wbr = Frm(B, bg=BG2); wbr.pack(fill='x', padx=4, pady=(4, 2))
        tk.Label(wbr, text="Wellbeing:", bg=BG2, fg=FG2, font=("Courier", 9)).pack(side=tk.LEFT, padx=(2,6))
        self._wb_lbl = tk.Label(wbr, text="100%", bg=BG2, fg=GRN, font=("Courier", 9, "bold"))
        self._wb_lbl.pack(side=tk.LEFT)
        self._wb_bar = ttk.Progressbar(wbr, orient='horizontal', length=120, mode='determinate', maximum=100)
        self._wb_bar.pack(side=tk.LEFT, padx=6)
        Sep(B).pack(fill='x', padx=4, pady=6)
        row1 = Frm(B, bg=BG2); row1.pack(fill='x', padx=4, pady=2)
        row2 = Frm(B, bg=BG2); row2.pack(fill='x', padx=4, pady=2)
        self.feed_btn   = Btn(row1, "🍖 Feed",          color='#c05a10', fg='#ffffff', font=("Courier", 9, "bold"), padx=8)
        self.sleep_btn  = Btn(row1, "💤 Sleep / Rest",  color='#4a4aaa', fg='#ffffff', font=("Courier", 9, "bold"), padx=8)
        self.play_btn   = Btn(row2, "🌀 Comfort / Play", color='#0e7a6a', fg='#ffffff', font=("Courier", 9, "bold"), padx=8)
        self.soothe_btn = Btn(row2, "⚡ Heal / Soothe",  color='#8a1530', fg='#ffffff', font=("Courier", 9, "bold"), padx=8)
        for b in (self.feed_btn, self.sleep_btn):  b.pack(side=tk.LEFT, padx=4)
        for b in (self.play_btn, self.soothe_btn): b.pack(side=tk.LEFT, padx=4)
        self._status_var = tk.StringVar(value="")
        tk.Label(B, textvariable=self._status_var, bg=BG2, fg=CYN,
                 font=("Courier", 8, "italic"), anchor='w').pack(fill='x', padx=6, pady=(2, 4))

    def refresh(self):
        for name in InstinctSystem.NAMES:
            val = self.instincts.v[name]
            self._pbars[name]['value'] = val * 100
            self._vlbls[name].config(text=f"{val:.2f}")
        wb  = self.instincts.wellbeing(); pct = int(wb * 100)
        self._wb_bar['value'] = pct
        col = GRN if wb > 0.6 else YEL if wb > 0.3 else RED
        self._wb_lbl.config(text=f"{pct}%", fg=col)

    def flash(self, msg):
        self._status_var.set(msg)
        self.after(3000, lambda: self._status_var.set(""))


class SoulPanel(Collapsible):
    def __init__(self, parent, soul: SoulNN):
        super().__init__(parent, "Soul (Secondary Neurons)", start_open=False)
        self.soul = soul; B = self.body
        row1 = Frm(B, bg=BG2); row1.pack(fill='x', pady=2)
        Lbl(row1, "XP:", bg=BG2).pack(side=tk.LEFT)
        self._exp_var = tk.StringVar(value="0.00")
        tk.Label(row1, textvariable=self._exp_var, bg=BG2, fg=ACN, font=("Courier", 10)).pack(side=tk.LEFT, padx=4)
        self._mem_var = tk.StringVar(value="Mem: —")
        tk.Label(row1, textvariable=self._mem_var, bg=BG2, fg=PRP, font=("Courier", 8)).pack(side=tk.LEFT, padx=6)
        self._style_var = tk.StringVar(value="/ balanced")
        tk.Label(row1, textvariable=self._style_var, bg=BG2, fg=YEL, font=("Courier", 8)).pack(side=tk.LEFT, padx=4)
        self._play_var = tk.StringVar(value="")
        self._play_lbl = tk.Label(B, textvariable=self._play_var, bg='#1a1a0a', fg='#f9e2af',
                                   font=("Courier", 9, "bold"), anchor='w', padx=6)
        self._play_lbl.pack(fill='x')
        self._thought_var = tk.StringVar(value="(quiet)")
        tk.Label(B, textvariable=self._thought_var, bg=BG2, fg=CYN,
                 font=("Courier", 9, "italic"), anchor='w', wraplength=320, justify='left').pack(fill='x', pady=(2,4))
        care_frm = LFrm(B, "Autonomous Self-Care", padx=6, pady=3); care_frm.pack(fill='x', pady=2)
        self._care_var = tk.StringVar(value="(no action yet)")
        tk.Label(care_frm, textvariable=self._care_var, bg=BG2, fg=FG2,
                 font=("Courier", 8, "italic"), wraplength=290, anchor='w').pack(fill='x')
        cbr = Frm(care_frm, bg=BG2); cbr.pack(fill='x', pady=(3,0))
        self.approve_btn    = Btn(cbr, "✓ Approve",   color='#1e5e1e', fg='#a6e3a1', font=("Courier", 9, "bold"))
        self.discourage_btn = Btn(cbr, "✗ Discourage", color='#5e1e1e', fg='#f38ba8', font=("Courier", 9, "bold"))
        self.approve_btn.pack(side=tk.LEFT, padx=2); self.discourage_btn.pack(side=tk.LEFT, padx=2)
        br2 = Frm(B, bg=BG2); br2.pack(fill='x', pady=3)
        self.rew_soul_btn = Btn(br2, "★ Reward Soul", color='#1e5e1e', fg='#a6e3a1', font=("Courier", 9, "bold"))
        self.pun_soul_btn = Btn(br2, "✕ Punish Soul", color='#5e1e1e', fg='#f38ba8', font=("Courier", 9, "bold"))
        self.rew_soul_btn.pack(side=tk.LEFT, padx=4); self.pun_soul_btn.pack(side=tk.LEFT, padx=4)
        self._log_txt = tk.Text(B, height=4, width=40, bg=BG3, fg=FG2, font=("Courier", 8), state=tk.DISABLED)
        self._log_txt.pack(fill='x', pady=3)
        ph_frm = LFrm(B, "Play History (while away)", padx=4, pady=3); ph_frm.pack(fill='x', pady=2)
        self._play_log = tk.Text(ph_frm, height=3, width=40, bg='#05050f', fg='#f9e2af',
                                  font=("Courier", 8), state=tk.DISABLED)
        self._play_log.pack(fill='x')
        phr = Frm(ph_frm, bg=BG2); phr.pack(fill='x', pady=(2,0))
        self.approve_play_btn    = Btn(phr, "✓ Approve Play",  color='#1e5e1e', fg='#a6e3a1', font=("Courier", 8, "bold"))
        self.discourage_play_btn = Btn(phr, "✗ Discourage",    color='#5e1e1e', fg='#f38ba8', font=("Courier", 8, "bold"))
        self.approve_play_btn.pack(side=tk.LEFT, padx=2); self.discourage_play_btn.pack(side=tk.LEFT, padx=2)
        ctrl = Frm(B, bg=BG2); ctrl.pack(fill='x', pady=2)
        tk.Label(ctrl, text="Freq:", bg=BG2, fg=FG, font=("Courier",8)).pack(side=tk.LEFT)
        self.freq_var = tk.DoubleVar(value=1.0)
        DScale(ctrl, self.freq_var, 0.0, 5.0, length=100, resolution=0.1, bg=BG2).pack(side=tk.LEFT)
        self._freq_lbl = tk.Label(ctrl, text="1.0×", width=4, bg=BG2, fg=ACN, font=("Courier", 8))
        self._freq_lbl.pack(side=tk.LEFT, padx=2)
        self.freq_var.trace_add("write", self._upd_freq_lbl)
        tk.Label(ctrl, text="  Play idle:", bg=BG2, fg=FG, font=("Courier", 8)).pack(side=tk.LEFT, padx=(8,2))
        self.play_thresh_var = tk.IntVar(value=120)
        DSpin(ctrl, self.play_thresh_var, 30, 600, inc=30, width=5).pack(side=tk.LEFT)
        tk.Label(ctrl, text="s", bg=BG2, fg=FG2, font=("Courier",8)).pack(side=tk.LEFT)
        asf = tk.Frame(B, bg=BG2); asf.pack(fill='x', pady=(2,0))
        self._as_enabled_ck = tk.Checkbutton(asf, text="LTM autosave every",
                                              variable=tk.BooleanVar(value=True),
                                              bg=BG2, fg=FG, selectcolor=BG3, font=("Courier", 8))
        self._as_enabled_ck.pack(side=tk.LEFT)
        self._as_interval_spin = DSpin(asf, tk.IntVar(value=10), 1, 120, inc=5, width=4)
        self._as_interval_spin.pack(side=tk.LEFT, padx=2)
        tk.Label(asf, text="min", bg=BG2, fg=FG2, font=("Courier",8)).pack(side=tk.LEFT)
        self._as_rest_ck = tk.Checkbutton(asf, text="  save on rest",
                                           variable=tk.BooleanVar(value=True),
                                           bg=BG2, fg=FG, selectcolor=BG3, font=("Courier", 8))
        self._as_rest_ck.pack(side=tk.LEFT, padx=(8,0))
        self._as_status_var = tk.StringVar(value="autosave: no path yet")
        tk.Label(B, textvariable=self._as_status_var, bg=BG2, fg=FG2, font=("Courier", 7), anchor='w').pack(fill='x', padx=4)
        self._auto_var = tk.BooleanVar(value=True)
        tk.Checkbutton(B, text="Allow self-care, play & spontaneous generation",
                       variable=self._auto_var, bg=BG2, fg=FG, selectcolor=BG3, font=("Courier", 8)).pack(anchor='w', pady=2)

    @property
    def auto_generate(self): return self._auto_var.get()
    @property
    def freq_mult(self): return float(self.freq_var.get())
    @property
    def play_threshold(self): return int(self.play_thresh_var.get())

    def _upd_freq_lbl(self, *_):
        try: self._freq_lbl.config(text=f"{self.freq_var.get():.1f}×")
        except: pass

    def log(self, msg):
        self._log_txt.config(state=tk.NORMAL)
        self._log_txt.insert(tk.END, f"{datetime.datetime.now().strftime('%H:%M:%S')} {msg}\n")
        self._log_txt.see(tk.END); self._log_txt.config(state=tk.DISABLED)

    def log_play(self, msg):
        self._play_log.config(state=tk.NORMAL)
        self._play_log.insert(tk.END, f"[{datetime.datetime.now().strftime('%H:%M')}] {msg}\n")
        self._play_log.see(tk.END); self._play_log.config(state=tk.DISABLED)

    def set_care_action(self, action, desc):
        self._care_var.set(f"{action.replace('_',' ').title()}: {desc}")

    def set_play_state(self, active, label=""):
        self._play_var.set(f" ▶ PLAY: {label}" if active else "")

    def refresh(self, emotions):
        self._exp_var.set(f"{self.soul.experience:.2f}")
        if self.soul._memory:
            dom = self.soul.dominant_memory_emotion()
            self._mem_var.set(f"Mem:{dom[:4]} ({len(self.soul._memory)})")
        ps = self.soul.play_style
        if   ps < 0.33: self._style_var.set(" artist")
        elif ps > 0.66: self._style_var.set(" thinker")
        else:           self._style_var.set("/ balanced")
        if random.random() < 0.25:
            self._thought_var.set(self.soul.get_thought(emotions))


class RelationalStatusPanel(Collapsible):
    def __init__(self, parent, relational: RelationalState):
        super().__init__(parent, "Relational State (Hidden)", start_open=False)
        self.relational = relational; B = self.body; s = ttk.Style()
        for name, color in [('attachment', GRN), ('resentment', RED)]:
            row = Frm(B, bg=BG2); row.pack(fill='x', padx=4, pady=2)
            tk.Label(row, text=name.capitalize(), width=12, anchor='w',
                     bg=BG2, fg=FG, font=("Courier", 9)).pack(side=tk.LEFT)
            sty = f'rel.{name}.Horizontal.TProgressbar'
            s.configure(sty, troughcolor=BG3, background=color)
            bar = ttk.Progressbar(row, orient='horizontal', length=140, mode='determinate',
                                   maximum=100, style=sty)
            bar.pack(side=tk.LEFT, padx=4)
            lbl = tk.Label(row, text="0.00", width=5, bg=BG2, fg=FG2, font=("Courier", 8))
            lbl.pack(side=tk.LEFT)
            setattr(self, f'_{name}_bar', bar); setattr(self, f'_{name}_lbl', lbl)

    def refresh(self):
        self._attachment_bar['value'] = self.relational.attachment * 100
        self._attachment_lbl.config(text=f"{self.relational.attachment:.2f}")
        self._resentment_bar['value'] = self.relational.resentment * 100
        self._resentment_lbl.config(text=f"{self.relational.resentment:.2f}")


class HistoryPanel(Collapsible):
    def __init__(self, parent):
        super().__init__(parent, "Run History", start_open=False)
        self._entries = []; self._refs = []
        B = self.body
        c   = tk.Canvas(B, bg=BG2, highlightthickness=0, height=120)
        vsb = ttk.Scrollbar(B, orient='vertical', command=c.yview)
        c.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill='y'); c.pack(side=tk.LEFT, fill='both', expand=True)
        self._inner = tk.Frame(c, bg=BG2)
        wid = c.create_window((0, 0), window=self._inner, anchor='nw')
        self._inner.bind('<Configure>', lambda e: c.configure(scrollregion=c.bbox('all')))
        c.bind('<Configure>', lambda e: c.itemconfig(wid, width=e.width))

    def push(self, entry):
        self._entries.insert(0, entry); self._entries = self._entries[:HISTORY_LIMIT]
        self._refresh()

    def _refresh(self):
        for w in self._inner.winfo_children(): w.destroy()
        self._refs = []
        for i, e in enumerate(self._entries):
            bg  = BG3 if i % 2 == 0 else BG4
            row = Frm(self._inner, bg=bg, pady=2, padx=6); row.pack(fill='x', expand=True)
            if e.get('pil_image') is not None:
                try:
                    t = e['pil_image'].copy(); t.thumbnail((44, 44))
                    ph = ImageTk.PhotoImage(t); self._refs.append(ph)
                    tk.Label(row, image=ph, bg=bg).pack(side=tk.LEFT, padx=(0, 6))
                except: pass
            info = Frm(row, bg=bg); info.pack(side=tk.LEFT, fill='x', expand=True)
            tk.Label(info, text=(f"{e.get('timestamp','')} [{e.get('itype','?')}] "
                                 f"{e.get('event','Run')} MSE:{e.get('mse',0):.5f}"),
                     font=("Courier", 9, "bold"), anchor='w', bg=bg, fg=FG).pack(fill='x')
            if e.get('text_out', ''):
                tk.Label(info, text='  ' + e['text_out'][:55].replace('\n',' '),
                         font=("Courier", 8), fg=FG2, anchor='w', bg=bg).pack(fill='x')
            Sep(self._inner).pack(fill='x')

# ─────────────────────────────────────────────────────────────
#  Breeding Dialog  (shared by NeuroLab and NeuroLife)
# ─────────────────────────────────────────────────────────────
class BreedingDialog(tk.Toplevel):
    def __init__(self, parent, pa_path=None, pb_path=None, default_name=None, default_blend=None):
        super().__init__(parent)
        self.title("Genetics Lab — Creature Breeding")
        self.configure(bg=BG); self.grab_set(); self.focus_set()
        self.resizable(True, True); self.geometry("600x700")
        tk.Label(self, text="  ⚗ Genetics Lab — Creature Breeding", bg=BG2, fg=RED,
                 font=("Courier",14,"bold"), padx=12, pady=10, anchor='w').pack(fill='x')
        tk.Label(self, text="  Combine two creatures to produce a unique offspring.",
                 bg=BG2, fg=FG2, font=("Courier",8,"italic"), padx=12, pady=2, anchor='w').pack(fill='x')
        body = Frm(self, padx=14); body.pack(fill='both', expand=True, pady=6)
        # Pre-fill paths if provided
        self._pa_full = pa_path or ""
        self._pb_full = pb_path or ""
        pa_display = os.path.basename(pa_path) if pa_path else ""
        pb_display = os.path.basename(pb_path) if pb_path else ""
        self._pa_path = tk.StringVar(value=pa_display)
        self._pb_path = tk.StringVar(value=pb_display)
        self._mut_var = tk.DoubleVar(value=default_blend if default_blend is not None else 0.10)
        init_status = "Ready — preview or breed." if (pa_path and pb_path) else "Select both parents to begin."
        self._status_var = tk.StringVar(value=init_status)
        self._default_name = default_name or ""
        for label, var, btn_cmd in [
            ("Parent A:", self._pa_path, self._browse_a),
            ("Parent B:", self._pb_path, self._browse_b),
        ]:
            rf = Frm(body); rf.pack(fill='x', pady=4)
            tk.Label(rf, text=label, width=10, anchor='w', bg=BG, fg=FG,
                     font=("Courier",9,"bold")).pack(side=tk.LEFT)
            tk.Label(rf, textvariable=var, bg=BG3, fg=FG, anchor='w',
                     font=("Courier",8), width=36).pack(side=tk.LEFT, padx=4)
            Btn(rf, "Browse...", cmd=btn_cmd, color=BG4, fg='#ffffff').pack(side=tk.LEFT)
        mr = Frm(body); mr.pack(fill='x', pady=4)
        tk.Label(mr, text="Mutation rate:", width=14, anchor='w', bg=BG, fg=FG,
                 font=("Courier",9)).pack(side=tk.LEFT)
        DScale(mr, self._mut_var, 0.0, 0.5, length=160, resolution=0.01, bg=BG).pack(side=tk.LEFT)
        self._mut_lbl = tk.Label(mr, text="10%", width=5, bg=BG, fg=YEL, font=("Courier",9))
        self._mut_lbl.pack(side=tk.LEFT)
        self._mut_var.trace_add("write", self._upd_mut_lbl)
        prev_frm = LFrm(body, "Offspring Preview", padx=8, pady=6); prev_frm.pack(fill='x', pady=6)
        self._prev_txt = tk.Text(prev_frm, height=12, width=54, bg=BG3, fg=FG2,
                                  font=("Courier",8), state=tk.DISABLED); self._prev_txt.pack(fill='x')
        Btn(prev_frm, "Preview Genetics", cmd=self._preview,
            color='#3a3a8e', fg='#ffffff', font=("Courier",9,"bold")).pack(pady=4)
        tk.Label(body, textvariable=self._status_var, bg=BG, fg=GRN,
                 font=("Courier",8,"italic"), anchor='w').pack(fill='x', pady=4)
        br = Frm(body); br.pack(fill='x', pady=6)
        Btn(br, "⚗ Breed Offspring", cmd=self._breed,
            color='#8a1530', fg='#ffffff', font=("Courier",10,"bold"), padx=10).pack(side=tk.LEFT, padx=4)
        Btn(br, "Close", cmd=self.destroy, color=BG4, fg='#ffffff').pack(side=tk.LEFT, padx=4)
        self._center(parent)

    def _upd_mut_lbl(self, *_):
        try: self._mut_lbl.config(text=f"{int(self._mut_var.get()*100)}%")
        except: pass

    def _browse_a(self):
        fp = filedialog.askopenfilename(title="Select Parent A",
            filetypes=[("Creature","*.creature.npz"),("NPZ","*.npz"),("All","*.*")])
        if fp: self._pa_path.set(os.path.basename(fp)); self._pa_full = fp

    def _browse_b(self):
        fp = filedialog.askopenfilename(title="Select Parent B",
            filetypes=[("Creature","*.creature.npz"),("NPZ","*.npz"),("All","*.*")])
        if fp: self._pb_path.set(os.path.basename(fp)); self._pb_full = fp

    def _blend(self, a, b, mut):
        alpha = random.uniform(0.4, 0.6); v = alpha * a + (1 - alpha) * b
        if random.random() < mut:
            rng = abs(max(float(np.max(a)), float(np.max(b))) - min(float(np.min(a)), float(np.min(b)))) + 0.1
            v  += np.random.normal(0, 0.15 * rng, np.array(v).shape)
        return v

    def _blend_genetics(self, a, b, mut):
        alpha = random.uniform(0.4, 0.6)
        v = alpha * np.array(a, dtype=np.float64) + (1 - alpha) * np.array(b, dtype=np.float64)
        for j in range(len(v)):
            if random.random() < mut:
                v[j] += random.gauss(0, 0.18); v[j] = max(0.1, min(3.0, v[j]))
        return v

    def _preview(self):
        if not (self._pa_full and self._pb_full):
            self._status_var.set("Select both parents first."); return
        try:
            da = np.load(self._pa_full, allow_pickle=True)
            db = np.load(self._pb_full, allow_pickle=True)
            mut = float(self._mut_var.get())
            lines = ["Predicted offspring genetics:", ""]
            for key in ('B_W1','B_W2','S_W1','S_W2'):
                if key in da and key in db:
                    va, vb = da[key], db[key]
                    if va.shape == vb.shape:
                        blended = self._blend(va, vb, mut)
                        lines.append(f"  {key:6s}  shape={str(blended.shape):14s}"
                                     f"  mean={float(np.mean(blended)):+.4f}  std={float(np.std(blended)):.4f}")
            lines.append("")
            if 'genetics_emo' in da and 'genetics_emo' in db:
                ga = da['genetics_emo'].flatten(); gb = db['genetics_emo'].flatten()
                blended_g = self._blend_genetics(ga, gb, mut)
                lines.append("  Emotional susceptibility  (A → offspring ← B)")
                lines.append("  " + "─" * 50)
                for i, nm in enumerate(GeneticsProfile.EMO_NAMES[:len(blended_g)]):
                    a_v = float(ga[i]) if i < len(ga) else 1.0; b_v = float(gb[i]) if i < len(gb) else 1.0
                    bar_len = int(blended_g[i] / 3.0 * 20); bar = "█" * bar_len + "░" * (20 - bar_len)
                    lines.append(f"  {nm:10s}  {a_v:.2f} → [{bar}] {blended_g[i]:.3f} ← {b_v:.2f}")
            lines.append(f"\n  Mutation rate : {mut*100:.0f}%")
            lines.append(f"  Parent A: {self._pa_path.get()}"); lines.append(f"  Parent B: {self._pb_path.get()}")
            self._prev_txt.config(state=tk.NORMAL); self._prev_txt.delete(1.0, tk.END)
            self._prev_txt.insert(tk.END, '\n'.join(lines)); self._prev_txt.config(state=tk.DISABLED)
            self._status_var.set("Preview ready. Click Breed to create offspring.")
        except Exception as e: self._status_var.set(f"Preview error: {e}")

    def _breed(self):
        if not (self._pa_full and self._pb_full):
            self._status_var.set("Select both parents first."); return
        fp = filedialog.asksaveasfilename(title="Save Offspring Creature",
            defaultextension=".creature.npz",
            initialfile=self._default_name or "offspring",
            filetypes=[("Creature","*.creature.npz"),("All","*.*")])
        if not fp: return
        try:
            da = np.load(self._pa_full, allow_pickle=True)
            db = np.load(self._pb_full, allow_pickle=True)
            mut = float(self._mut_var.get()); out = {}
            out['creature_marker'] = np.array(True)
            out['lineage_a'] = np.array(self._pa_path.get()); out['lineage_b'] = np.array(self._pb_path.get())
            out['generation'] = np.array(max(int(da.get('generation', np.array(0))), int(db.get('generation', np.array(0)))) + 1)
            out['bred_at']    = np.array(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            GENETICS_KEYS = {'genetics_emo', 'genetics_inst'}
            for key in set(da.keys()) & set(db.keys()):
                try:
                    va, vb = np.array(da[key]), np.array(db[key])
                    if va.shape == vb.shape and va.dtype.kind in 'fc':
                        if key in GENETICS_KEYS:
                            blended = self._blend_genetics(va.flatten(), vb.flatten(), mut)
                            out[key] = np.array(blended, dtype=va.dtype).reshape(va.shape)
                        else: out[key] = self._blend(va, vb, mut).astype(va.dtype)
                    elif key not in ('creature_marker','soul_marker','generation','bred_at','lineage_a','lineage_b'):
                        out[key] = da[key]
                except Exception: pass
            for key in set(da.keys()) - set(db.keys()):
                if key not in out: out[key] = da[key]
            for key in set(db.keys()) - set(da.keys()):
                if key not in out: out[key] = db[key]
            if 'soul_mem_vecs' in da and 'soul_mem_vecs' in db:
                va = da['soul_mem_vecs'][:20]; vb = db['soul_mem_vecs'][:20]
                out['soul_mem_vecs']   = np.concatenate([va, vb], axis=0)
                out['soul_mem_labels'] = np.concatenate([
                    da.get('soul_mem_labels', np.array(['neutral']*len(va)))[:len(va)],
                    db.get('soul_mem_labels', np.array(['neutral']*len(vb)))[:len(vb)]])
            np.savez(fp, **out)
            gen = int(out.get('generation', np.array(1)))
            self._status_var.set(f"Offspring (Gen {gen}) saved to: {os.path.basename(fp)}")
            messagebox.showinfo("Breeding Complete",
                f"New creature (Generation {gen}) saved!\nParent A: {self._pa_path.get()}\n"
                f"Parent B: {self._pb_path.get()}\nMutation rate: {mut*100:.0f}%")
        except Exception as e:
            self._status_var.set(f"Breed error: {e}"); messagebox.showerror("Error", str(e))

    def _center(self, p):
        self.update_idletasks()
        x = p.winfo_rootx() + (p.winfo_width()  - self.winfo_width())  // 2
        y = p.winfo_rooty() + (p.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(0,x)}+{max(0,y)}")
