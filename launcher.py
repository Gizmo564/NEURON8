#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  NEURON 8 — Main Launcher                                        ║
║  Central hub for NeuroSim · NeuroForge · NeuroLab · NeuroLife    ║
╚══════════════════════════════════════════════════════════════════╝
"""
import sys, os, subprocess, threading, glob, time, random, re
import tkinter as tk
from tkinter import ttk

# ── Colour palette ──────────────────────────────────────────
BG  = '#0f0f1a'; BG2 = '#1a1a2e'; BG3 = '#252545'; BG4 = '#2e2e50'
FG  = '#e0e0f0'; FG2 = '#9090b0'; ACN = '#7b8cde'; GRN = '#a6e3a1'
RED = '#f38ba8'; YEL = '#f9e2af'; PRP = '#cba6f7'; CYN = '#89dceb'

HERE = os.path.dirname(os.path.abspath(__file__))


# ── Inline music player (launcher has no core import) ───────
class _MusicPlayer:
    _BASE     = sys._MEIPASS if getattr(sys, 'frozen', False) else HERE
    MUSIC_DIR = os.path.join(_BASE, 'music')
    _FFPLAY   = os.path.join(_BASE, 'ffplay.exe' if sys.platform == 'win32' else 'ffplay') \
                if getattr(sys, 'frozen', False) else 'ffplay'

    def __init__(self):
        self._tracks: list = []
        self._index = 0
        self._proc = None
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._muted = False
        self._running = False
        self._track_var = None
        if os.path.isdir(self.MUSIC_DIR):
            self._tracks = sorted(glob.glob(os.path.join(self.MUSIC_DIR, '*.mp3')))
            random.shuffle(self._tracks)

    def _name(self, p):
        return re.sub(r'\s*-\s*.*$', '',
                      os.path.splitext(os.path.basename(p))[0].replace('_', ' '), count=1)[:36]

    def attach(self, v): self._track_var = v

    def start(self):
        if not self._tracks: return
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._running = False
        self._wake.set()
        self._kill()

    def skip(self):
        # Don't increment index here — the loop advances after wait() returns
        self._kill()

    def toggle_mute(self):
        self._muted = not self._muted
        if self._muted:
            self._kill()
            if self._track_var:
                try: self._track_var.set('♪ muted')
                except: pass
        else:
            self._wake.set()  # wake immediately from muted sleep

    @property
    def is_muted(self): return self._muted

    def _kill(self):
        with self._lock:
            p, self._proc = self._proc, None
        if p is not None:
            try:
                p.kill()
                p.wait(timeout=3)
            except Exception:
                pass

    def _loop(self):
        while self._running and self._tracks:
            if self._muted:
                self._wake.wait(timeout=0.4)
                self._wake.clear()
                continue
            path = self._tracks[self._index % len(self._tracks)]
            if self._track_var:
                try: self._track_var.set(f'♪ {self._name(path)}')
                except: pass
            try:
                with self._lock:
                    if not self._running: break
                    self._proc = subprocess.Popen(
                        [self._FFPLAY, '-nodisp', '-autoexit', '-loglevel', 'quiet', path],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    p = self._proc
                p.wait()
            except Exception:
                time.sleep(1)
                continue
            if not self._running: break
            if not self._muted:
                self._index = (self._index + 1) % len(self._tracks)
                if self._index == 0: random.shuffle(self._tracks)


APPS = [
    {
        "key":   "neuro_sim",
        "title": "NeuroSim",
        "icon":  "◉",
        "color": ACN,
        "desc":  "Primary creature runtime\nChat · Train · Care · Observe",
        "file":  "neuro_sim.py",
    },
    {
        "key":   "neuro_forge",
        "title": "NeuroForge",
        "icon":  "⚡",
        "color": YEL,
        "desc":  "Creature creation & pre-training\nForge from scratch · Blank nets",
        "file":  "neuro_forge.py",
    },
    {
        "key":   "neuro_lab",
        "title": "NeuroLab",
        "icon":  "⚗",
        "color": PRP,
        "desc":  "Deep editing & bulk training\nWeights · Genetics · Breeding",
        "file":  "neuro_lab.py",
    },
    {
        "key":   "neuro_life",
        "title": "NeuroLife",
        "icon":  "✦",
        "color": GRN,
        "desc":  "Multi-creature simulation\nInteraction · World · Social",
        "file":  "neuro_life.py",
    },
]


class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Neuron 8")
        self.configure(bg=BG)
        self.resizable(False, False)
        self._running: dict = {}   # key → subprocess.Popen
        self._apply_style()
        self._build()

        # Music + copyright
        self._music = _MusicPlayer()
        self._add_footer_bar()
        self._music.start()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        self._music.stop()
        self.destroy()

    def _apply_style(self):
        s = ttk.Style(); s.theme_use('clam')
        s.configure('.', background=BG, foreground=FG)
        s.configure('TLabel', background=BG, foreground=FG)
        s.configure('TFrame', background=BG)

    def _build(self):
        # ── Header ──────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG2, pady=18)
        hdr.pack(fill='x')
        tk.Label(hdr, text="N E U R O N   8",
                 bg=BG2, fg=ACN, font=("Courier", 26, "bold")).pack()
        tk.Label(hdr, text="Digital Creature Simulation Suite",
                 bg=BG2, fg=FG2, font=("Courier", 10, "italic")).pack(pady=(2, 0))

        sep = tk.Frame(self, bg=BG4, height=2)
        sep.pack(fill='x', padx=20, pady=(10, 0))

        # ── App tiles ───────────────────────────────────────
        grid = tk.Frame(self, bg=BG, padx=30, pady=20)
        grid.pack()

        for i, app in enumerate(APPS):
            col = i % 2; row = i // 2
            self._make_tile(grid, app, row, col)

        sep2 = tk.Frame(self, bg=BG4, height=2)
        sep2.pack(fill='x', padx=20, pady=(0, 10))

        # ── Footer ──────────────────────────────────────────
        ftr = tk.Frame(self, bg=BG, pady=8)
        ftr.pack(fill='x')
        self._status_var = tk.StringVar(value="Ready — launch any program above.")
        tk.Label(ftr, textvariable=self._status_var,
                 bg=BG, fg=FG2, font=("Courier", 8, "italic")).pack()
        tk.Label(ftr, text="All four programs share the same Neuron 8 creature format.",
                 bg=BG, fg=BG4, font=("Courier", 7)).pack(pady=(2, 0))

    def _make_tile(self, parent, app, row, col):
        color = app['color']

        outer = tk.Frame(parent, bg=BG3, padx=2, pady=2)
        outer.grid(row=row, column=col, padx=14, pady=10, sticky='nsew')

        inner = tk.Frame(outer, bg=BG2, padx=22, pady=18)
        inner.pack(fill='both', expand=True)

        # Icon + title
        top = tk.Frame(inner, bg=BG2); top.pack(fill='x')
        tk.Label(top, text=app['icon'], bg=BG2, fg=color,
                 font=("Courier", 28)).pack(side=tk.LEFT, padx=(0, 12))
        tk.Label(top, text=app['title'], bg=BG2, fg=color,
                 font=("Courier", 18, "bold"), anchor='w').pack(side=tk.LEFT)

        # Description
        tk.Label(inner, text=app['desc'], bg=BG2, fg=FG2,
                 font=("Courier", 9), justify='left', anchor='w').pack(
                 fill='x', pady=(8, 12))

        # Status indicator
        self._running[app['key']] = None
        stat_var = tk.StringVar(value="● idle")
        stat_lbl = tk.Label(inner, textvariable=stat_var,
                             bg=BG2, fg=BG4, font=("Courier", 8))
        stat_lbl.pack(anchor='w', pady=(0, 8))

        # Launch button
        btn = tk.Button(inner,
                        text=f"  Launch {app['title']}  ",
                        command=lambda a=app, sv=stat_var, sl=stat_lbl: self._launch(a, sv, sl),
                        bg=color, fg=BG,
                        font=("Courier", 10, "bold"),
                        relief='flat', cursor='hand2',
                        activebackground=BG4, activeforeground=FG,
                        padx=10, pady=6)
        btn.pack(fill='x')

        # Bind hover
        def _on(e, b=btn, c=color): b.config(bg=BG3, fg=c)
        def _off(e, b=btn, c=color): b.config(bg=c, fg=BG)
        btn.bind('<Enter>', _on); btn.bind('<Leave>', _off)

    def _add_footer_bar(self):
        # Copyright label
        tk.Label(self, text="© 2026 Volvi", bg=BG, fg=BG3,
                 font=("Courier", 7), anchor='e').pack(fill='x', padx=10, pady=(0,1))
        # Music bar
        bar = tk.Frame(self, bg=BG2, pady=3); bar.pack(fill='x')
        track_var = tk.StringVar(value='♪ loading…' if self._music._tracks else '♪ no music')
        self._music.attach(track_var)
        tk.Label(bar, textvariable=track_var, bg=BG2, fg=BG4,
                 font=("Courier", 7, "italic"), anchor='w').pack(side=tk.LEFT, padx=8)
        def _mute():
            self._music.toggle_mute()
            mb.config(text='▶ unmute' if self._music.is_muted else '⏸ mute',
                      fg=YEL if self._music.is_muted else BG4)
        mb = tk.Button(bar, text='⏸ mute', command=_mute, bg=BG2, fg=BG4,
                       font=("Courier",7), relief='flat', cursor='hand2',
                       activebackground=BG3, activeforeground=FG2, padx=4, pady=0, bd=0)
        mb.pack(side=tk.RIGHT, padx=2)
        tk.Button(bar, text='⏭ skip', command=self._music.skip, bg=BG2, fg=BG4,
                  font=("Courier",7), relief='flat', cursor='hand2',
                  activebackground=BG3, activeforeground=FG2, padx=4, pady=0, bd=0).pack(side=tk.RIGHT, padx=2)

    def _launch(self, app, stat_var, stat_lbl):
        key = app['key']

        # Build the subprocess command.
        # Frozen (PyInstaller): the exe re-invokes itself with the app key as argv[1].
        # Dev mode: run the .py script directly with the Python interpreter.
        FROZEN = getattr(sys, 'frozen', False)
        if FROZEN:
            cmd = [sys.executable, key]
        else:
            script = os.path.join(HERE, f"{key}.py")
            if not os.path.exists(script):
                # Fallback: try main.py routing
                main_py = os.path.join(HERE, 'main.py')
                if os.path.exists(main_py):
                    cmd = [sys.executable, main_py, key]
                else:
                    stat_var.set("✖ file not found")
                    stat_lbl.config(fg=RED)
                    self._status_var.set(f"Error: {app['file']} not found.")
                    return
            else:
                cmd = [sys.executable, script]
        # Check if already running
        proc = self._running.get(key)
        if proc is not None and proc.poll() is None:
            stat_var.set("● already running")
            stat_lbl.config(fg=YEL)
            return

        stat_var.set("● launching…")
        stat_lbl.config(fg=YEL)
        self._status_var.set(f"Launching {app['title']}…")

        def _run():
            try:
                p = subprocess.Popen(cmd)
                self._running[key] = p
                self.after(500, lambda: _update_status(p))
            except Exception as e:
                self.after(0, lambda: stat_var.set(f"✖ {e}"))
                self.after(0, lambda: stat_lbl.config(fg=RED))

        def _update_status(p):
            if p.poll() is None:
                stat_var.set("● running")
                stat_lbl.config(fg=GRN)
                self._status_var.set(f"{app['title']} is running.")
                self.after(3000, lambda: _poll(p))
            else:
                stat_var.set("● idle")
                stat_lbl.config(fg=BG4)

        def _poll(p):
            if p.poll() is None:
                self.after(3000, lambda: _poll(p))
            else:
                stat_var.set("● idle")
                stat_lbl.config(fg=BG4)
                self._status_var.set(f"{app['title']} closed.")

        threading.Thread(target=_run, daemon=True).start()


if __name__ == '__main__':
    app = Launcher()
    # Centre on screen
    app.update_idletasks()
    sw = app.winfo_screenwidth(); sh = app.winfo_screenheight()
    w  = app.winfo_width();       h  = app.winfo_height()
    app.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")
    app.mainloop()
