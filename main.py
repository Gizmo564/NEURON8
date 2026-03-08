#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  NEURON 8 — Unified entry point                                  ║
║  Used by PyInstaller to bundle all apps into a single executable ║
║                                                                  ║
║  Usage (frozen):   neuron8                     → opens launcher  ║
║                    neuron8 neuro_sim           → opens NeuroSim  ║
║                    neuron8 neuro_forge         → opens NeuroForge║
║                    neuron8 neuro_lab           → opens NeuroLab  ║
║                    neuron8 neuro_life          → opens NeuroLife ║
╚══════════════════════════════════════════════════════════════════╝
"""
import sys
import os

# When frozen by PyInstaller, add the bundle dir to sys.path so all
# modules (neuron8_core, neuro_sim, …) can be found.
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    if bundle_dir not in sys.path:
        sys.path.insert(0, bundle_dir)


def run_launcher():
    import launcher
    app = launcher.Launcher()
    app.update_idletasks()
    sw = app.winfo_screenwidth(); sh = app.winfo_screenheight()
    w  = app.winfo_width();       h  = app.winfo_height()
    app.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")
    app.mainloop()


def run_neuro_sim():
    import tkinter as tk
    from neuro_sim import App
    root = tk.Tk()
    App(root)
    root.mainloop()


def run_neuro_forge():
    from neuro_forge import NeuroForgeApp
    NeuroForgeApp().mainloop()


def run_neuro_lab():
    from neuro_lab import NeuroLabApp
    NeuroLabApp().mainloop()


def run_neuro_life():
    from neuro_life import NeuroLifeApp
    NeuroLifeApp().mainloop()


MODES = {
    'neuro_sim':   run_neuro_sim,
    'neuro_forge': run_neuro_forge,
    'neuro_lab':   run_neuro_lab,
    'neuro_life':  run_neuro_life,
}

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    if mode in MODES:
        MODES[mode]()
    else:
        run_launcher()
