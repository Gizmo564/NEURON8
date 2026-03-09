#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  NEURON 8 — Main Launcher                                        ║
║  Central hub for NeuroSim · NeuroForge · NeuroLab · NeuroLife    ║
╚══════════════════════════════════════════════════════════════════╝
"""
import sys, os, subprocess, threading, glob, time, random, re, atexit
import tkinter as tk
from tkinter import ttk, messagebox

# ── Optional updater (gracefully absent if file is missing) ──
try:
    import updater as _updater
except ImportError:
    _updater = None            # type: ignore

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
        atexit.register(self.stop)

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
        self._latest_release = None   # populated by background update check
        self._update_btn     = None   # set in _build(); updated by bg check

        self._apply_style()
        self._build()

        # Music + copyright
        self._music = _MusicPlayer()
        self._add_footer_bar()
        self._music.start()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Silent background update check — runs 3 s after launch so startup feels instant
        if _updater is not None:
            self.after(3000, self._bg_check_updates)

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

        # Version tag — shown when updater is available
        if _updater is not None:
            ver = _updater.current_version()
            tk.Label(hdr, text=f"v{ver}",
                     bg=BG2, fg=BG4, font=("Courier", 8)).pack(pady=(4, 0))

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

        # Update button — hidden until background check finds a newer release
        if _updater is not None:
            self._update_btn = tk.Button(
                ftr,
                text="⬆  Check for Updates",
                command=self._open_update_dialog,
                bg=BG, fg=BG4,
                font=("Courier", 8), relief='flat',
                cursor='hand2', padx=6, pady=2,
                activebackground=BG3, activeforeground=FG2,
                bd=0, highlightthickness=0,
            )
            self._update_btn.pack(pady=(6, 0))

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
                        activebackground=BG3, activeforeground=color,
                        padx=10, pady=6, bd=1, highlightthickness=0)
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
                       activebackground=BG3, activeforeground=FG2, padx=4, pady=0, bd=1, highlightthickness=0)
        mb.pack(side=tk.RIGHT, padx=2)
        tk.Button(bar, text='⏭ skip', command=self._music.skip, bg=BG2, fg=BG4,
                  font=("Courier",7), relief='flat', cursor='hand2',
                  activebackground=BG3, activeforeground=FG2, padx=4, pady=0, bd=1, highlightthickness=0).pack(side=tk.RIGHT, padx=2)

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

    # ── Auto-update ───────────────────────────────────────────
    def _bg_check_updates(self):
        """Fetch latest release info on a daemon thread — never blocks the UI."""
        def _worker():
            release = _updater.fetch_latest_release()
            if release is None:
                return   # network unavailable — silently do nothing
            remote = release.get("tag_name", "").lstrip("v")
            local  = _updater.current_version()
            if _updater.is_newer(remote, local):
                self._latest_release = release
                # Marshal back to the Tk main thread to update the UI
                self.after(0, lambda: self._show_update_badge(remote))
        threading.Thread(target=_worker, daemon=True).start()

    def _show_update_badge(self, remote_ver: str):
        """Light up the update button to announce a new version."""
        if self._update_btn is None:
            return
        self._update_btn.config(
            text=f"⬆  Update available  v{_updater.current_version()} → v{remote_ver}",
            fg=GRN,
            font=("Courier", 8, "bold"),
            activeforeground=GRN,
        )
        self._status_var.set(
            f"Neuron 8 v{remote_ver} is available — click 'Update available' below."
        )

    def _open_update_dialog(self):
        """Open the update dialog. If a release is already cached, use it;
        otherwise do a fresh check first."""
        if self._latest_release is not None:
            _UpdateDialog(self, self._latest_release)
        else:
            # Manual check — show a brief 'checking…' message
            self._status_var.set("Checking for updates…")
            def _worker():
                release = _updater.fetch_latest_release()
                def _done():
                    if release is None:
                        self._status_var.set("Could not reach GitHub — check your connection.")
                        return
                    remote = release.get("tag_name", "").lstrip("v")
                    local  = _updater.current_version()
                    if _updater.is_newer(remote, local):
                        self._latest_release = release
                        self._show_update_badge(remote)
                        _UpdateDialog(self, release)
                    else:
                        self._status_var.set(
                            f"You are on the latest version (v{local})."
                        )
                self.after(0, _done)
            threading.Thread(target=_worker, daemon=True).start()


# ── Update dialog ─────────────────────────────────────────────────────────────
class _UpdateDialog(tk.Toplevel):
    """
    Modal dialog that shows release notes and drives the download/install.
    """
    def __init__(self, parent: tk.Tk, release: dict):
        super().__init__(parent)
        self._parent  = parent
        self._release = release
        self._remote  = release.get("tag_name", "?").lstrip("v")
        self._local   = _updater.current_version()

        self.title("Neuron 8 — Update Available")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build()

        # Centre over parent
        self.update_idletasks()
        px = parent.winfo_x(); py = parent.winfo_y()
        pw = parent.winfo_width(); ph = parent.winfo_height()
        w  = self.winfo_width();   h  = self.winfo_height()
        self.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=BG2, padx=20, pady=14); hdr.pack(fill='x')
        tk.Label(hdr, text="⬆  Update Available",
                 bg=BG2, fg=GRN, font=("Courier", 14, "bold")).pack(anchor='w')
        tk.Label(hdr,
                 text=f"  Installed: v{self._local}    →    Latest: v{self._remote}",
                 bg=BG2, fg=FG2, font=("Courier", 9)).pack(anchor='w', pady=(4, 0))

        # Release notes
        nf = tk.Frame(self, bg=BG, padx=16, pady=10); nf.pack(fill='both', expand=True)
        tk.Label(nf, text="Release notes:", bg=BG, fg=FG2,
                 font=("Courier", 8, "bold")).pack(anchor='w')
        notes_box = tk.Text(nf, height=10, width=58, bg=BG3, fg=FG,
                            font=("Courier", 8), wrap=tk.WORD,
                            relief='flat', bd=0, padx=8, pady=6,
                            state=tk.NORMAL)
        notes_box.insert("1.0", self._release.get("body") or "(no release notes)")
        notes_box.config(state=tk.DISABLED)
        notes_box.pack(fill='x', pady=(4, 0))

        # Progress area (hidden until install starts)
        self._prog_frame = tk.Frame(self, bg=BG, padx=16); self._prog_frame.pack(fill='x')
        self._prog_var   = tk.IntVar(value=0)
        self._prog_lbl   = tk.StringVar(value="")
        self._prog_bar   = ttk.Progressbar(self._prog_frame, variable=self._prog_var,
                                            maximum=100, length=440)
        self._prog_status = tk.Label(self._prog_frame, textvariable=self._prog_lbl,
                                      bg=BG, fg=FG2, font=("Courier", 8))

        # Buttons
        bf = tk.Frame(self, bg=BG, padx=16, pady=14); bf.pack(fill='x')
        self._install_btn = tk.Button(
            bf, text="  ⬇  Install Update  ",
            command=self._start_install,
            bg=GRN, fg=BG, font=("Courier", 10, "bold"),
            relief='flat', cursor='hand2',
            activebackground=BG3, activeforeground=GRN,
            padx=10, pady=6, bd=0, highlightthickness=0,
        )
        self._install_btn.pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(bf, text="Later", command=self.destroy,
                  bg=BG3, fg=FG2, font=("Courier", 9),
                  relief='flat', cursor='hand2',
                  activebackground=BG4, activeforeground=FG,
                  padx=8, pady=4, bd=0, highlightthickness=0,
                  ).pack(side=tk.LEFT)

        # GitHub link
        link = tk.Label(bf, text="View on GitHub ↗",
                        bg=BG, fg=BG4, font=("Courier", 8),
                        cursor='hand2')
        link.pack(side=tk.RIGHT)
        link.bind("<Button-1>", lambda _: self._open_github())
        link.bind("<Enter>",    lambda _: link.config(fg=ACN))
        link.bind("<Leave>",    lambda _: link.config(fg=BG4))

    def _open_github(self):
        import webbrowser
        url = self._release.get("html_url",
              f"https://github.com/{_updater.GITHUB_OWNER}/{_updater.GITHUB_REPO}/releases/latest")
        webbrowser.open(url)

    def _show_progress(self):
        self._prog_bar.pack(fill='x', pady=(8, 2))
        self._prog_status.pack(anchor='w', pady=(0, 6))

    def _progress_cb(self, fraction: float, text: str):
        """Called from the download thread — marshals updates to the Tk thread."""
        pct = max(0, min(100, int(fraction * 100)))
        self.after(0, lambda: self._prog_var.set(pct))
        self.after(0, lambda: self._prog_lbl.set(text))

    def _start_install(self):
        self._install_btn.config(state=tk.DISABLED, text="  Installing…  ")
        self._show_progress()

        def _worker():
            ok, msg = _updater.launch_update(self._release, self._progress_cb)
            self.after(0, lambda: self._on_install_done(ok, msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_install_done(self, ok: bool, msg: str):
        if ok:
            self._prog_lbl.set("✔ Update ready — Neuron 8 will restart automatically.")
            self._install_btn.config(
                state=tk.NORMAL, text="  Quit & Apply  ",
                command=self._quit_and_apply,
                bg=GRN,
            )
        else:
            self._prog_lbl.set(f"✖ {msg}")
            self._install_btn.config(
                state=tk.NORMAL, text="  Retry  ",
                command=self._start_install,
                bg=YEL, fg=BG,
            )

    def _quit_and_apply(self):
        """Close all open sub-apps and exit so the helper script can replace the files."""
        try:
            for proc in self._parent._running.values():
                if proc is not None and proc.poll() is None:
                    proc.terminate()
        except Exception:
            pass
        self._parent.destroy()


if __name__ == '__main__':
    app = Launcher()
    # Centre on screen
    app.update_idletasks()
    sw = app.winfo_screenwidth(); sh = app.winfo_screenheight()
    w  = app.winfo_width();       h  = app.winfo_height()
    app.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")
    app.mainloop()
