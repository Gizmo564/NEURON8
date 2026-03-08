#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  NEURON 8 — NeuroLab                                             ║
║  Deep editing · Weight analysis · Bulk training · Breeding       ║
╚══════════════════════════════════════════════════════════════════╝
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neuron8_core import (
    BG, BG2, BG3, BG4, FG, FG2, ACN, GRN, RED, YEL, PRP, CYN, ORG,
    _apply_dark_style, Lbl, Btn, DEntry, DSpin, DScale, Sep, Frm, LFrm,
    ScrollableFrame, Collapsible,
    text_to_vec, text_to_vec_hash, image_to_vec, vec_to_text, ALLOWED, A_CODES,
    EmotionState, InstinctSystem, GeneticsProfile, RelationalState,
    WordBigram, SoulNN, SimpleNN, make_face, _emotion_rgb,
    BreedingDialog, MusicPlayer, add_music_bar,
)

import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from PIL import Image, ImageTk
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading, datetime, math, random, json, re, csv

# ── Program-accent button: all buttons use PRP (NeuroLab purple) ──────────────
_Btn_core = Btn
def Btn(parent, text, cmd=None, color=None, fg=None, **kw):
    return _Btn_core(parent, text, cmd=cmd, color=PRP, fg=BG, **kw)


# ─────────────────────────────────────────────────────────────
#  Creature slot (holds one loaded creature)
# ─────────────────────────────────────────────────────────────
class CreatureSlot:
    def __init__(self):
        self.name     = ""
        self.nn       = None
        self.soul     = SoulNN(hidden=20)
        self.genetics = GeneticsProfile()
        self.emotions = EmotionState()
        self.instincts= InstinctSystem()
        self.relational = RelationalState()
        self.word_dict  = []
        self.bigram     = WordBigram()
        self.bigram_matrix = None
        self.bigram_vocab  = []
        self.source_path  = ""

    @property
    def loaded(self): return self.nn is not None

    def load_from_npz(self, fp):
        d = np.load(fp, allow_pickle=True)
        if 'B_W1' in d:
            in_s=int(d['B_input_size']); hid_s=int(d['B_hidden_size']); out_s=int(d['B_output_size'])
            self.nn = SimpleNN(in_s, hid_s, out_s, float(d.get('B_weight_init', np.array(0.1))))
            self.nn.W1=np.array(d['B_W1']); self.nn.b1=np.array(d['B_b1'])
            self.nn.W2=np.array(d['B_W2']); self.nn.b2=np.array(d['B_b2'])
            if 'B_W_h' in d: self.nn.W_h = np.array(d['B_W_h'])
            self.nn._init_momentum()
            self.name = str(d['B_name']) if 'B_name' in d else os.path.basename(fp)
        elif 'text_W1' in d:
            in_s=int(d['text_in']); hid_s=int(d['text_hid']); out_s=int(d['text_out'])
            self.nn = SimpleNN(in_s, hid_s, out_s)
            self.nn.W1=np.array(d['text_W1']); self.nn.b1=np.array(d['text_b1'])
            self.nn.W2=np.array(d['text_W2']); self.nn.b2=np.array(d['text_b2'])
            self.nn._init_momentum(); self.name = os.path.basename(fp)
        else: raise ValueError("Unrecognised creature/LTM file format.")
        if 'S_W1' in d:
            self.soul.W1=np.array(d['S_W1']); self.soul.b1=np.array(d['S_b1'])
            self.soul.W2=np.array(d['S_W2']); self.soul.b2=np.array(d['S_b2'])
            if 'S_experience' in d: self.soul.experience=float(d['S_experience'])
            if 'S_play_style' in d: self.soul.play_style=float(d['S_play_style'])
        if 'soul_mem_vecs' in d:
            v=d['soul_mem_vecs']; l=d['soul_mem_labels']
            self.soul._memory=[(v[i],str(l[i])) for i in range(len(v))]
        emo_order  = ['happiness','sadness','anger','fear','curiosity','calm']
        inst_order = ['hunger','tiredness','boredom','pain']
        if 'genetics_emo'  in d:
            g=d['genetics_emo'].flatten()
            for i,nm in enumerate(emo_order[:len(g)]): self.genetics.emo_susceptibility[nm]=float(g[i])
        if 'genetics_inst' in d:
            g=d['genetics_inst'].flatten()
            for i,nm in enumerate(inst_order[:len(g)]): self.genetics.inst_vulnerability[nm]=float(g[i])
        if 'word_dict' in d: self.word_dict=list(str(w) for w in d['word_dict'])
        if 'word_bigram_json' in d: self.bigram=WordBigram.from_json(str(d['word_bigram_json']))
        if 'bigram_matrix' in d and 'bigram_vocab' in d:
            self.bigram_matrix=d['bigram_matrix']; self.bigram_vocab=list(str(w) for w in d['bigram_vocab'])
        if 'relational_att' in d: self.relational.attachment=float(d['relational_att'])
        if 'relational_res' in d: self.relational.resentment=float(d['relational_res'])
        self.source_path = fp


# ─────────────────────────────────────────────────────────────
#  NeuroLab App
# ─────────────────────────────────────────────────────────────
class NeuroLabApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Neuron 8 — NeuroLab")
        self.configure(bg=BG); self.geometry("1340x900"); self.minsize(1100, 700)
        _apply_dark_style()
        self.slot = CreatureSlot()
        self._train_thread = None
        self._stop_flag    = False
        self._tag_images   = {}   # tag → list of vecs
        self._neuron_after = None
        self._build_ui()

        # Music + copyright footer
        self._music = MusicPlayer()
        add_music_bar(self, self._music)
        self._music.start()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=BG2, pady=6); hdr.pack(fill='x')
        tk.Label(hdr, text="  ⚗ NeuroLab", bg=BG2, fg=PRP,
                 font=("Courier",14,"bold")).pack(side=tk.LEFT)
        tk.Label(hdr, text="Deep editing · Training · Analysis · Breeding",
                 bg=BG2, fg=FG2, font=("Courier",9,"italic")).pack(side=tk.LEFT, padx=12)
        Btn(hdr, "Load Creature…", cmd=self._load_creature, color=PRP, fg=BG,
            font=("Courier",9,"bold")).pack(side=tk.RIGHT, padx=6)
        Btn(hdr, "Save Creature…", cmd=self._save_creature, color=GRN, fg=BG,
            font=("Courier",9,"bold")).pack(side=tk.RIGHT, padx=4)

        # Status bar
        self._status_var = tk.StringVar(value="No creature loaded — use 'Load Creature' above.")
        tk.Label(self, textvariable=self._status_var, bg=BG3, fg=FG2,
                 font=("Courier",8,"italic"), anchor='w', padx=8, pady=4).pack(fill='x')

        nb = ttk.Notebook(self); nb.pack(fill='both', expand=True, padx=6, pady=(4,0))
        self._nb = nb

        # Tab 1: Neuron Map + Overview
        t1 = tk.Frame(nb, bg=BG); nb.add(t1, text="  Neuron Map  ")
        self._build_map_tab(t1)

        # Tab 2: Genetics Editor
        t2 = tk.Frame(nb, bg=BG); nb.add(t2, text="  Genetics  ")
        self._build_genetics_tab(t2)

        # Tab 3: Weights Viewer
        t3 = tk.Frame(nb, bg=BG); nb.add(t3, text="  Weights  ")
        self._build_weights_tab(t3)

        # Tab 4: Bulk Training
        t4 = tk.Frame(nb, bg=BG); nb.add(t4, text="  Bulk Train  ")
        self._build_train_tab(t4)

        # Tab 5: Image Tagger
        t5 = tk.Frame(nb, bg=BG); nb.add(t5, text="  Image Tags  ")
        self._build_image_tab(t5)

        # Tab 6: Test Chat
        t6 = tk.Frame(nb, bg=BG); nb.add(t6, text="  Test Chat  ")
        self._build_test_tab(t6)

        # Tab 7: Breeding
        t7 = tk.Frame(nb, bg=BG); nb.add(t7, text="  Breeding  ")
        self._build_breed_tab(t7)

    # ── Tab 1: Neuron Map ─────────────────────────────────────
    def _build_map_tab(self, parent):
        left = tk.Frame(parent, bg=BG, width=500); left.pack(side=tk.LEFT, fill='both', expand=True)
        right = tk.Frame(parent, bg=BG2, width=320); right.pack(side=tk.RIGHT, fill='y', padx=(4,0))

        map_hdr = tk.Frame(left, bg=BG3, pady=4); map_hdr.pack(fill='x')
        tk.Label(map_hdr, text="  Live Neuron Activation Map", bg=BG3, fg=ACN,
                 font=("Courier",10,"bold")).pack(side=tk.LEFT, padx=8)
        self._map_hz_var = tk.DoubleVar(value=2.0)
        tk.Label(map_hdr, text="Hz:", bg=BG3, fg=FG2, font=("Courier",9)).pack(side=tk.LEFT, padx=(12,2))
        DScale(map_hdr, self._map_hz_var, 0.5, 10.0, bg=BG3, length=80, resolution=0.5).pack(side=tk.LEFT)
        self._map_running = tk.BooleanVar(value=False)
        self._map_toggle_btn = Btn(map_hdr, "▶ Start", cmd=self._toggle_map, color=GRN, fg=BG,
                                    font=("Courier",9,"bold"), padx=6)
        self._map_toggle_btn.pack(side=tk.LEFT, padx=8)

        fig_frame = tk.Frame(left, bg=BG); fig_frame.pack(fill='both', expand=True, padx=4, pady=4)
        self._map_fig, self._map_axes = plt.subplots(1, 3, figsize=(12, 5))
        self._map_fig.patch.set_facecolor(BG)
        self._map_canvas = FigureCanvasTkAgg(self._map_fig, master=fig_frame)
        self._map_canvas.get_tk_widget().pack(fill='both', expand=True)
        self._draw_blank_map()

        # Right info panel
        tk.Label(right, text="  Creature Info", bg=BG2, fg=ACN,
                 font=("Courier",10,"bold"), pady=6, anchor='w').pack(fill='x', padx=8)
        self._info_txt = tk.Text(right, height=20, bg=BG3, fg=FG, font=("Courier",8),
                                  state=tk.DISABLED, relief='flat', wrap=tk.WORD)
        self._info_txt.pack(fill='both', expand=True, padx=6, pady=4)
        Btn(right, "Refresh", cmd=self._refresh_info, color=BG4, fg='#ffffff',
            font=("Courier",8)).pack(anchor='e', padx=6, pady=2)

    def _draw_blank_map(self):
        for ax in self._map_axes:
            ax.set_facecolor(BG2); ax.set_xticks([]); ax.set_yticks([])
            ax.set_title("load a creature", color=FG2, fontsize=7, fontfamily='monospace')
        self._map_fig.tight_layout(pad=0.5)
        self._map_canvas.draw_idle()

    def _toggle_map(self):
        if self._map_running.get():
            self._map_running.set(False)
            self._map_toggle_btn.config(text="▶ Start", bg=GRN, fg=BG)
            if self._neuron_after: self.after_cancel(self._neuron_after)
        else:
            self._map_running.set(True)
            self._map_toggle_btn.config(text="■ Stop", bg=RED, fg='#ffffff')
            self._map_tick()

    def _map_tick(self):
        if not self._map_running.get(): return
        try: self._update_map()
        except: pass
        ms = max(100, int(1000.0 / max(0.1, self._map_hz_var.get())))
        self._neuron_after = self.after(ms, self._map_tick)

    def _update_map(self):
        nn = self.slot.nn
        if nn is None: return
        in_sz = nn.input_size; hid_sz = nn.hidden_size
        x = np.random.rand(1, in_sz).astype(np.float32) * 0.3
        out = nn.forward(x, noise=0.02)
        ax_in, ax_hid, ax_out = self._map_axes
        # Input activations
        sq_in = int(math.ceil(math.sqrt(in_sz))); pad_in = sq_in*sq_in - in_sz
        arr_in = np.concatenate([x.flatten(), np.zeros(pad_in)]).reshape(sq_in, sq_in)
        ax_in.clear(); ax_in.imshow(arr_in, cmap='plasma', vmin=0, vmax=1, aspect='auto')
        ax_in.set_title(f"Input [{in_sz}]", color=CYN, fontsize=7, fontfamily='monospace')
        ax_in.set_xticks([]); ax_in.set_yticks([])
        # Hidden activations
        h = nn.a1.flatten(); sq_h = int(math.ceil(math.sqrt(hid_sz))); pad_h = sq_h*sq_h - hid_sz
        arr_h = np.concatenate([h, np.zeros(pad_h)]).reshape(sq_h, sq_h)
        ax_hid.clear(); ax_hid.imshow(arr_h, cmap='viridis', vmin=0, vmax=1, aspect='auto')
        ax_hid.set_title(f"Hidden [{hid_sz}]", color=GRN, fontsize=7, fontfamily='monospace')
        ax_hid.set_xticks([]); ax_hid.set_yticks([])
        # Output activations
        out_sz = nn.output_size; sq_out = int(math.ceil(math.sqrt(out_sz))); pad_out = sq_out*sq_out - out_sz
        arr_out = np.concatenate([out.flatten(), np.zeros(pad_out)]).reshape(sq_out, sq_out)
        ax_out.clear(); ax_out.imshow(arr_out, cmap='inferno', vmin=0, vmax=1, aspect='auto')
        ax_out.set_title(f"Output [{out_sz}]", color=YEL, fontsize=7, fontfamily='monospace')
        ax_out.set_xticks([]); ax_out.set_yticks([])
        self._map_fig.patch.set_facecolor(BG)
        for ax in self._map_axes: ax.set_facecolor(BG2)
        self._map_fig.tight_layout(pad=0.5)
        self._map_canvas.draw_idle()

    def _refresh_info(self):
        nn = self.slot.nn
        lines = []
        if nn is None: lines = ["No creature loaded."]
        else:
            lines = [
                f"Name:         {self.slot.name}",
                f"Source:       {os.path.basename(self.slot.source_path)}",
                f"Architecture: {nn.input_size} → {nn.hidden_size} → {nn.output_size}",
                f"W1 shape:     {nn.W1.shape}",
                f"W2 shape:     {nn.W2.shape}",
                f"W_h shape:    {nn.W_h.shape}",
                f"W1 mean:      {nn.W1.mean():.5f}  std: {nn.W1.std():.5f}",
                f"W2 mean:      {nn.W2.mean():.5f}  std: {nn.W2.std():.5f}",
                f"Sup mem:      {len(nn._supervised_mem)} entries",
                f"Work mem:     {len(nn._working_mem)} entries",
                f"",
                f"Soul XP:      {self.slot.soul.experience:.3f}",
                f"Soul PS:      {self.slot.soul.play_style:.3f}",
                f"Soul mem:     {len(self.slot.soul._memory)} entries",
                f"",
                f"Dictionary:   {len(self.slot.word_dict)} words",
                f"Bigram:       {self.slot.bigram.vocab_size()} words  {len(self.slot.bigram)} pairs",
                f"",
                f"Genetics (emo susceptibility):",
            ]
            for k,v in self.slot.genetics.emo_susceptibility.items():
                lines.append(f"  {k:<12} {v:.3f}")
            lines.append("Genetics (inst vulnerability):")
            for k,v in self.slot.genetics.inst_vulnerability.items():
                lines.append(f"  {k:<12} {v:.3f}")
            lines += [f"","Relational:","  attachment  "+f"{self.slot.relational.attachment:.3f}",
                      "  resentment  "+f"{self.slot.relational.resentment:.3f}"]
        self._info_txt.config(state=tk.NORMAL)
        self._info_txt.delete(1.0, tk.END)
        self._info_txt.insert(tk.END, '\n'.join(lines))
        self._info_txt.config(state=tk.DISABLED)

    # ── Tab 2: Genetics Editor ────────────────────────────────
    def _build_genetics_tab(self, parent):
        sf = ScrollableFrame(parent); sf.pack(fill='both', expand=True)
        p  = sf.inner
        tk.Label(p, text="  Edit Genetics — changes take effect immediately on save",
                 bg=BG2, fg=YEL, font=("Courier",9,"italic"), pady=6, anchor='w').pack(fill='x')

        self._gen_vars = {}
        gen_frm = LFrm(p, "Emotional Susceptibility", padx=16, pady=8); gen_frm.pack(fill='x', padx=12, pady=6)
        for emo in ['happiness','sadness','anger','fear','curiosity','calm']:
            v = tk.DoubleVar(value=self.slot.genetics.emo_susceptibility.get(emo, 1.0))
            self._gen_vars[f'emo_{emo}'] = v
            row = Frm(gen_frm); row.pack(fill='x', pady=2)
            tk.Label(row, text=f"{emo:<12}", bg=BG2, fg=FG, font=("Courier",9), width=13, anchor='w').pack(side=tk.LEFT)
            DScale(row, v, 0.1, 3.0, bg=BG2, length=220, resolution=0.05).pack(side=tk.LEFT, padx=4)
            dv = tk.StringVar(value=f"{v.get():.2f}")
            tk.Label(row, textvariable=dv, bg=BG2, fg=ACN, font=("Courier",9), width=5).pack(side=tk.LEFT)
            def _make_upd(sv=dv, vv=v):
                def _u(*_): sv.set(f"{vv.get():.2f}")
                return _u
            v.trace_add("write", _make_upd())

        inst_frm = LFrm(p, "Instinct Vulnerability", padx=16, pady=8); inst_frm.pack(fill='x', padx=12, pady=6)
        for inst in ['hunger','tiredness','boredom','pain']:
            v = tk.DoubleVar(value=self.slot.genetics.inst_vulnerability.get(inst, 1.0))
            self._gen_vars[f'inst_{inst}'] = v
            row = Frm(inst_frm); row.pack(fill='x', pady=2)
            tk.Label(row, text=f"{inst:<12}", bg=BG2, fg=FG, font=("Courier",9), width=13, anchor='w').pack(side=tk.LEFT)
            DScale(row, v, 0.1, 3.0, bg=BG2, length=220, resolution=0.05).pack(side=tk.LEFT, padx=4)
            dv = tk.StringVar(value=f"{v.get():.2f}")
            tk.Label(row, textvariable=dv, bg=BG2, fg=ORG, font=("Courier",9), width=5).pack(side=tk.LEFT)
            def _make_upd2(sv=dv, vv=v):
                def _u(*_): sv.set(f"{vv.get():.2f}")
                return _u
            v.trace_add("write", _make_upd2())

        rel_frm = LFrm(p, "Relational State", padx=16, pady=8); rel_frm.pack(fill='x', padx=12, pady=6)
        self._att_var = tk.DoubleVar(value=self.slot.relational.attachment)
        self._res_var = tk.DoubleVar(value=self.slot.relational.resentment)
        for label, var, color in [("attachment", self._att_var, GRN), ("resentment", self._res_var, RED)]:
            row = Frm(rel_frm); row.pack(fill='x', pady=2)
            tk.Label(row, text=f"{label:<12}", bg=BG2, fg=FG, font=("Courier",9), width=13, anchor='w').pack(side=tk.LEFT)
            DScale(row, var, 0.0, 1.0, bg=BG2, length=220, resolution=0.02).pack(side=tk.LEFT, padx=4)
            dv = tk.StringVar(value=f"{var.get():.2f}")
            tk.Label(row, textvariable=dv, bg=BG2, fg=color, font=("Courier",9), width=5).pack(side=tk.LEFT)
            def _make_upd3(sv=dv, vv=var):
                def _u(*_): sv.set(f"{vv.get():.2f}")
                return _u
            var.trace_add("write", _make_upd3())

        bp = Frm(p); bp.pack(fill='x', padx=12, pady=8)
        Btn(bp, "Apply Genetics to Creature", cmd=self._apply_genetics,
            color=PRP, fg=BG, font=("Courier",10,"bold"), padx=10, pady=6).pack(side=tk.LEFT, padx=4)
        Btn(bp, "Reset to Defaults", cmd=self._reset_genetics,
            color=BG4, fg='#ffffff', font=("Courier",9), padx=8, pady=4).pack(side=tk.LEFT, padx=4)
        self._gen_status = tk.StringVar(value="")
        tk.Label(p, textvariable=self._gen_status, bg=BG, fg=GRN, font=("Courier",8,"italic")).pack(padx=12, anchor='w')

    def _apply_genetics(self):
        if not self.slot.loaded: messagebox.showwarning("No creature", "Load a creature first."); return
        for emo in ['happiness','sadness','anger','fear','curiosity','calm']:
            self.slot.genetics.emo_susceptibility[emo] = self._gen_vars[f'emo_{emo}'].get()
        for inst in ['hunger','tiredness','boredom','pain']:
            self.slot.genetics.inst_vulnerability[inst] = self._gen_vars[f'inst_{inst}'].get()
        self.slot.relational.attachment = self._att_var.get()
        self.slot.relational.resentment = self._res_var.get()
        self._gen_status.set(f"Genetics applied — save creature to persist.")

    def _reset_genetics(self):
        for emo in ['happiness','sadness','anger','fear','curiosity','calm']:
            self._gen_vars[f'emo_{emo}'].set(1.0)
        for inst in ['hunger','tiredness','boredom','pain']:
            self._gen_vars[f'inst_{inst}'].set(1.0)
        self._att_var.set(0.5); self._res_var.set(0.1)

    # ── Tab 3: Weights Viewer ─────────────────────────────────
    def _build_weights_tab(self, parent):
        # ── Layer selector + utility buttons ─────────────────────────────
        ctrl = tk.Frame(parent, bg=BG3, pady=6); ctrl.pack(fill='x')
        self._w_layer = tk.StringVar(value='W1')
        for v,t in [('W1','W1 (inp→hid)'),('W2','W2 (hid→out)'),('W_h','W_h (recurrent)')]:
            tk.Radiobutton(ctrl, text=t, variable=self._w_layer, value=v,
                           bg=BG3, fg=ACN, selectcolor=BG4, font=("Courier",9),
                           command=self._draw_weights, activebackground=BG3).pack(side=tk.LEFT, padx=10)
        Btn(ctrl, "Draw",            cmd=self._draw_weights, color=ACN, fg=BG, font=("Courier",9,"bold")).pack(side=tk.RIGHT, padx=8)
        Btn(ctrl, "Add Noise ±0.01", cmd=self._add_noise,   color=YEL, fg=BG, font=("Courier",9,"bold")).pack(side=tk.RIGHT, padx=4)

        # ── Heatmap ───────────────────────────────────────────────────────
        self._w_fig = plt.figure(figsize=(10, 5)); self._w_fig.patch.set_facecolor(BG)
        self._w_canvas = FigureCanvasTkAgg(self._w_fig, master=parent)
        self._w_canvas.get_tk_widget().pack(fill='both', expand=True, padx=8, pady=4)
        # Click-to-select a weight cell
        self._w_sel_row = None; self._w_sel_col = None
        self._w_canvas.mpl_connect('button_press_event', self._on_weight_click)

        # ── Weight editor row ─────────────────────────────────────────────
        edit_frm = tk.Frame(parent, bg=BG4, pady=6); edit_frm.pack(fill='x', padx=8, pady=(0,2))
        self._w_sel_lbl = tk.StringVar(value="Click a cell in the heatmap to select a weight  →  then use + / − buttons")
        tk.Label(edit_frm, textvariable=self._w_sel_lbl, bg=BG4, fg=FG2,
                 font=("Courier",8), anchor='w', width=52).pack(side=tk.LEFT, padx=8)

        # Delta step radios
        self._w_delta = tk.DoubleVar(value=0.01)
        tk.Label(edit_frm, text="Δ:", bg=BG4, fg=CYN, font=("Courier",9,"bold")).pack(side=tk.LEFT, padx=(4,2))
        for dv, dl in [(0.001,"0.001"),(0.01,"0.01"),(0.05,"0.05"),(0.1,"0.1"),(0.5,"0.5")]:
            tk.Radiobutton(edit_frm, text=dl, variable=self._w_delta, value=dv,
                           bg=BG4, fg=YEL, selectcolor=BG3, activebackground=BG4,
                           font=("Courier",8)).pack(side=tk.LEFT, padx=2)

        tk.Label(edit_frm, text=" ", bg=BG4).pack(side=tk.LEFT, padx=4)
        Btn(edit_frm, "+  Add Δ", cmd=lambda: self._nudge_weight(+1),
            color=GRN, fg=BG, font=("Courier",9,"bold"), padx=10).pack(side=tk.LEFT, padx=2)
        Btn(edit_frm, "−  Sub Δ", cmd=lambda: self._nudge_weight(-1),
            color=RED, fg='#ffffff', font=("Courier",9,"bold"), padx=10).pack(side=tk.LEFT, padx=2)
        Btn(edit_frm, "Zero", cmd=lambda: self._set_weight(0.0),
            color=BG3, fg='#ffffff', font=("Courier",8), padx=6).pack(side=tk.LEFT, padx=2)

        # Stats
        stats_frm = tk.Frame(parent, bg=BG3, pady=4); stats_frm.pack(fill='x')
        self._w_stats = tk.StringVar(value="")
        tk.Label(stats_frm, textvariable=self._w_stats, bg=BG3, fg=FG2,
                 font=("Courier",8), anchor='w').pack(padx=10)

    def _on_weight_click(self, event):
        """Handle matplotlib click on the weight heatmap — select a cell."""
        if event.inaxes is None: return
        nn = self.slot.nn
        if nn is None: return
        layer = self._w_layer.get()
        W = {'W1': nn.W1, 'W2': nn.W2, 'W_h': nn.W_h}.get(layer, nn.W1)
        col = int(round(event.xdata)); row = int(round(event.ydata))
        rows, cols = W.shape
        if not (0 <= row < rows and 0 <= col < cols): return
        self._w_sel_row = row; self._w_sel_col = col
        val = float(W[row, col])
        self._w_sel_lbl.set(f"Selected: {layer}[row={row}, col={col}]  =  {val:.6f}     (use + / − to modify)")
        self._draw_weights()   # redraw so selection marker updates

    def _nudge_weight(self, sign: int):
        """Add or subtract delta from the selected weight cell."""
        nn = self.slot.nn
        if nn is None: return
        if self._w_sel_row is None:
            self._status_var.set("Click a weight cell first."); return
        layer = self._w_layer.get()
        W = {'W1': nn.W1, 'W2': nn.W2, 'W_h': nn.W_h}.get(layer, nn.W1)
        r, c = self._w_sel_row, self._w_sel_col
        rows, cols = W.shape
        if not (0 <= r < rows and 0 <= c < cols): return
        delta = float(self._w_delta.get()) * sign
        W[r, c] = float(W[r, c]) + delta
        val = float(W[r, c])
        self._w_sel_lbl.set(f"Selected: {layer}[row={r}, col={c}]  =  {val:.6f}     (use + / − to modify)")
        self._status_var.set(f"  {layer}[{r},{c}] {'+'if sign>0 else ''}{delta:.4f}  →  {val:.6f}")
        self._draw_weights()

    def _set_weight(self, value: float):
        """Set selected weight cell to an exact value."""
        nn = self.slot.nn
        if nn is None: return
        if self._w_sel_row is None:
            self._status_var.set("Click a weight cell first."); return
        layer = self._w_layer.get()
        W = {'W1': nn.W1, 'W2': nn.W2, 'W_h': nn.W_h}.get(layer, nn.W1)
        r, c = self._w_sel_row, self._w_sel_col
        if not (0 <= r < W.shape[0] and 0 <= c < W.shape[1]): return
        W[r, c] = np.float32(value)
        self._w_sel_lbl.set(f"Selected: {layer}[row={r}, col={c}]  =  {value:.6f}")
        self._status_var.set(f"  {layer}[{r},{c}] set to {value}")
        self._draw_weights()

    def _draw_weights(self):
        nn = self.slot.nn
        if nn is None: return
        layer = self._w_layer.get()
        W = {'W1': nn.W1, 'W2': nn.W2, 'W_h': nn.W_h}.get(layer, nn.W1)
        self._w_fig.clear()
        ax = self._w_fig.add_subplot(111)
        ax.set_facecolor(BG2)
        vmax = np.abs(W).max() or 1.0
        im = ax.imshow(W, cmap='RdBu', vmin=-vmax, vmax=vmax, aspect='auto', interpolation='nearest')
        self._w_fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
        ax.set_title(f"Layer {layer}  shape={W.shape}", color=FG, fontfamily='monospace', fontsize=9)
        ax.set_xlabel("Input neurons",  color=FG2, fontsize=7)
        ax.set_ylabel("Output neurons", color=FG2, fontsize=7)
        ax.tick_params(colors=FG2, labelsize=6)
        # Draw selection marker
        if self._w_sel_row is not None and self._w_sel_col is not None:
            r, c = self._w_sel_row, self._w_sel_col
            if 0 <= r < W.shape[0] and 0 <= c < W.shape[1]:
                rect = plt.Rectangle((c-0.5, r-0.5), 1, 1, linewidth=2,
                                     edgecolor='#ffffff', facecolor='none', linestyle='--')
                ax.add_patch(rect)
        self._w_fig.patch.set_facecolor(BG); self._w_fig.tight_layout()
        self._w_canvas.draw_idle()
        self._w_stats.set(f"  {layer}: shape={W.shape}  mean={W.mean():.5f}  std={W.std():.5f}  min={W.min():.4f}  max={W.max():.4f}")

    def _add_noise(self):
        nn = self.slot.nn
        if nn is None: return
        nn.W1 += np.random.randn(*nn.W1.shape).astype(np.float32) * 0.01
        nn.W2 += np.random.randn(*nn.W2.shape).astype(np.float32) * 0.01
        self._draw_weights(); self._status_var.set("Noise added to W1, W2.")

    # ── Tab 4: Bulk Training ──────────────────────────────────
    def _build_train_tab(self, parent):
        left  = tk.Frame(parent, bg=BG, width=420); left.pack(side=tk.LEFT, fill='y', padx=(8,4), pady=8)
        right = tk.Frame(parent, bg=BG); right.pack(side=tk.LEFT, fill='both', expand=True, padx=(4,8), pady=8)

        # Input source
        src_frm = LFrm(left, "Training Source", padx=10, pady=8); src_frm.pack(fill='x')
        self._train_mode = tk.StringVar(value='qa')
        for v,t,c in [('qa','Q&A Pairs (below)',ACN),('csv','CSV File',YEL),('txt_vocab','Text File — Vocab',GRN),('txt_assoc','Text File — Bigram',PRP)]:
            tk.Radiobutton(src_frm, text=t, variable=self._train_mode, value=v,
                           bg=BG2, fg=c, selectcolor=BG3, font=("Courier",9),
                           command=self._on_train_mode, activebackground=BG2).pack(anchor='w', padx=4, pady=1)
        Btn(src_frm, "Browse File…", cmd=self._browse_train_file, color=BG4, fg='#ffffff',
            font=("Courier",9)).pack(fill='x', pady=(6,0))
        self._train_file_lbl = tk.Label(src_frm, text="no file", bg=BG2, fg=FG2,
                                         font=("Courier",8), anchor='w', wraplength=320)
        self._train_file_lbl.pack(fill='x', pady=2)
        self._train_file = None

        # Inline Q&A
        qa_frm = LFrm(left, "Q&A Pairs", padx=10, pady=8); qa_frm.pack(fill='both', expand=True, pady=4)
        self._train_qa_pairs = []
        qi = Frm(qa_frm, bg=BG2); qi.pack(fill='x')
        self._tqa_p = tk.StringVar(); self._tqa_r = tk.StringVar()
        DEntry(qi, textvariable=self._tqa_p, width=16, font=("Courier",8)).pack(side=tk.LEFT, padx=2)
        tk.Label(qi, text="→", bg=BG2, fg=FG2, font=("Courier",9)).pack(side=tk.LEFT)
        DEntry(qi, textvariable=self._tqa_r, width=16, font=("Courier",8)).pack(side=tk.LEFT, padx=2)
        Btn(qi, "+", cmd=self._add_train_qa, color=GRN, fg=BG, font=("Courier",10,"bold"), padx=4).pack(side=tk.LEFT)
        qb = Frm(qa_frm, bg=BG2); qb.pack(fill='x', pady=2)
        Btn(qb, "Import CSV", cmd=self._import_train_csv, color=ACN, fg=BG, font=("Courier",8,"bold")).pack(side=tk.LEFT, padx=2)
        Btn(qb, "Clear",      cmd=self._clear_train_qa,   color=RED, fg='#ffffff', font=("Courier",8,"bold")).pack(side=tk.LEFT, padx=2)
        self._tqa_count = tk.Label(qb, text="0 pairs", bg=BG2, fg=FG2, font=("Courier",8))
        self._tqa_count.pack(side=tk.LEFT, padx=8)
        self._tqa_lb = tk.Listbox(qa_frm, height=8, bg=BG3, fg=FG, font=("Courier",8), selectbackground=ACN, relief='flat')
        self._tqa_lb.pack(fill='both', expand=True, pady=2)
        Btn(qa_frm, "Remove selected", cmd=self._rem_train_qa, color=BG4, fg='#ffffff', font=("Courier",8)).pack(anchor='w')

        # Training params (right panel)
        params = LFrm(right, "Parameters", padx=10, pady=8); params.pack(fill='x')
        pr = Frm(params); pr.pack(fill='x', pady=2)
        Lbl(pr, "Epochs:", font=("Courier",9)).pack(side=tk.LEFT)
        self._bt_epochs = tk.IntVar(value=400); DSpin(pr, self._bt_epochs, 1, 20000, inc=100, width=7).pack(side=tk.LEFT, padx=4)
        Lbl(pr, "  LR:", font=("Courier",9)).pack(side=tk.LEFT)
        self._bt_lr = tk.DoubleVar(value=0.015); DScale(pr, self._bt_lr, 0.001, 0.2, length=120, resolution=0.001).pack(side=tk.LEFT, padx=4)
        pr2 = Frm(params); pr2.pack(fill='x', pady=2)
        self._bt_cosine = tk.BooleanVar(value=True)
        tk.Checkbutton(pr2, text="Cosine LR", variable=self._bt_cosine, bg=BG2, fg=FG2, selectcolor=BG3, font=("Courier",9), activebackground=BG2).pack(side=tk.LEFT, padx=4)
        self._bt_hebbian = tk.BooleanVar(value=False)
        tk.Checkbutton(pr2, text="Hebbian during train", variable=self._bt_hebbian, bg=BG2, fg=GRN, selectcolor=BG3, font=("Courier",9), activebackground=BG2).pack(side=tk.LEFT, padx=4)
        self._bt_consolidate = tk.BooleanVar(value=True)
        tk.Checkbutton(pr2, text="Consolidate after", variable=self._bt_consolidate, bg=BG2, fg=PRP, selectcolor=BG3, font=("Courier",9), activebackground=BG2).pack(side=tk.LEFT, padx=4)

        # Run buttons
        rb = Frm(right); rb.pack(fill='x', pady=6)
        self._train_btn = Btn(rb, "▶ Run Training", cmd=self._start_bulk_train,
                               color=GRN, fg=BG, font=("Courier",11,"bold"), padx=10, pady=6)
        self._train_btn.pack(side=tk.LEFT, padx=4)
        self._train_stop_btn = Btn(rb, "■ Stop", cmd=self._stop_bulk_train,
                                    color=RED, fg='#ffffff', font=("Courier",10,"bold"), padx=8)
        self._train_stop_btn.pack(side=tk.LEFT, padx=4); self._train_stop_btn.config(state=tk.DISABLED)

        # Progress
        pf = Frm(right); pf.pack(fill='x')
        self._bt_prog_var = tk.IntVar(value=0)
        self._bt_phase_var = tk.StringVar(value="")
        tk.Label(pf, textvariable=self._bt_phase_var, bg=BG, fg=FG2, font=("Courier",8), width=18).pack(side=tk.LEFT, padx=4)
        ttk.Progressbar(pf, variable=self._bt_prog_var, maximum=100, length=280).pack(side=tk.LEFT)

        # Log
        log_frm = LFrm(right, "Training Log", padx=6, pady=4); log_frm.pack(fill='both', expand=True, pady=4)
        self._bt_log = tk.Text(log_frm, height=14, bg='#0a0a18', fg=FG2, font=("Courier",8),
                                state=tk.DISABLED, wrap=tk.WORD, relief='flat')
        bt_sb = ttk.Scrollbar(log_frm, command=self._bt_log.yview); self._bt_log.config(yscrollcommand=bt_sb.set)
        bt_sb.pack(side=tk.RIGHT, fill='y'); self._bt_log.pack(fill='both', expand=True)

    def _on_train_mode(self, *_): pass
    def _browse_train_file(self):
        mode = self._train_mode.get()
        ft = [("All","*.*")]
        if 'csv' in mode: ft = [("CSV","*.csv"),("All","*.*")]
        elif 'txt' in mode: ft = [("Text","*.txt"),("All","*.*")]
        fp = filedialog.askopenfilename(filetypes=ft)
        if fp: self._train_file = fp; self._train_file_lbl.config(text=os.path.basename(fp))

    def _add_train_qa(self):
        p=self._tqa_p.get().strip(); r=self._tqa_r.get().strip()
        if p and r:
            self._train_qa_pairs.append((p,r)); self._tqa_lb.insert(tk.END, f"{p[:22]} → {r[:22]}")
            self._tqa_p.set(''); self._tqa_r.set('')
            self._tqa_count.config(text=f"{len(self._train_qa_pairs)} pairs")
    def _rem_train_qa(self):
        sel=self._tqa_lb.curselection()
        if sel: self._train_qa_pairs.pop(sel[0]); self._tqa_lb.delete(sel[0]); self._tqa_count.config(text=f"{len(self._train_qa_pairs)} pairs")
    def _clear_train_qa(self): self._train_qa_pairs.clear(); self._tqa_lb.delete(0,tk.END); self._tqa_count.config(text="0 pairs")
    def _import_train_csv(self):
        fp=filedialog.askopenfilename(filetypes=[("CSV","*.csv"),("All","*.*")])
        if not fp: return
        try:
            with open(fp,newline='',encoding='utf-8',errors='ignore') as f:
                for row in csv.reader(f):
                    if len(row)>=2 and row[0].strip():
                        self._train_qa_pairs.append((row[0].strip(),row[1].strip()))
                        self._tqa_lb.insert(tk.END, f"{row[0][:22]} → {row[1][:22]}")
            self._tqa_count.config(text=f"{len(self._train_qa_pairs)} pairs")
        except Exception as e: messagebox.showerror("Error",str(e))

    def _bt_log_msg(self, msg, tag='data'):
        self.after(0, lambda m=msg, t=tag: self._write_bt_log(m,t))
    def _write_bt_log(self, msg, tag='data'):
        self._bt_log.config(state=tk.NORMAL); self._bt_log.insert(tk.END, msg+'\n'); self._bt_log.see(tk.END); self._bt_log.config(state=tk.DISABLED)

    def _start_bulk_train(self):
        if not self.slot.loaded: messagebox.showwarning("No creature","Load a creature first."); return
        if self._train_thread and self._train_thread.is_alive(): return
        self._stop_flag = False
        self._train_btn.config(state=tk.DISABLED); self._train_stop_btn.config(state=tk.NORMAL)
        self._train_thread = threading.Thread(target=self._bulk_train_worker, daemon=True)
        self._train_thread.start()

    def _stop_bulk_train(self): self._stop_flag = True

    def _bulk_train_worker(self):
        nn = self.slot.nn; mode = self._train_mode.get()
        epochs = int(self._bt_epochs.get()); lr = float(self._bt_lr.get())
        cosine = self._bt_cosine.get(); min_lr = lr * 0.08
        self._bt_log_msg(f"▸ Training start  mode={mode}  epochs={epochs}  lr={lr:.4f}", 'ok')
        pairs = []
        try:
            if mode == 'qa': pairs = list(self._train_qa_pairs)
            elif mode == 'csv' and self._train_file:
                with open(self._train_file, newline='', encoding='utf-8', errors='ignore') as f:
                    for row in csv.reader(f):
                        if len(row)>=2 and row[0].strip(): pairs.append((row[0].strip(),row[1].strip()))
                self._bt_log_msg(f"  Loaded {len(pairs)} pairs from CSV.")
            elif mode == 'txt_vocab' and self._train_file:
                with open(self._train_file, encoding='utf-8', errors='ignore') as f: raw=f.read()
                words=[w.strip().lower() for w in re.split(r'\W+',raw) if w.strip().isalpha()]
                words=sorted(set(words))
                for w in words:
                    if w not in self.slot.word_dict: self.slot.word_dict.append(w)
                self.slot.word_dict.sort()
                self._bt_log_msg(f"  Added {len(words)} words to dictionary.  Total: {len(self.slot.word_dict)}")
                self.after(0, lambda: self._status_var.set(f"Vocabulary updated: {len(self.slot.word_dict)} words"))
                self.after(0, lambda: self._train_btn.config(state=tk.NORMAL))
                self.after(0, lambda: self._train_stop_btn.config(state=tk.DISABLED))
                return
            elif mode == 'txt_assoc' and self._train_file:
                with open(self._train_file, encoding='utf-8', errors='ignore') as f: raw=f.read()
                self.slot.bigram.record_text(raw)
                self._bt_log_msg(f"  Bigram updated: {self.slot.bigram.vocab_size()} words")
                self.after(0, lambda: self._train_btn.config(state=tk.NORMAL))
                self.after(0, lambda: self._train_stop_btn.config(state=tk.DISABLED))
                return

            if not pairs: self._bt_log_msg("  No pairs to train on. Add Q&A or load a CSV/file."); return
            total_mse = 0.0
            for ep in range(1, epochs+1):
                if self._stop_flag: break
                clr = lr if not cosine else (min_lr + 0.5*(lr-min_lr)*(1+math.cos(math.pi*ep/epochs)))
                random.shuffle(pairs); ep_mse = 0.0
                for pr, rsp in pairs:
                    x=text_to_vec(pr,nn.input_size); t=text_to_vec(rsp,nn.output_size)
                    nn.forward(x); ep_mse += nn.train_supervised(x,t,lr=clr)
                    self.slot.bigram.record_text(pr+" "+rsp)
                avg = ep_mse/len(pairs); total_mse = avg
                pct = int(ep/epochs*100)
                self.after(0, lambda p=pct,m=avg,e=ep: (self._bt_prog_var.set(p), self._bt_phase_var.set(f"ep {e}/{epochs}")))
                if ep % max(1,epochs//15) == 0: self._bt_log_msg(f"  ep {ep:>6}/{epochs}  lr={clr:.5f}  mse={avg:.5f}")
            if self._bt_consolidate.get():
                nn.consolidate(passes=3, lr=lr*0.3); nn.supervised_consolidate(passes=2, lr=lr*0.2)
                self._bt_log_msg(f"  Consolidation done.")
            if self._bt_hebbian.get(): nn.hebbian_update(eta=0.0005, decay=0.000002); self._bt_log_msg("  Hebbian update done.")
            self._bt_log_msg(f"✓ Training complete  final_mse={total_mse:.6f}")
        except Exception as e:
            self._bt_log_msg(f"✗ Error: {e}")
        finally:
            self.after(0, lambda: self._train_btn.config(state=tk.NORMAL))
            self.after(0, lambda: self._train_stop_btn.config(state=tk.DISABLED))

    # ── Tab 5: Image Tagger ───────────────────────────────────
    def _build_image_tab(self, parent):
        self._img_dim = 16
        left = tk.Frame(parent, bg=BG, width=480); left.pack(side=tk.LEFT, fill='both', expand=True)
        right = tk.Frame(parent, bg=BG2, width=300); right.pack(side=tk.RIGHT, fill='y')

        tk.Label(left, text="  Batch Image Upload & Tagging", bg=BG3, fg=PRP,
                 font=("Courier",10,"bold"), pady=6, anchor='w').pack(fill='x')
        ctl = Frm(left); ctl.pack(fill='x', padx=8, pady=4)
        Btn(ctl, "Upload Images…", cmd=self._upload_batch_images,
            color=PRP, fg=BG, font=("Courier",10,"bold"), padx=8).pack(side=tk.LEFT, padx=4)
        Btn(ctl, "Train Selected Tag", cmd=self._train_tag,
            color=GRN, fg=BG, font=("Courier",10,"bold"), padx=8).pack(side=tk.LEFT, padx=4)
        Btn(ctl, "Train All Tags", cmd=self._train_all_tags,
            color=YEL, fg=BG, font=("Courier",9,"bold"), padx=6).pack(side=tk.LEFT, padx=4)
        Btn(ctl, "Clear All", cmd=self._clear_tags, color=RED, fg='#ffffff', font=("Courier",9), padx=4).pack(side=tk.LEFT, padx=4)

        self._tag_tree = ttk.Treeview(left, columns=('tag','count','preview'), show='headings', height=14)
        for c,w in [('tag',160),('count',80),('preview',200)]:
            self._tag_tree.heading(c,text=c.capitalize()); self._tag_tree.column(c,width=w)
        self._tag_tree.pack(fill='both', expand=True, padx=8, pady=4)
        self._tag_tree.bind('<ButtonRelease-1>', self._on_tag_select)

        self._tag_log = tk.Label(left, text="", bg=BG, fg=FG2, font=("Courier",8), anchor='w')
        self._tag_log.pack(fill='x', padx=8, pady=2)

        # Right: preview
        tk.Label(right, text="  Preview", bg=BG2, fg=FG2,
                 font=("Courier",9,"italic"), pady=4, anchor='w').pack(fill='x', padx=6)
        self._tag_preview_canvas = tk.Canvas(right, bg='#000000', width=192, height=192,
                                              highlightthickness=1, highlightbackground=BG4)
        self._tag_preview_canvas.pack(padx=8, pady=8)
        self._tp_ref = None
        self._tp_tag_lbl = tk.Label(right, text="", bg=BG2, fg=FG2, font=("Courier",8), anchor='center')
        self._tp_tag_lbl.pack()
        Btn(right, "Generate from Tag", cmd=self._generate_tag_img,
            color=PRP, fg=BG, font=("Courier",9,"bold")).pack(fill='x', padx=8, pady=6)
        self._tag_epochs_var = tk.IntVar(value=200)
        tr = Frm(right, bg=BG2); tr.pack(fill='x', padx=8)
        Lbl(tr, "Train epochs:", bg=BG2, font=("Courier",8)).pack(side=tk.LEFT)
        DSpin(tr, self._tag_epochs_var, 10, 5000, inc=50, width=6).pack(side=tk.LEFT, padx=4)
        self._tag_lr_var = tk.DoubleVar(value=0.02)
        Lbl(tr, "  LR:", bg=BG2, font=("Courier",8)).pack(side=tk.LEFT)
        DScale(tr, self._tag_lr_var, 0.001, 0.15, bg=BG2, length=80, resolution=0.001).pack(side=tk.LEFT, padx=2)

    def _upload_batch_images(self):
        paths = filedialog.askopenfilenames(filetypes=[("Images","*.png *.jpg *.jpeg *.bmp *.gif"),("All","*.*")])
        if not paths: return
        tag = simpledialog.askstring("Tag", "Enter a tag for these images:", parent=self)
        if not tag: return
        tag = tag.strip().lower()
        if tag not in self._tag_images: self._tag_images[tag] = []
        # Derive dimension from loaded creature if available, else fall back to default
        if self.slot.loaded and self.slot.nn is not None:
            import math
            d = int(math.isqrt(self.slot.nn.input_size))
            if d * d != self.slot.nn.input_size:
                messagebox.showwarning("Non-square input",
                    f"Creature input_size ({self.slot.nn.input_size}) is not a perfect square. "
                    f"Using d={d} (d²={d*d}). Some neurons will be unused.")
        else:
            d = self._img_dim
        for p in paths:
            try:
                v = image_to_vec(p, (d, d))
                self._tag_images[tag].append(v.flatten())
            except: pass
        self._refresh_tag_tree()
        self._tag_log.config(text=f"Uploaded {len(paths)} images to tag '{tag}'  ({len(self._tag_images[tag])} total)")

    def _refresh_tag_tree(self):
        for row in self._tag_tree.get_children(): self._tag_tree.delete(row)
        for tag, vecs in self._tag_images.items():
            n = len(vecs); preview = f"{n} images · avg vec {np.mean([v.mean() for v in vecs]):.3f}"
            self._tag_tree.insert('', 'end', values=(tag, n, preview))

    def _on_tag_select(self, event):
        sel = self._tag_tree.selection()
        if sel: tag = self._tag_tree.item(sel[0])['values'][0]; self._tp_tag_lbl.config(text=f"Selected: {tag}")

    def _train_tag(self):
        sel = self._tag_tree.selection()
        if not sel: return
        tag = self._tag_tree.item(sel[0])['values'][0]; self._train_tag_impl(tag)

    def _train_all_tags(self):
        for tag in list(self._tag_images.keys()): self._train_tag_impl(tag)

    def _train_tag_impl(self, tag):
        if not self.slot.loaded: messagebox.showwarning("No creature","Load a creature first."); return
        vecs = self._tag_images.get(tag, [])
        if not vecs: return
        nn = self.slot.nn; epochs = int(self._tag_epochs_var.get()); lr = float(self._tag_lr_var.get())
        import math
        d = int(math.isqrt(nn.input_size)); in_sz = d * d
        # Pad or truncate stored vectors to match nn.input_size
        def _fit_vec(v):
            v = np.array(v).flatten()
            if len(v) == nn.input_size: return v
            out = np.zeros(nn.input_size, dtype=np.float32)
            out[:min(len(v), nn.input_size)] = v[:nn.input_size]
            return out
        def _worker():
            for ep in range(epochs):
                for v in vecs:
                    x = np.clip(_fit_vec(v),0,1).reshape(1,-1).astype(np.float32)
                    nn.forward(x); nn.train(x, lr=lr*max(0.1, 1-ep/epochs))
                if ep % max(1,epochs//10)==0:
                    self.after(0, lambda e=ep: self._tag_log.config(text=f"Training '{tag}'… ep {e}/{epochs}"))
            self.after(0, lambda: self._tag_log.config(text=f"✓ Tag '{tag}' trained ({epochs} epochs)."))
        threading.Thread(target=_worker, daemon=True).start()

    def _generate_tag_img(self):
        sel = self._tag_tree.selection()
        if not sel: return
        tag = self._tag_tree.item(sel[0])['values'][0]
        if tag not in self._tag_images: return
        nn = self.slot.nn
        if nn is None: return
        vecs = self._tag_images[tag]
        mean_vec = np.mean(vecs, axis=0).reshape(1,-1).astype(np.float32)
        nn.reset_hidden(); out = nn.forward(mean_vec, noise=0.05)
        import math
        d = int(math.isqrt(nn.input_size)); pix = np.clip(out.flatten()[:d*d],0,1)
        rgb = (np.stack([pix,pix*0.8,pix*1.2],axis=-1)*255).astype(np.uint8)
        small = Image.fromarray(rgb.reshape(d,d,3),'RGB'); big = small.resize((192,192),Image.NEAREST)
        ph = ImageTk.PhotoImage(big); self._tp_ref = ph
        self._tag_preview_canvas.delete("all"); self._tag_preview_canvas.create_image(0,0,anchor='nw',image=ph)

    def _clear_tags(self): self._tag_images.clear(); self._refresh_tag_tree()

    # ── Tab 6: Test Chat ──────────────────────────────────────
    def _build_test_tab(self, parent):
        left = tk.Frame(parent, bg=BG, width=440); left.pack(side=tk.LEFT, fill='y')
        right = tk.Frame(parent, bg=BG2, width=380); right.pack(side=tk.LEFT, fill='both', expand=True)

        tk.Label(left, text="  Test Chat — prompt / response & image gen",
                 bg=BG3, fg=ACN, font=("Courier",10,"bold"), pady=6, anchor='w').pack(fill='x')

        self._tc_log = tk.Text(left, height=22, bg='#0a0a18', fg=FG, font=("Courier",9),
                                state=tk.DISABLED, wrap=tk.WORD, relief='flat')
        tc_sb = ttk.Scrollbar(left, command=self._tc_log.yview); self._tc_log.config(yscrollcommand=tc_sb.set)
        tc_sb.pack(side=tk.RIGHT, fill='y'); self._tc_log.pack(fill='both', expand=True, padx=4, pady=4)
        self._tc_log.tag_config('you',      foreground=YEL, font=("Courier",9,"bold"))
        self._tc_log.tag_config('creature', foreground=CYN, font=("Courier",9))
        self._tc_log.tag_config('sys',      foreground=BG4, font=("Courier",8,"italic"))

        inp_frm = tk.Frame(left, bg=BG3, pady=4); inp_frm.pack(fill='x')
        self._tc_entry = DEntry(inp_frm, width=32, font=("Courier",9)); self._tc_entry.pack(side=tk.LEFT, padx=6)
        self._tc_entry.bind('<Return>', lambda e: self._tc_send())
        Btn(inp_frm, "Send", cmd=self._tc_send, color=ACN, fg=BG, font=("Courier",9,"bold")).pack(side=tk.LEFT)
        Btn(inp_frm, "Clear", cmd=lambda: (self._tc_log.config(state=tk.NORMAL), self._tc_log.delete(1.0,tk.END), self._tc_log.config(state=tk.DISABLED)), color=BG4, fg='#ffffff', font=("Courier",8)).pack(side=tk.LEFT, padx=4)

        # Right: image gen
        tk.Label(right, text="  Image Generation Test", bg=BG2, fg=PRP,
                 font=("Courier",10,"bold"), pady=6, anchor='w').pack(fill='x', padx=8)
        self._tc_img_canvas = tk.Canvas(right, bg='#000011', width=256, height=256,
                                         highlightthickness=1, highlightbackground=BG4)
        self._tc_img_canvas.pack(padx=16, pady=8)
        self._tc_img_ref = None
        Btn(right, "Generate from last prompt", cmd=self._tc_generate_image,
            color=PRP, fg=BG, font=("Courier",9,"bold")).pack(fill='x', padx=16)
        self._tc_noise_var = tk.DoubleVar(value=0.05)
        nr = Frm(right, bg=BG2); nr.pack(fill='x', padx=16, pady=4)
        Lbl(nr, "Noise:", bg=BG2, font=("Courier",9)).pack(side=tk.LEFT)
        DScale(nr, self._tc_noise_var, 0.0, 0.5, bg=BG2, length=120, resolution=0.01).pack(side=tk.LEFT, padx=4)
        self._tc_last_prompt = ""

    def _tc_send(self):
        nn = self.slot.nn
        if nn is None: self._tc_log_append('sys', "(no creature loaded)"); return
        msg = self._tc_entry.get().strip()
        if not msg: return
        self._tc_entry.delete(0, tk.END); self._tc_last_prompt = msg
        self._tc_log_append('you', f"You: {msg}")
        x = text_to_vec_hash(msg, nn.input_size)
        nn.reset_hidden(); out = nn.forward(x, noise=float(self._tc_noise_var.get()))
        flat = out.flatten()
        wd = self.slot.word_dict
        if wd:
            words = []
            for _ in range(8):
                best=''; best_sim=-1.0; v_n=flat/(np.linalg.norm(flat)+1e-9)
                for w in wd:
                    wv = text_to_vec_hash(w,nn.input_size).flatten(); wv/=(np.linalg.norm(wv)+1e-9)
                    s=float(np.dot(v_n,wv))
                    if s>best_sim: best_sim=s; best=w
                words.append(best); nn.reset_hidden(); flat=nn.forward(text_to_vec_hash(best,nn.input_size),noise=0).flatten()
            resp = ' '.join(words)
        else: resp = ''.join(chr(int(v*255)) if 32<=int(v*255)<=126 else '.' for v in flat[:40])
        self._tc_log_append('creature', f"  → {resp}")

    def _tc_log_append(self, tag, text):
        self._tc_log.config(state=tk.NORMAL); self._tc_log.insert(tk.END, text+'\n', tag)
        self._tc_log.see(tk.END); self._tc_log.config(state=tk.DISABLED)

    def _tc_generate_image(self):
        nn = self.slot.nn
        if nn is None: return
        p = self._tc_last_prompt or "hello"
        x = text_to_vec_hash(p, nn.input_size); nn.reset_hidden()
        out = nn.forward(x, noise=float(self._tc_noise_var.get())); flat = out.flatten()
        import math
        d = int(math.isqrt(nn.output_size)) if nn.output_size >= 4 else 16
        pix = np.clip(flat[:d*d],0,1)
        r_e,g_e,b_e = (0.7, 0.6, 0.9)
        r=np.clip(pix*r_e,0,1); g=np.clip(pix*g_e,0,1); b=np.clip(pix*b_e,0,1)
        rgb=(np.stack([r,g,b],axis=-1)*255).astype(np.uint8)
        small=Image.fromarray(rgb.reshape(d,d,3),'RGB'); big=small.resize((256,256),Image.NEAREST)
        ph=ImageTk.PhotoImage(big); self._tc_img_ref=ph
        self._tc_img_canvas.delete("all"); self._tc_img_canvas.create_image(0,0,anchor='nw',image=ph)

    # ── Tab 7: Breeding ───────────────────────────────────────
    def _build_breed_tab(self, parent):
        self._breed_slots = [None, None]  # two creature paths
        header = tk.Frame(parent, bg=BG3, pady=8); header.pack(fill='x')
        tk.Label(header, text="  Intentional Breeding Lab", bg=BG3, fg=GRN,
                 font=("Courier",12,"bold")).pack(side=tk.LEFT, padx=10)
        tk.Label(header, text="Load two creatures, review their genetics, then breed.",
                 bg=BG3, fg=FG2, font=("Courier",9,"italic")).pack(side=tk.LEFT, padx=8)

        slots_frm = tk.Frame(parent, bg=BG); slots_frm.pack(fill='x', padx=12, pady=8)
        self._breed_labels = []
        for i in range(2):
            sf = LFrm(slots_frm, f"Parent {i+1}", padx=12, pady=8)
            sf.pack(side=tk.LEFT, fill='both', expand=True, padx=(0 if i==0 else 8, 0))
            lbl = tk.Label(sf, text="(empty)", bg=BG2, fg=FG2, font=("Courier",9,"italic"), anchor='w')
            lbl.pack(fill='x'); self._breed_labels.append(lbl)
            idx = i
            Btn(sf, f"Load Parent {i+1}…", cmd=lambda n=idx: self._load_breed_slot(n),
                color=ACN, fg=BG, font=("Courier",9,"bold")).pack(fill='x', pady=(6,0))

        info_frm = LFrm(parent, "Genetics Preview", padx=12, pady=8); info_frm.pack(fill='x', padx=12, pady=4)
        self._breed_info = tk.Text(info_frm, height=6, bg=BG3, fg=FG2, font=("Courier",8),
                                    state=tk.DISABLED, relief='flat')
        self._breed_info.pack(fill='x')

        out_frm = LFrm(parent, "Offspring Settings", padx=12, pady=8); out_frm.pack(fill='x', padx=12, pady=4)
        or_ = Frm(out_frm); or_.pack(fill='x')
        Lbl(or_, "Name:", font=("Courier",9)).pack(side=tk.LEFT)
        self._breed_name = tk.StringVar(value="Offspring")
        DEntry(or_, textvariable=self._breed_name, width=18, font=("Courier",10)).pack(side=tk.LEFT, padx=6)
        Lbl(or_, "  Blend P1:", font=("Courier",9)).pack(side=tk.LEFT)
        self._breed_blend = tk.DoubleVar(value=0.5)
        DScale(or_, self._breed_blend, 0.0, 1.0, length=120, resolution=0.05).pack(side=tk.LEFT, padx=4)
        self._blend_lbl = tk.Label(or_, text="0.50", bg=BG, fg=FG2, font=("Courier",8), width=5)
        self._blend_lbl.pack(side=tk.LEFT)
        self._breed_blend.trace_add("write", lambda *_: self._blend_lbl.config(text=f"{self._breed_blend.get():.2f}"))

        br_row = Frm(parent); br_row.pack(fill='x', padx=12, pady=8)
        Btn(br_row, "  ⚡ BREED  ", cmd=self._run_breed, color=GRN, fg=BG,
            font=("Courier",12,"bold"), padx=12, pady=8).pack(side=tk.LEFT)
        self._breed_status = tk.StringVar(value="")
        tk.Label(parent, textvariable=self._breed_status, bg=BG, fg=GRN,
                 font=("Courier",9,"italic")).pack(padx=12, anchor='w')

    def _load_breed_slot(self, idx):
        fp = filedialog.askopenfilename(title="Select Creature",
            filetypes=[("Creature","*.creature.npz"),("NPZ","*.npz"),("All","*.*")])
        if not fp: return
        try:
            cs = CreatureSlot(); cs.load_from_npz(fp)
            self._breed_slots[idx] = cs
            self._breed_labels[idx].config(text=f"{cs.name}\n{os.path.basename(fp)}")
            self._update_breed_info()
        except Exception as e: messagebox.showerror("Error", str(e))

    def _update_breed_info(self):
        lines = []
        for i, cs in enumerate(self._breed_slots):
            if cs is None: lines.append(f"Parent {i+1}: (empty)"); continue
            lines.append(f"Parent {i+1}: {cs.name}  [{cs.nn.input_size if cs.nn else '?'} → {cs.nn.hidden_size if cs.nn else '?'}]")
            for k,v in cs.genetics.emo_susceptibility.items(): lines.append(f"   emo_{k}: {v:.2f}")
        self._breed_info.config(state=tk.NORMAL); self._breed_info.delete(1.0,tk.END)
        self._breed_info.insert(tk.END, '\n'.join(lines)); self._breed_info.config(state=tk.DISABLED)

    def _run_breed(self):
        p1, p2 = self._breed_slots
        if p1 is None or p2 is None: messagebox.showwarning("Missing parents","Load two parents first."); return
        if not p1.loaded or not p2.loaded: messagebox.showwarning("Not loaded","Both parents need valid neural nets."); return
        # Open full BreedingDialog
        BreedingDialog(self, p1.source_path, p2.source_path,
                       default_name=self._breed_name.get(),
                       default_blend=self._breed_blend.get())
        self._breed_status.set("Breeding dialog opened.")

    # ── Load / Save ───────────────────────────────────────────
    def _load_creature(self):
        fp = filedialog.askopenfilename(title="Load Creature",
            filetypes=[("Creature","*.creature.npz"),("LTM","*.ltm.npz"),("All","*.*")])
        if not fp: return
        try:
            self.slot.load_from_npz(fp)
            self._status_var.set(f"Loaded: {self.slot.name}  [{self.slot.nn.input_size}→{self.slot.nn.hidden_size}]  {len(self.slot.word_dict)} words")
            self._refresh_info()
            self._update_genetics_ui()
            self._draw_blank_map()
        except Exception as e: messagebox.showerror("Error", str(e))

    def _update_genetics_ui(self):
        for emo in ['happiness','sadness','anger','fear','curiosity','calm']:
            if f'emo_{emo}' in self._gen_vars:
                self._gen_vars[f'emo_{emo}'].set(self.slot.genetics.emo_susceptibility.get(emo, 1.0))
        for inst in ['hunger','tiredness','boredom','pain']:
            if f'inst_{inst}' in self._gen_vars:
                self._gen_vars[f'inst_{inst}'].set(self.slot.genetics.inst_vulnerability.get(inst, 1.0))
        self._att_var.set(self.slot.relational.attachment); self._res_var.set(self.slot.relational.resentment)

    def _save_creature(self):
        if not self.slot.loaded: messagebox.showwarning("No creature","Load a creature first."); return
        fp = filedialog.asksaveasfilename(title="Save Creature",
            defaultextension=".creature.npz",
            filetypes=[("Creature","*.creature.npz"),("All","*.*")])
        if not fp: return
        try:
            nn = self.slot.nn; ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            emo_order  = ['happiness','sadness','anger','fear','curiosity','calm']
            inst_order = ['hunger','tiredness','boredom','pain']
            ge = np.array([self.slot.genetics.emo_susceptibility[e] for e in emo_order], dtype=np.float32)
            gi = np.array([self.slot.genetics.inst_vulnerability[i] for i in inst_order], dtype=np.float32)
            if self.slot.soul._memory:
                raw_vecs = [np.array(m[0]).flatten() for m in self.slot.soul._memory]
                max_len  = max(len(v) for v in raw_vecs)
                padded   = [np.pad(v, (0, max_len - len(v))) for v in raw_vecs]
                vecs   = np.array(padded, dtype=np.float32)
                labels = np.array([m[1] for m in self.slot.soul._memory])
            else:
                vecs   = np.zeros((0, 6), dtype=np.float32)
                labels = np.array([])
            payload = dict(
                creature_marker=np.array(True), B_W1=nn.W1, B_b1=nn.b1, B_W2=nn.W2, B_b2=nn.b2, B_W_h=nn.W_h,
                B_input_size=np.array(nn.input_size), B_hidden_size=np.array(nn.hidden_size),
                B_output_size=np.array(nn.output_size), B_weight_init=np.array(nn.weight_init),
                B_name=np.array(self.slot.name),
                S_W1=self.slot.soul.W1, S_b1=self.slot.soul.b1, S_W2=self.slot.soul.W2, S_b2=self.slot.soul.b2,
                S_experience=np.array(self.slot.soul.experience), S_play_style=np.array(self.slot.soul.play_style),
                soul_mem_vecs=vecs, soul_mem_labels=labels,
                relational_att=np.array(self.slot.relational.attachment),
                relational_res=np.array(self.slot.relational.resentment),
                word_dict=np.array(self.slot.word_dict) if self.slot.word_dict else np.array([]),
                word_bigram_json=np.array(self.slot.bigram.to_json()),
                bigram_matrix=self.slot.bigram_matrix if self.slot.bigram_matrix is not None else np.zeros((0,0)),
                bigram_vocab=np.array(self.slot.bigram_vocab) if self.slot.bigram_vocab else np.array([]),
                genetics_emo=ge, genetics_inst=gi,
                saved_at=np.array(ts), forged_by=np.array("NeuroLab_N8"),
            )
            np.savez(fp, **payload)
            self._status_var.set(f"Saved: {os.path.basename(fp)}")
            messagebox.showinfo("Saved", f"Saved:\n{fp}")
        except Exception as e: messagebox.showerror("Error", str(e))


if __name__ == '__main__':
    NeuroLabApp().mainloop()
