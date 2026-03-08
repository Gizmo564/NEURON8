#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  NEURON 8 — NeuroSim                                             ║
║  Primary creature runtime: chat · train · care · observe         ║
║  Requires a creature created in NeuroForge to get started        ║
╚══════════════════════════════════════════════════════════════════╝
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neuron8_core import (
    BG, BG2, BG3, BG4, FG, FG2, ACN, GRN, RED, YEL, PRP, CYN, ORG,
    _apply_dark_style, Lbl, Btn, DEntry, DSpin, DScale, Sep, Frm, LFrm,
    ScrollableFrame, Collapsible, HISTORY_LIMIT,
    text_to_vec, image_to_vec, text_to_vec_hash, vec_to_text, ALLOWED, A_CODES,
    EmotionState, InstinctSystem, GeneticsProfile, RelationalState,
    WordBigram, TagImageMemory, InternalRewardSystem, VisualCortex,
    SoulNN, SimpleNN, make_face, _emotion_rgb,
    EmotionPanel, InstinctPanel, SoulPanel, RelationalStatusPanel, HistoryPanel,
    MusicPlayer, add_music_bar,
)

import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from PIL import Image, ImageTk
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading, datetime, math, random, json, queue, re

# ── Program-accent button: all buttons use ACN (NeuroSim blue-purple) ─────────
_Btn_core = Btn
def Btn(parent, text, cmd=None, color=None, fg=None, **kw):
    return _Btn_core(parent, text, cmd=cmd, color=ACN, fg=BG, **kw)


# ─────────────────────────────────────────────────────────────
#  Utility Dialogs
# ─────────────────────────────────────────────────────────────
class DictionaryEditorDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app; self.title("Word Dictionary Editor")
        self.configure(bg=BG); self.grab_set(); self.geometry("480x520")
        tk.Label(self, text="  Word Dictionary", bg=BG2, fg=ACN,
                 font=("Courier",13,"bold"), padx=10, pady=8, anchor='w').pack(fill='x')
        tk.Label(self, text=f"  {len(app.word_dict)} words loaded",
                 bg=BG2, fg=FG2, font=("Courier",8), padx=10, anchor='w').pack(fill='x')
        efrm = Frm(self, padx=10, pady=4); efrm.pack(fill='x')
        DEntry(efrm, width=30).pack(side=tk.LEFT, padx=(0,6))
        self._entry = efrm.winfo_children()[-1]
        Btn(efrm, "Add", cmd=self._add, color=GRN, fg=BG, font=("Courier",9,"bold")).pack(side=tk.LEFT, padx=2)
        Btn(efrm, "Remove", cmd=self._rem, color=RED, fg=BG, font=("Courier",9,"bold")).pack(side=tk.LEFT, padx=2)
        fr = tk.Frame(self, bg=BG3); fr.pack(fill='both', expand=True, padx=10, pady=4)
        self._lb = tk.Listbox(fr, bg=BG3, fg=FG, font=("Courier",9), selectbackground=ACN, relief='flat')
        sb = ttk.Scrollbar(fr, command=self._lb.yview); self._lb.config(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill='y'); self._lb.pack(side=tk.LEFT, fill='both', expand=True)
        Btn(self, "Close", cmd=self.destroy, color=BG4, fg='#ffffff').pack(pady=8)
        self._refresh()
    def _refresh(self):
        self._lb.delete(0, tk.END)
        for w in sorted(self.app.word_dict): self._lb.insert(tk.END, w)
    def _add(self):
        w = self._entry.get().strip().lower()
        if w and w not in self.app.word_dict:
            self.app.word_dict.append(w); self.app.word_dict.sort()
            self.app._whc_matrix = None; self._entry.delete(0, tk.END); self._refresh()
    def _rem(self):
        sel = self._lb.curselection()
        if not sel: return
        w = self._lb.get(sel[0])
        if w in self.app.word_dict: self.app.word_dict.remove(w); self.app._whc_matrix = None; self._refresh()


class TagManagerDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app; self.title("Image Tag Manager")
        self.configure(bg=BG); self.grab_set(); self.geometry("560x600")
        tk.Label(self, text="  Image Tag Manager", bg=BG2, fg=PRP,
                 font=("Courier",13,"bold"), padx=10, pady=8, anchor='w').pack(fill='x')
        pf = Frm(self, padx=10); pf.pack(fill='x', pady=6)
        Btn(pf, "Upload Image", cmd=self._upload, color=ACN, fg=BG,
            font=("Courier",9,"bold")).pack(side=tk.LEFT, padx=4)
        Btn(pf, "Delete Tag",  cmd=self._delete, color=RED, fg='#ffffff',
            font=("Courier",9,"bold")).pack(side=tk.LEFT, padx=4)
        Btn(pf, "Generate",    cmd=self._generate, color=PRP, fg=BG,
            font=("Courier",9,"bold")).pack(side=tk.LEFT, padx=4)
        cols = ('Tag', 'Images', 'Preview')
        self._tv = ttk.Treeview(self, columns=cols, show='headings', height=12)
        for c in cols: self._tv.heading(c, text=c); self._tv.column(c, width=120)
        self._tv.pack(fill='both', expand=True, padx=10, pady=4)
        Btn(self, "Close", cmd=self.destroy, color=BG4, fg='#ffffff').pack(pady=8)
        self._refresh()

    def _refresh(self):
        for row in self._tv.get_children(): self._tv.delete(row)
        for tag in self.app.tag_image_mem.tags():
            n = self.app.tag_image_mem.count(tag)
            self._tv.insert('', 'end', values=(tag, n, f"{n} stored vecs"))

    def _upload(self):
        paths = filedialog.askopenfilenames(
            title="Select image(s)", filetypes=[("Images","*.png *.jpg *.jpeg *.bmp"),("All","*.*")])
        if not paths: return
        tag = simpledialog.askstring("Tag", "Enter a tag for these images:", parent=self)
        if not tag: return
        img_nn = self.app.nn_store.get('image')
        if img_nn is None:
            messagebox.showwarning("No image net", "Train an image network first."); return
        for p in paths:
            try:
                d = self.app.cfg_img_dim
                v = image_to_vec(p, (d, d))
                out = img_nn.forward(v)
                self.app.tag_image_mem.record(tag, img_nn.a1.copy(), 1.0)
                self.app.tag_registry[tag] = self.app.tag_registry.get(tag, 0) + 1
            except Exception as e:
                messagebox.showerror("Error", str(e))
        self._refresh()

    def _delete(self):
        sel = self._tv.selection()
        if not sel: return
        tag = self._tv.item(sel[0])['values'][0]
        if tag in self.app.tag_image_mem.store: del self.app.tag_image_mem.store[tag]
        if tag in self.app.tag_registry:         del self.app.tag_registry[tag]
        self._refresh()

    def _generate(self):
        sel = self._tv.selection()
        if not sel: return
        tag = self._tv.item(sel[0])['values'][0]
        self.app._render_tag_image([self.app.tag_image_mem.blend(tag)])


class TextTrainDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app; self.title("Train from Text File")
        self.configure(bg=BG); self.grab_set(); self.geometry("480x380")
        tk.Label(self, text="  Train from Text File", bg=BG2, fg=YEL,
                 font=("Courier",13,"bold"), padx=10, pady=8, anchor='w').pack(fill='x')
        Btn(self, "Browse…", cmd=self._browse, color=YEL, fg=BG, font=("Courier",9,"bold")).pack(pady=8, padx=10, anchor='w')
        self._path_lbl = tk.Label(self, text="No file selected", bg=BG, fg=FG2, font=("Courier",8))
        self._path_lbl.pack(padx=10, anchor='w')
        mf = Frm(self, padx=10); mf.pack(fill='x', pady=6)
        tk.Label(mf, text="Mode:", bg=BG, fg=FG, font=("Courier",9)).pack(side=tk.LEFT)
        self._mode = tk.StringVar(value='vocab')
        for v,t in [('vocab','Vocabulary (word list)'),('assoc','Word association (bigram)')]:
            tk.Radiobutton(mf, text=t, variable=self._mode, value=v,
                           bg=BG, fg=FG, selectcolor=BG3, font=("Courier",9)).pack(side=tk.LEFT, padx=8)
        self._log = tk.Text(self, height=8, bg=BG3, fg=FG2, font=("Courier",8), state=tk.DISABLED)
        self._log.pack(fill='x', padx=10, pady=4)
        Btn(self, "Train", cmd=self._train, color=GRN, fg=BG, font=("Courier",10,"bold")).pack(pady=8)
        self._fp = None

    def _browse(self):
        fp = filedialog.askopenfilename(filetypes=[("Text","*.txt"),("All","*.*")])
        if fp: self._fp = fp; self._path_lbl.config(text=os.path.basename(fp))

    def _log_msg(self, m):
        self._log.config(state=tk.NORMAL)
        self._log.insert(tk.END, m + '\n'); self._log.see(tk.END)
        self._log.config(state=tk.DISABLED)

    def _train(self):
        if not self._fp: messagebox.showwarning("No file","Select a file first."); return
        try:
            with open(self._fp, 'r', encoding='utf-8', errors='ignore') as f: raw = f.read()
            mode = self._mode.get()
            if mode == 'vocab':
                words = [w.strip().lower() for w in re.split(r'\W+', raw) if w.strip().isalpha()]
                words = sorted(set(words))
                for w in words:
                    if w not in self.app.word_dict: self.app.word_dict.append(w)
                self.app.word_dict.sort(); self.app._whc_matrix = None
                self._log_msg(f"Added {len(words)} unique words to dictionary.")
                try: self.app._dict_lbl.config(text=f"{len(self.app.word_dict)} words")
                except: pass
            else:
                self.app.word_bigram.record_text(raw)
                self._log_msg(f"Bigram table updated: {self.app.word_bigram.vocab_size()} words, {len(self.app.word_bigram)} pairs.")
        except Exception as e: messagebox.showerror("Error", str(e))


class ExportDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app; self.title("Export Creature")
        self.configure(bg=BG); self.grab_set(); self.geometry("440x300")
        tk.Label(self, text="  Export Creature", bg=BG2, fg=GRN,
                 font=("Courier",13,"bold"), padx=10, pady=8, anchor='w').pack(fill='x')
        info = tk.Frame(self, bg=BG3, padx=12, pady=10); info.pack(fill='x', padx=10, pady=6)
        nn  = app.nn_store.get('text') or app.nn_store.get('image')
        hid = nn.hidden_size if nn else '?'
        inp = nn.input_size  if nn else '?'
        tk.Label(info, text=f"Brain:  {app.brain_name.get() or '?'}   hidden={hid}  in={inp}",
                 bg=BG3, fg=FG, font=("Courier",9), anchor='w').pack(fill='x')
        tk.Label(info, text=f"Soul:   XP={app.soul.experience:.2f}  play_style={app.soul.play_style:.2f}",
                 bg=BG3, fg=FG, font=("Courier",9), anchor='w').pack(fill='x')
        tk.Label(info, text=f"Dict:   {len(app.word_dict)} words",
                 bg=BG3, fg=FG, font=("Courier",9), anchor='w').pack(fill='x')
        brow = Frm(self, padx=10); brow.pack(fill='x', pady=8)
        Btn(brow, "Save .creature.npz", cmd=self._save_creature,
            color=GRN, fg=BG, font=("Courier",9,"bold")).pack(side=tk.LEFT, padx=4)
        Btn(brow, "Save .ltm.npz", cmd=lambda: app.save_long_term_memory(),
            color=ACN, fg=BG, font=("Courier",9,"bold")).pack(side=tk.LEFT, padx=4)
        Btn(self, "Close", cmd=self.destroy, color=BG4, fg='#ffffff').pack(pady=8)

    def _save_creature(self):
        fp = filedialog.asksaveasfilename(title="Save Creature",
            defaultextension=".creature.npz",
            filetypes=[("Creature","*.creature.npz"),("All","*.*")])
        if not fp: return
        app = self.app
        try:
            nn   = app.nn_store.get(app._last_itype)
            soul = app.soul
            if nn is None: messagebox.showwarning("No network","Train a network first."); return
            emo_order  = ['happiness','sadness','anger','fear','curiosity','calm']
            inst_order = ['hunger','tiredness','boredom','pain']
            ge = np.array([app.genetics.emo_susceptibility[e] for e in emo_order], dtype=np.float32)
            gi = np.array([app.genetics.inst_vulnerability[i] for i in inst_order], dtype=np.float32)
            if soul._memory:
                raw_vecs    = [np.array(m[0]).flatten() for m in soul._memory]
                max_len     = max(len(v) for v in raw_vecs)
                soul_vecs   = np.array([np.pad(v,(0,max_len-len(v))) for v in raw_vecs], dtype=np.float32)
                soul_labels = np.array([m[1] for m in soul._memory])
            else:
                soul_vecs   = np.zeros((0,6), dtype=np.float32)
                soul_labels = np.array([])
            payload = dict(
                creature_marker=np.array(True),
                B_W1=nn.W1, B_b1=nn.b1, B_W2=nn.W2, B_b2=nn.b2, B_W_h=nn.W_h,
                B_input_size=np.array(nn.input_size), B_hidden_size=np.array(nn.hidden_size),
                B_output_size=np.array(nn.output_size), B_weight_init=np.array(nn.weight_init),
                B_name=np.array(app.brain_name.get().strip() or "Brain"),
                S_W1=soul.W1, S_b1=soul.b1, S_W2=soul.W2, S_b2=soul.b2,
                S_hidden=np.array(soul.hidden), S_experience=np.array(soul.experience),
                S_play_style=np.array(soul.play_style), S_name=np.array(app.soul_name.get().strip() or "Soul"),
                soul_mem_vecs=soul_vecs, soul_mem_labels=soul_labels,
                genetics_emo=ge, genetics_inst=gi,
                relational_att=np.array(app.relational.attachment),
                relational_res=np.array(app.relational.resentment),
                word_dict=np.array(app.word_dict) if app.word_dict else np.array([]),
                personality=np.array("live"),
                saved_at=np.array(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                forged_by=np.array("NeuroSim_N8"),
            )
            if app.bigram_matrix is not None:
                payload['bigram_matrix'] = app.bigram_matrix
                payload['bigram_vocab']  = np.array(app.bigram_vocab)
            np.savez(fp, **payload)
            messagebox.showinfo("Saved", f"Creature saved:\n{os.path.basename(fp)}")
            self.destroy()
        except Exception as e: messagebox.showerror("Error", str(e))


class ImportDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app; self.title("Import Creature")
        self.configure(bg=BG); self.grab_set(); self.geometry("500x420")
        tk.Label(self, text="  Import Creature", bg=BG2, fg=ACN,
                 font=("Courier",13,"bold"), padx=10, pady=8, anchor='w').pack(fill='x')
        tk.Label(self, text="  Load a .creature.npz created by NeuroForge",
                 bg=BG2, fg=FG2, font=("Courier",8), padx=10, anchor='w').pack(fill='x')
        bf = Frm(self, padx=10, pady=8); bf.pack(fill='x')
        Btn(bf, "Browse .creature.npz…", cmd=self._browse,
            color=ACN, fg=BG, font=("Courier",9,"bold")).pack(side=tk.LEFT, padx=4)
        self._path_lbl = tk.Label(bf, text="No file", bg=BG, fg=FG2, font=("Courier",8))
        self._path_lbl.pack(side=tk.LEFT, padx=8)
        self._info_txt = tk.Text(self, height=10, bg=BG3, fg=FG2, font=("Courier",8), state=tk.DISABLED)
        self._info_txt.pack(fill='x', padx=10, pady=4)
        self._status = tk.StringVar(value="")
        tk.Label(self, textvariable=self._status, bg=BG, fg=GRN,
                 font=("Courier",8,"italic")).pack(padx=10, anchor='w')
        brow = Frm(self, padx=10); brow.pack(fill='x', pady=8)
        self._load_btn = Btn(brow, "Load Creature", cmd=self._load,
                             color=GRN, fg=BG, font=("Courier",10,"bold"))
        self._load_btn.pack(side=tk.LEFT, padx=4); self._load_btn.config(state=tk.DISABLED)
        Btn(brow, "Close", cmd=self.destroy, color=BG4, fg='#ffffff').pack(side=tk.LEFT, padx=4)
        self._fp = None

    def _browse(self):
        fp = filedialog.askopenfilename(title="Select Creature",
            filetypes=[("Creature","*.creature.npz"),("NPZ","*.npz"),("All","*.*")])
        if not fp: return
        self._fp = fp; self._path_lbl.config(text=os.path.basename(fp))
        try:
            d = np.load(fp, allow_pickle=True)
            lines = [f"File: {os.path.basename(fp)}", ""]
            if 'B_name' in d:     lines.append(f"Brain:        {d['B_name']}")
            if 'B_hidden_size' in d: lines.append(f"Hidden size:  {int(d['B_hidden_size'])}")
            if 'B_input_size'  in d: lines.append(f"Input size:   {int(d['B_input_size'])}")
            if 'S_experience'  in d: lines.append(f"Soul XP:      {float(d['S_experience']):.2f}")
            if 'personality'   in d: lines.append(f"Personality:  {d['personality']}")
            if 'forged_by'     in d: lines.append(f"Created by:   {d['forged_by']}")
            if 'saved_at'      in d: lines.append(f"Saved:        {d['saved_at']}")
            if 'word_dict'     in d: lines.append(f"Dictionary:   {len(d['word_dict'])} words")
            self._info_txt.config(state=tk.NORMAL)
            self._info_txt.delete(1.0, tk.END)
            self._info_txt.insert(tk.END, '\n'.join(lines))
            self._info_txt.config(state=tk.DISABLED)
            self._load_btn.config(state=tk.NORMAL)
        except Exception as e:
            self._status.set(f"Read error: {e}")

    def _load(self):
        if not self._fp: return
        app = self.app
        try:
            d = np.load(self._fp, allow_pickle=True)
            # Load brain
            if 'B_W1' in d:
                in_s  = int(d['B_input_size']); hid_s = int(d['B_hidden_size']); out_s = int(d['B_output_size'])
                nn = SimpleNN(in_s, hid_s, out_s, float(d.get('B_weight_init', np.array(0.1))))
                nn.W1 = np.array(d['B_W1']); nn.b1 = np.array(d['B_b1'])
                nn.W2 = np.array(d['B_W2']); nn.b2 = np.array(d['B_b2'])
                if 'B_W_h' in d: nn.W_h = np.array(d['B_W_h'])
                nn._init_momentum()
                app.nn_store['text'] = nn; app.cfg_hidden_size = hid_s
                app.visual_cortex = VisualCortex(input_size=hid_s)
                app.cfg_text_len = in_s; app._last_itype = 'text'
                bn = str(d['B_name']) if 'B_name' in d else "Brain"
                app.brain_name.set(bn)
            # Load soul
            if 'S_W1' in d:
                app.soul.W1 = np.array(d['S_W1']); app.soul.b1 = np.array(d['S_b1'])
                app.soul.W2 = np.array(d['S_W2']); app.soul.b2 = np.array(d['S_b2'])
                if 'S_hidden'     in d: app.soul.hidden     = int(d['S_hidden'])
                if 'S_experience' in d: app.soul.experience = float(d['S_experience'])
                if 'S_play_style' in d: app.soul.play_style = float(d['S_play_style'])
                sn = str(d['S_name']) if 'S_name' in d else "Soul"
                app.soul_name.set(sn)
            # Soul memory
            if 'soul_mem_vecs' in d:
                vecs = d['soul_mem_vecs']; labels = d['soul_mem_labels']
                app.soul._memory = [(vecs[i], str(labels[i])) for i in range(len(vecs))]
            # Genetics
            emo_order  = ['happiness','sadness','anger','fear','curiosity','calm']
            inst_order = ['hunger','tiredness','boredom','pain']
            if 'genetics_emo' in d:
                g = d['genetics_emo'].flatten()
                for i, nm in enumerate(emo_order[:len(g)]): app.genetics.emo_susceptibility[nm] = float(g[i])
            if 'genetics_inst' in d:
                g = d['genetics_inst'].flatten()
                for i, nm in enumerate(inst_order[:len(g)]): app.genetics.inst_vulnerability[nm] = float(g[i])
            if 'relational_att' in d: app.relational.attachment = float(d['relational_att'])
            if 'relational_res' in d: app.relational.resentment = float(d['relational_res'])
            # Dictionary
            if 'word_dict' in d:
                app.word_dict = list(str(w) for w in d['word_dict'])
                app._whc_matrix = None
                try: app._dict_lbl.config(text=f"{len(app.word_dict)} words")
                except: pass
            if 'bigram_matrix' in d and 'bigram_vocab' in d:
                app.bigram_matrix = d['bigram_matrix']
                app.bigram_vocab  = list(str(w) for w in d['bigram_vocab'])
            app._creature_autosave_path = self._fp
            app._upd_badge()
            app._has_creature = True
            app._update_face()
            try: app._welcome_frame.place_forget()
            except: pass
            self._status.set("Creature loaded successfully!")
            messagebox.showinfo("Loaded", f"Creature '{app.brain_name.get()}' loaded from:\n{os.path.basename(self._fp)}")
            self.destroy()
        except Exception as e: messagebox.showerror("Error", str(e))


# ─────────────────────────────────────────────────────────────
#  Main App
# ─────────────────────────────────────────────────────────────
class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Neuron 8 — NeuroSim")
        root.configure(bg=BG)
        root.geometry("1280x860")
        root.minsize(1100, 720)
        _apply_dark_style()

        # ── Runtime state ────────────────────────────────────
        self._has_creature  = False
        self.nn_store       = {'text': None, 'image': None}
        self._last_itype    = 'text'
        self._running       = False
        self._stop_flag     = False
        self._run_thread    = None
        self._play_mode     = False
        self._last_interaction  = datetime.datetime.now()
        self._last_play_action  = None
        self._autosave_path     = None
        self._creature_autosave_path = None
        self._last_autosave     = None
        self._last_creature_autosave = None
        self._rest_since_save   = 0
        self._soc_running       = False
        self._soc_tick_count    = 0
        self._face_window       = None
        self._out_img_ref       = None
        self._img_canvas_size   = 192
        self._whc_words         = None
        self._whc_matrix        = None

        # ── Config ───────────────────────────────────────────
        self.cfg_learning_rate = 0.02
        self.cfg_text_len      = 32
        self.cfg_img_dim       = 16
        self.cfg_hidden_size   = 256
        self.cfg_out_dim       = 64

        # ── Core systems ─────────────────────────────────────
        self.emotions      = EmotionState()
        self.instincts     = InstinctSystem()
        self.genetics      = GeneticsProfile()
        self.relational    = RelationalState()
        self.soul          = SoulNN(hidden=20)
        self.word_dict     = []
        self.word_bigram   = WordBigram()
        self.tag_image_mem = TagImageMemory()
        self.tag_registry  = {}
        self.internal_reward = InternalRewardSystem()
        self.visual_cortex = VisualCortex(input_size=self.cfg_hidden_size)
        self.bigram_matrix = None
        self.bigram_vocab  = []

        # ── Tk variables ─────────────────────────────────────
        self.brain_name    = tk.StringVar(value="")
        self.soul_name     = tk.StringVar(value="")
        self._lr_var       = tk.DoubleVar(value=self.cfg_learning_rate)
        self._noise_var    = tk.DoubleVar(value=0.02)
        self._iter_var     = tk.IntVar(value=50)
        self._prompt_var   = tk.StringVar(value="")
        self._resp_var     = tk.StringVar(value="")
        self._itype_var    = tk.StringVar(value="text")
        self.out_text      = tk.BooleanVar(value=True)
        self.out_graph     = tk.BooleanVar(value=False)
        self.out_heat      = tk.BooleanVar(value=False)
        self.alpha_filt    = tk.BooleanVar(value=True)
        self.face_interval = tk.DoubleVar(value=3.0)
        self._use_rnn      = tk.BooleanVar(value=True)
        self._use_hebbian  = tk.BooleanVar(value=False)
        self._use_hash     = tk.BooleanVar(value=True)
        self._soc_hz       = tk.DoubleVar(value=5.0)
        self._hebbian_eta  = tk.DoubleVar(value=0.0005)
        self._autosave_enabled  = tk.BooleanVar(value=True)
        self._autosave_interval = tk.IntVar(value=10)
        self._autosave_on_rest  = tk.BooleanVar(value=True)
        self._cosine_anneal     = tk.BooleanVar(value=True)
        self._anneal_min_lr_frac= tk.DoubleVar(value=0.1)

        self._build_layout()
        self._build_left(self._left_sf.inner)
        self._build_right(self._right_sf.inner)
        self._build_chat_strip(self.root)

        # Music + copyright footer
        self._music = MusicPlayer()
        add_music_bar(self.root, self._music)
        self._music.start()
        # add_music_bar sets WM_DELETE_WINDOW automatically when no prior handler exists

        # Start ticks
        self.root.after(2000,  self._emotion_tick)
        self.root.after(8000,  self._soul_tick)
        self.root.after(8000,  self._reward_decay_tick)
        self.root.after(3000,  self._passive_train_tick)
        self.root.after(60000, self._autosave_tick)
        self.root.after(60000, self._creature_autosave_tick)
        self.root.after(800,   self._soc_auto_start)

        # Show import gate if no creature loaded
        self.root.after(200, self._maybe_show_welcome)

    # ── Welcome gate ─────────────────────────────────────────
    def _maybe_show_welcome(self):
        if not self._has_creature:
            self._show_welcome_overlay()

    def _show_welcome_overlay(self):
        ov = tk.Frame(self.root, bg=BG2, bd=2, relief='flat')
        ov.place(relx=0.5, rely=0.5, anchor='center', width=500, height=320)
        self._welcome_frame = ov
        tk.Label(ov, text="◉ NeuroSim", bg=BG2, fg=ACN,
                 font=("Courier",20,"bold")).pack(pady=(24,4))
        tk.Label(ov, text="No creature is loaded yet.",
                 bg=BG2, fg=FG, font=("Courier",11)).pack()
        tk.Label(ov, text="Create one in NeuroForge, then import it here.",
                 bg=BG2, fg=FG2, font=("Courier",9,"italic")).pack(pady=(4,20))
        bf = tk.Frame(ov, bg=BG2); bf.pack()
        Btn(bf, "  ↪  Import Creature…  ", cmd=lambda: [ov.destroy(), self.open_load_dialog()],
            color=ACN, fg=BG, font=("Courier",12,"bold"), padx=12, pady=8).pack(side=tk.LEFT, padx=10)
        Btn(bf, "  Continue Anyway  ", cmd=ov.destroy,
            color=BG4, fg='#ffffff', font=("Courier",9), padx=6, pady=6).pack(side=tk.LEFT, padx=6)
        tk.Label(ov, text="NeuroForge creates pre-trained creatures ready for interaction.",
                 bg=BG2, fg=BG4, font=("Courier",7,"italic")).pack(pady=(18,0))

    # ── Layout ───────────────────────────────────────────────
    def _build_layout(self):
        # Header
        hdr = tk.Frame(self.root, bg=BG2, pady=6)
        hdr.pack(fill='x', side=tk.TOP)
        tk.Label(hdr, text="  ◉ NeuroSim", bg=BG2, fg=ACN,
                 font=("Courier",14,"bold")).pack(side=tk.LEFT)
        self._badge_var = tk.StringVar(value="no creature")
        self._badge_lbl = tk.Label(hdr, textvariable=self._badge_var,
                                    bg=BG3, fg=FG2, font=("Courier",8), padx=8, pady=3)
        self._badge_lbl.pack(side=tk.LEFT, padx=10)
        Btn(hdr, "Export", cmd=self.open_save_dialog, color=BG3, fg='#ffffff',
            font=("Courier",9)).pack(side=tk.RIGHT, padx=6)
        Btn(hdr, "Import", cmd=self.open_load_dialog, color=ACN, fg=BG,
            font=("Courier",9,"bold")).pack(side=tk.RIGHT, padx=4)

        # Split pane
        pane = tk.PanedWindow(self.root, orient='horizontal', sashwidth=6,
                               bg=BG4, sashrelief='flat')
        pane.pack(fill='both', expand=True, side=tk.TOP)

        left_outer  = tk.Frame(pane, bg=BG, width=480)
        right_outer = tk.Frame(pane, bg=BG, width=560)
        pane.add(left_outer,  minsize=360); pane.add(right_outer, minsize=400)

        self._left_sf  = ScrollableFrame(left_outer)
        self._left_sf.pack(fill='both', expand=True)
        self._right_sf = ScrollableFrame(right_outer)
        self._right_sf.pack(fill='both', expand=True)

    # ── Left panel ───────────────────────────────────────────
    def _build_left(self, parent):
        p = parent

        # Input type
        itf = LFrm(p, "Input Type", padx=8, pady=4); itf.grid(row=0, column=0, columnspan=2, sticky='ew', padx=8, pady=(8,4))
        for v, t in [('text','Text'), ('image','Image')]:
            tk.Radiobutton(itf, text=t, variable=self._itype_var, value=v,
                           bg=BG2, fg=FG, selectcolor=BG3, font=("Courier",10),
                           command=self._on_itype_change).pack(side=tk.LEFT, padx=12)

        # Prompt / Response
        for label, var, row in [("Prompt:", self._prompt_var, 1), ("Response:", self._resp_var, 2)]:
            Lbl(p, label).grid(row=row, column=0, sticky='w', padx=10, pady=2)
            e = DEntry(p, textvariable=var, font=("Courier",9), width=32)
            e.grid(row=row, column=1, sticky='ew', padx=8, pady=2)
        p.columnconfigure(1, weight=1)

        # Noise / Iterations
        nif = Frm(p); nif.grid(row=3, column=0, columnspan=2, sticky='ew', padx=8, pady=2)
        Lbl(nif, "Noise:", bg=BG).pack(side=tk.LEFT)
        DScale(nif, self._noise_var, 0.0, 0.5, length=110).pack(side=tk.LEFT, padx=4)
        Lbl(nif, " Iters:", bg=BG).pack(side=tk.LEFT, padx=4)
        DSpin(nif, self._iter_var, 1, 2000, inc=10, width=6).pack(side=tk.LEFT)
        Lbl(nif, " LR:", bg=BG).pack(side=tk.LEFT, padx=4)
        DScale(nif, self._lr_var, 0.001, 0.5, length=100).pack(side=tk.LEFT, padx=4)

        # Output options
        oof = Frm(p); oof.grid(row=4, column=0, columnspan=2, sticky='ew', padx=8, pady=2)
        for var, txt in [(self.out_text,'Text'), (self.out_graph,'Graph'), (self.out_heat,'Heatmap')]:
            tk.Checkbutton(oof, text=txt, variable=var, bg=BG, fg=FG,
                           selectcolor=BG3, font=("Courier",9)).pack(side=tk.LEFT, padx=6)
        tk.Checkbutton(oof, text="Alpha filter", variable=self.alpha_filt,
                       bg=BG, fg=FG2, selectcolor=BG3, font=("Courier",8)).pack(side=tk.LEFT, padx=6)
        tk.Checkbutton(oof, text="Cosine LR", variable=self._cosine_anneal,
                       bg=BG, fg=FG2, selectcolor=BG3, font=("Courier",8)).pack(side=tk.LEFT, padx=6)

        # Run / Stop / Predict
        rbf = Frm(p); rbf.grid(row=5, column=0, columnspan=2, sticky='ew', padx=8, pady=6)
        self._run_btn  = Btn(rbf, "▶ Run",      cmd=self.start_run,   color='#2e6b2e', fg='#ffffff', font=("Courier",10,"bold"))
        self._stop_btn = Btn(rbf, "■ Stop",     cmd=self.stop_run,    color='#6b2e2e', fg='#ffffff', font=("Courier",10,"bold"))
        self._pred_btn = Btn(rbf, "◆ Predict",  cmd=self._predict,    color='#2e2e6b', fg='#ffffff', font=("Courier",10,"bold"))
        for b in (self._run_btn, self._stop_btn, self._pred_btn): b.pack(side=tk.LEFT, padx=4)

        # Reward / Punish
        rpf = Frm(p); rpf.grid(row=6, column=0, columnspan=2, sticky='ew', padx=8, pady=4)
        Btn(rpf, "★ Reward", cmd=self.apply_reward, color='#1e5e1e', fg='#a6e3a1', font=("Courier",9,"bold")).pack(side=tk.LEFT, padx=4)
        Btn(rpf, "✕ Punish", cmd=self.apply_punish, color='#5e1e1e', fg='#f38ba8', font=("Courier",9,"bold")).pack(side=tk.LEFT, padx=4)

        Sep(p).grid(row=7, column=0, columnspan=2, sticky='ew', padx=8, pady=4)

        # Tools row
        trf = Frm(p); trf.grid(row=8, column=0, columnspan=2, sticky='ew', padx=8, pady=2)
        Btn(trf, "Train Text File", cmd=self._open_text_train,  color=YEL,  fg=BG, font=("Courier",9,"bold")).pack(side=tk.LEFT, padx=4)
        Btn(trf, "Image Tags",      cmd=self._open_tag_mgr,     color=PRP,  fg=BG, font=("Courier",9,"bold")).pack(side=tk.LEFT, padx=4)
        Btn(trf, "Dictionary",      cmd=self._open_dict,        color=BG4,  fg='#ffffff', font=("Courier",9,"bold")).pack(side=tk.LEFT, padx=4)
        self._dict_lbl = tk.Label(trf, text="0 words", bg=BG, fg=FG2, font=("Courier",8))
        self._dict_lbl.pack(side=tk.LEFT, padx=6)

        # Memory row
        mrf = Frm(p); mrf.grid(row=9, column=0, columnspan=2, sticky='ew', padx=8, pady=2)
        Btn(mrf, "Save LTM",  cmd=self.save_long_term_memory,  color='#1e3d6e', fg='#ffffff', font=("Courier",9,"bold")).pack(side=tk.LEFT, padx=4)
        Btn(mrf, "Load LTM",  cmd=self.load_long_term_memory,  color='#3d1e6e', fg='#ffffff', font=("Courier",9,"bold")).pack(side=tk.LEFT, padx=4)

        Sep(p).grid(row=10, column=0, columnspan=2, sticky='ew', padx=8, pady=4)

        # Progress bar
        self._prog_var = tk.IntVar(value=0)
        self._prog_lbl = tk.Label(p, text="idle", bg=BG, fg=FG2, font=("Courier",8))
        self._prog_lbl.grid(row=11, column=0, sticky='w', padx=10)
        ttk.Progressbar(p, variable=self._prog_var, maximum=100, length=200).grid(
            row=11, column=1, sticky='ew', padx=8)

        # Output text widget
        otf = LFrm(p, "Network Output", padx=6, pady=4)
        otf.grid(row=12, column=0, columnspan=2, sticky='ew', padx=8, pady=4)
        self.out_txt_w = tk.Text(otf, height=5, bg=BG3, fg=FG, font=("Courier",9),
                                  wrap=tk.WORD, state=tk.DISABLED)
        self.out_txt_w.pack(fill='x')

        # Image output canvas
        self._img_frame = LFrm(p, "Image Output", padx=6, pady=4)
        self._img_frame.grid(row=13, column=0, columnspan=2, sticky='ew', padx=8, pady=4)
        self._img_canvas = tk.Canvas(self._img_frame, bg='#000011',
                                      width=self._img_canvas_size, height=self._img_canvas_size,
                                      highlightthickness=1, highlightbackground=BG4)
        self._img_canvas.pack()

        # History
        self.hist = HistoryPanel(p)
        self.hist.grid(row=14, column=0, columnspan=2, sticky='ew', padx=8, pady=4)

    # ── Right panel ──────────────────────────────────────────
    def _build_right(self, parent):
        p = parent

        # Face
        face_frm = tk.Frame(p, bg=BG2, padx=8, pady=8)
        face_frm.grid(row=0, column=0, columnspan=2, sticky='ew', padx=8, pady=(8,4))
        self.face_lbl = tk.Label(face_frm, bg=BG2, text="◉",
                                  font=("Courier", 72), fg=BG4, width=100, height=100)
        self.face_lbl.pack(side=tk.LEFT)
        nf = Frm(face_frm, bg=BG2); nf.pack(side=tk.LEFT, fill='both', expand=True, padx=12)
        Lbl(nf, "Brain name:", bg=BG2, font=("Courier",8)).pack(fill='x')
        DEntry(nf, textvariable=self.brain_name, font=("Courier",10,"bold")).pack(fill='x')
        Lbl(nf, "Soul name:", bg=BG2, font=("Courier",8)).pack(fill='x', pady=(6,0))
        DEntry(nf, textvariable=self.soul_name, font=("Courier",9)).pack(fill='x')
        self._badge_detail = tk.Label(nf, text="", bg=BG2, fg=FG2, font=("Courier",7), anchor='w')
        self._badge_detail.pack(fill='x', pady=(6,0))
        fspf = Frm(nf, bg=BG2); fspf.pack(fill='x', pady=(4,0))
        Lbl(fspf, "Face refresh:", bg=BG2, font=("Courier",7)).pack(side=tk.LEFT)
        DScale(fspf, self.face_interval, 1.0, 30.0, length=100, resolution=1.0, bg=BG2).pack(side=tk.LEFT)
        self._face_spd_lbl = tk.Label(fspf, text="3s", width=3, bg=BG2, fg=FG2, font=("Courier",7))
        self._face_spd_lbl.pack(side=tk.LEFT)
        self.face_interval.trace_add("write", self._upd_face_spd_lbl)
        Btn(nf, "Detach Face", cmd=self._detach_face, color=BG4, fg='#ffffff',
            font=("Courier",8)).pack(fill='x', pady=(6,0))

        Sep(p).grid(row=1, column=0, columnspan=2, sticky='ew', padx=8, pady=4)

        # Emotion / Instinct / Soul / Relational panels
        self.emo_panel  = EmotionPanel(p, self.emotions);  self.emo_panel.grid(row=2,  column=0, columnspan=2, sticky='ew', padx=8, pady=2)
        self.inst_panel = InstinctPanel(p, self.instincts); self.inst_panel.grid(row=3, column=0, columnspan=2, sticky='ew', padx=8, pady=2)
        self.inst_panel.feed_btn.config(command=self.care_feed)
        self.inst_panel.sleep_btn.config(command=self.care_sleep)
        self.inst_panel.play_btn.config(command=self.care_play)
        self.inst_panel.soothe_btn.config(command=self.care_soothe)

        self.soul_panel = SoulPanel(p, self.soul)
        self.soul_panel.grid(row=4, column=0, columnspan=2, sticky='ew', padx=8, pady=2)
        self.soul_panel.approve_btn.config(command=self._soul_approve_care)
        self.soul_panel.discourage_btn.config(command=self._soul_discourage_care)
        self.soul_panel.rew_soul_btn.config(command=self._reward_soul)
        self.soul_panel.pun_soul_btn.config(command=self._punish_soul)
        self.soul_panel.approve_play_btn.config(command=self._approve_last_play)
        self.soul_panel.discourage_play_btn.config(command=self._discourage_last_play)

        # Soul output
        sof = LFrm(p, "Soul Stream", padx=6, pady=4)
        sof.grid(row=5, column=0, columnspan=2, sticky='ew', padx=8, pady=2)
        self.soul_out_txt = tk.Text(sof, height=5, bg='#05050f', fg=PRP,
                                     font=("Courier",8), state=tk.DISABLED, wrap=tk.WORD)
        self.soul_out_txt.pack(fill='x')

        self.rel_panel = RelationalStatusPanel(p, self.relational)
        self.rel_panel.grid(row=6, column=0, columnspan=2, sticky='ew', padx=8, pady=2)

        # V3 panel
        self._build_v3_panel(p, row=7)

        # Schedule face
        self.root.after(1000, self._update_face)

    # ── V3 / SoC panel ───────────────────────────────────────
    def _build_v3_panel(self, parent, row=7):
        outer = Collapsible(parent, "  V3 — RNN · Hebbian · Visual Cortex · SoC", start_open=True)
        outer.grid(row=row, column=0, columnspan=2, sticky='ew', padx=8, pady=(4,8))
        B = outer.body

        tf = Frm(B, bg=BG2); tf.pack(fill='x', padx=4, pady=(4,2))
        for var, txt, col in [(self._use_rnn,'RNN State',ACN),(self._use_hebbian,'Hebbian',GRN),(self._use_hash,'Hash Encoding',YEL)]:
            tk.Checkbutton(tf, text=txt, variable=var, bg=BG2, fg=col,
                           selectcolor=BG3, font=("Courier",9), activebackground=BG2).pack(side=tk.LEFT, padx=6)

        hf = Frm(B, bg=BG2); hf.pack(fill='x', padx=4, pady=2)
        tk.Label(hf, text="Hebbian η:", width=11, anchor='w', bg=BG2, fg=GRN, font=("Courier",9)).pack(side=tk.LEFT)
        DScale(hf, self._hebbian_eta, 0.00005, 0.005, bg=BG2, resolution=0.00005, length=140).pack(side=tk.LEFT, padx=4)
        self._heb_lbl = tk.Label(hf, text=f"{self._hebbian_eta.get():.5f}", width=8, bg=BG2, fg=GRN, font=("Courier",8))
        self._heb_lbl.pack(side=tk.LEFT)
        self._hebbian_eta.trace_add("write", lambda *_: self._heb_lbl.config(text=f"{self._hebbian_eta.get():.5f}"))

        sf = Frm(B, bg=BG2); sf.pack(fill='x', padx=4, pady=2)
        self._soc_btn = Btn(sf, "▶ Start SoC", cmd=self._toggle_soc, color=GRN, fg=BG,
                             font=("Courier",9,"bold"), padx=8)
        self._soc_btn.pack(side=tk.LEFT, padx=4)
        Btn(sf, "Reset Hidden", cmd=self._reset_hidden, color=BG4, fg='#ffffff', font=("Courier",9), padx=6).pack(side=tk.LEFT, padx=4)
        Btn(sf, "Reset VC",     cmd=self._reset_vc,     color=BG4, fg='#ffffff', font=("Courier",9), padx=6).pack(side=tk.LEFT, padx=4)
        tk.Label(sf, text="Hz:", bg=BG2, fg=FG2, font=("Courier",9)).pack(side=tk.LEFT, padx=(8,2))
        DScale(sf, self._soc_hz, 0.5, 20.0, bg=BG2, resolution=0.5, length=80).pack(side=tk.LEFT)
        self._soc_hz_lbl = tk.Label(sf, text="5.0", width=4, bg=BG2, fg=FG2, font=("Courier",8)); self._soc_hz_lbl.pack(side=tk.LEFT)
        self._soc_hz.trace_add("write", lambda *_: self._soc_hz_lbl.config(text=f"{self._soc_hz.get():.1f}"))

        sf2 = Frm(B, bg=BG2); sf2.pack(fill='x', padx=4, pady=1)
        self._soc_h_lbl    = tk.Label(sf2, text="‖h‖=0.00", bg=BG2, fg=CYN, font=("Courier",8), width=12, anchor='w'); self._soc_h_lbl.pack(side=tk.LEFT, padx=4)
        self._soc_tick_lbl = tk.Label(sf2, text="ticks: 0",  bg=BG2, fg=FG2, font=("Courier",8), width=12, anchor='w'); self._soc_tick_lbl.pack(side=tk.LEFT, padx=4)

        bottom = Frm(B, bg=BG2); bottom.pack(fill='x', padx=4, pady=4)
        vc_frm = LFrm(bottom, "Visual Cortex (32×32)", padx=4, pady=4); vc_frm.pack(side=tk.LEFT, padx=(0,6))
        self._vc_canvas = tk.Canvas(vc_frm, bg='#000000', width=192, height=192, highlightthickness=1, highlightbackground=BG4); self._vc_canvas.pack()
        self._vc_cycle_lbl = tk.Label(vc_frm, text="cycle: 0", bg=BG2, fg=FG2, font=("Courier",7), anchor='center'); self._vc_cycle_lbl.pack()
        soc_frm = LFrm(bottom, "Stream of Consciousness", padx=4, pady=4); soc_frm.pack(side=tk.LEFT, fill='both', expand=True)
        self._soc_log_txt = tk.Text(soc_frm, height=10, width=32, bg=BG3, fg=CYN, font=("Courier",8), state=tk.DISABLED, wrap=tk.WORD)
        soc_sb = tk.Scrollbar(soc_frm, command=self._soc_log_txt.yview, bg=BG3)
        self._soc_log_txt.config(yscrollcommand=soc_sb.set)
        soc_sb.pack(side=tk.RIGHT, fill='y'); self._soc_log_txt.pack(side=tk.LEFT, fill='both', expand=True)

    # ── Chat strip ───────────────────────────────────────────
    def _build_chat_strip(self, parent):
        outer = tk.Frame(parent, bg=BG3, bd=0, height=230)
        outer.pack(side=tk.BOTTOM, fill='x')
        outer.pack_propagate(False)

        hdr = tk.Frame(outer, bg=BG4); hdr.pack(fill='x')
        tk.Label(hdr, text="  CHAT — speak to the creature",
                 bg=BG4, fg=ACN, font=("Courier",10,"bold"), anchor='w').pack(side=tk.LEFT, padx=6, pady=4)
        self._chat_status_var = tk.StringVar(value="")
        tk.Label(hdr, textvariable=self._chat_status_var, bg=BG4, fg=FG2,
                 font=("Courier",8), anchor='e').pack(side=tk.RIGHT, padx=8)

        body = tk.Frame(outer, bg=BG3); body.pack(fill='both', expand=True, padx=4, pady=(2,4))

        # Chat log — takes remaining horizontal space
        log_frm = tk.Frame(body, bg=BG3); log_frm.pack(side=tk.LEFT, fill='both', expand=True, padx=(0,4))
        self._chat_log = tk.Text(log_frm, height=7, bg='#0d0d18', fg=FG,
                                  font=("Courier",9), state=tk.DISABLED, wrap=tk.WORD, relief='flat',
                                  selectbackground=BG4, padx=6, pady=4)
        chat_sb = tk.Scrollbar(log_frm, command=self._chat_log.yview, bg=BG3)
        self._chat_log.config(yscrollcommand=chat_sb.set)
        chat_sb.pack(side=tk.RIGHT, fill='y'); self._chat_log.pack(side=tk.LEFT, fill='both', expand=True)
        self._chat_log.tag_config('you',      foreground=YEL, font=("Courier",9,"bold"))
        self._chat_log.tag_config('creature', foreground=CYN, font=("Courier",9))
        self._chat_log.tag_config('emo',      foreground=PRP, font=("Courier",8,"italic"))
        self._chat_log.tag_config('ts',       foreground=FG2, font=("Courier",7))
        self._chat_log.tag_config('sys',      foreground=BG4, font=("Courier",8,"italic"))

        # Input column — fixed width, not squeezed
        inp_frm = tk.Frame(body, bg=BG3, width=320); inp_frm.pack(side=tk.RIGHT, fill='y')
        inp_frm.pack_propagate(False)

        tk.Label(inp_frm, text="Your message:", bg=BG3, fg=FG2,
                 font=("Courier",8), anchor='w').pack(fill='x', padx=4)
        self._chat_entry = tk.Text(inp_frm, height=4, bg=BG4, fg=FG, font=("Courier",9),
                                    relief='flat', insertbackground=FG, wrap=tk.WORD, padx=4, pady=4)
        self._chat_entry.pack(fill='x', padx=4)
        self._chat_entry.bind('<Return>',       self._chat_on_enter)
        self._chat_entry.bind('<KP_Enter>',     self._chat_on_enter)
        self._chat_entry.bind('<Shift-Return>', lambda e: None)

        btn_row = tk.Frame(inp_frm, bg=BG3); btn_row.pack(fill='x', padx=4, pady=(4,2))
        Btn(btn_row, "Send [↵]", cmd=self._chat_send,
            color=ACN, fg=BG, font=("Courier",9,"bold")).pack(side=tk.LEFT)
        Btn(btn_row, "Clear", cmd=self._chat_clear,
            color=BG4, fg='#ffffff', font=("Courier",8)).pack(side=tk.LEFT, padx=6)

        fb_row = tk.Frame(inp_frm, bg=BG3); fb_row.pack(fill='x', padx=4, pady=(2,0))
        self._approve_btn = Btn(fb_row, "✓ Good",
            cmd=self._chat_approve,
            font=("Courier",9,"bold"), pady=3, state=tk.DISABLED)
        self._approve_btn.pack(side=tk.LEFT, padx=(0,4))
        self._disapprove_btn = Btn(fb_row, "✗ Bad",
            cmd=self._chat_disapprove,
            font=("Courier",9,"bold"), pady=3, state=tk.DISABLED)
        self._disapprove_btn.pack(side=tk.LEFT)
        self._feedback_lbl = tk.Label(inp_frm, text="", bg=BG3, fg=FG2,
                                       font=("Courier",7,"italic"), anchor='w')
        self._feedback_lbl.pack(fill='x', padx=4, pady=(2,0))

        self._chat_history = []
        self._last_chat_exchange = None
        self.root.after(600, self._chat_welcome)

    # ── Training ─────────────────────────────────────────────
    def _ensure_nn(self, itype, in_sz, out_sz):
        if self.nn_store.get(itype) is None:
            self.nn_store[itype] = SimpleNN(in_sz, self.cfg_hidden_size, out_sz)
            self.visual_cortex = VisualCortex(input_size=self.cfg_hidden_size)

    def _eff_noise(self):
        n = float(self._noise_var.get())
        n += self.emotions.noise_add() + self.instincts.noise_add() + self.relational.noise_add()
        return max(0.0, n)

    def start_run(self):
        if self._running: return
        itype = self._itype_var.get()
        if itype == 'text':
            self._ensure_nn('text', self.cfg_text_len, self.cfg_text_len)
        else:
            d = self.cfg_img_dim; self._ensure_nn('image', d*d, d*d)
        self._last_itype = itype; self._running = True; self._stop_flag = False
        self._prog_var.set(0)
        self._run_thread = threading.Thread(target=self._run_worker, daemon=True)
        self._run_thread.start()

    def stop_run(self):
        self._stop_flag = True

    def _run_worker(self):
        itype  = self._last_itype
        nn     = self.nn_store[itype]
        iters  = int(self._iter_var.get())
        lr     = float(self._lr_var.get()); self.cfg_learning_rate = lr
        cosine = self._cosine_anneal.get()
        min_lr = lr * float(self._anneal_min_lr_frac.get())
        p_var  = self._prompt_var.get().strip()
        r_var  = self._resp_var.get().strip()
        enc    = text_to_vec_hash if self._use_hash.get() else text_to_vec
        supervised = bool(p_var and r_var)
        try:
            for i in range(iters):
                if self._stop_flag: break
                clr = lr if not cosine else (min_lr + 0.5*(lr - min_lr)*(1 + math.cos(math.pi * i / iters)))
                clr *= self.emotions.lr_mult() * self.instincts.lr_mult() * self.relational.lr_mult()
                noise = self._eff_noise()
                if supervised:
                    x = enc(p_var, nn.input_size); t = enc(r_var, nn.output_size)
                    out = nn.forward(x, noise=noise)
                    mse = nn.train_supervised(x, t, lr=clr)
                    if i == 0: self.word_bigram.record_text(p_var + " " + r_var)
                elif itype == 'image' and p_var:
                    try: x = image_to_vec(p_var, (self.cfg_img_dim, self.cfg_img_dim))
                    except: break
                    out = nn.forward(x, noise=noise); mse = nn.train(x, lr=clr)
                else:
                    text = p_var or "the quick brown fox"
                    x = enc(text, nn.input_size)
                    out = nn.forward(x, noise=noise); mse = nn.train(x, lr=clr)
                self.instincts.on_training(mse, 1)
                self.emotions.on_mse(mse, self.genetics)
                self.internal_reward.on_mse(mse, self.emotions, self.instincts, self.genetics)
                pct = int((i+1)/iters*100)
                self.root.after(0, lambda p=pct, m=mse: (self._prog_var.set(p), self._prog_lbl.config(text=f"MSE:{m:.5f}")))
            self.root.after(0, lambda: self._finish(nn, itype))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Run Error", str(e)))
            self.root.after(0, self._clear_running)

    def _finish(self, nn, itype):
        self._running = False; self._stop_flag = False
        self._prog_lbl.config(text="done")
        x = None
        if self._prompt_var.get().strip():
            enc = text_to_vec_hash if self._use_hash.get() else text_to_vec
            x = enc(self._prompt_var.get(), nn.input_size)
        else:
            x = np.random.rand(1, nn.input_size).astype(np.float32)
        out = nn.forward(x, noise=0.0)
        mse = float(np.mean((out - x[:, :nn.output_size])**2))
        self._render(x, out, mse, nn, itype)
        self._update_face()

    def _clear_running(self):
        self._running = False; self._stop_flag = False

    def _predict(self):
        itype = self._last_itype; nn = self.nn_store.get(itype)
        if nn is None: return
        enc = text_to_vec_hash if self._use_hash.get() else text_to_vec
        p = self._prompt_var.get().strip()
        x = enc(p, nn.input_size) if p else np.random.rand(1, nn.input_size).astype(np.float32)
        nn.reset_hidden(); out = nn.forward(x, noise=self._eff_noise() * 0.05)
        mse = float(np.mean((out - x[:, :nn.output_size])**2))
        self._render(x, out, mse, nn, itype, event="Predict")

    def _render(self, x, final, mse, nn, itype, event="Run"):
        flat = final.flatten(); td = ""
        if self.out_text.get():
            td = self.word_dict and self._dict_text(flat) or vec_to_text(flat, self.alpha_filt.get())
            self.out_txt_w.config(state=tk.NORMAL); self.out_txt_w.delete(1.0, tk.END)
            if event != "Run": self.out_txt_w.insert(tk.END, f"[{event}]\n")
            self.out_txt_w.insert(tk.END, f"Alpha: {td}\nMSE : {mse:.6f}\n")
            self.out_txt_w.config(state=tk.DISABLED)
        pil_img = None
        if self.out_graph.get():
            od = self.cfg_out_dim
            if itype == "image":
                d = self.cfg_img_dim; raw = (flat.reshape(d,d)*255).astype(np.uint8)
            else: raw = (flat*255).astype(np.uint8).reshape(1,-1)
            pil_img = Image.fromarray(raw,'L').resize((od,od),Image.NEAREST)
        self.hist.push({"timestamp":datetime.datetime.now().strftime("%H:%M:%S"),
                        "itype":itype,"text_out":td,"mse":mse,"pil_image":pil_img,"event":event})

    # ── Reward / Punish ──────────────────────────────────────
    def apply_reward(self):
        nn = self.nn_store.get(self._last_itype)
        if nn is None: return
        ev = self.emotions.to_vec()
        self.emotions.on_reward(self.genetics); self.instincts.on_reward()
        self.relational.on_reward(); self.genetics.record('reward')
        self.soul.reward(ev, s=0.2)
        self.internal_reward.on_reward(self.emotions, self.instincts, self.genetics, 'external')
        self._update_face()

    def apply_punish(self):
        nn = self.nn_store.get(self._last_itype)
        if nn is None: return
        ev = self.emotions.to_vec()
        self.emotions.on_punish(self.genetics); self.instincts.on_punish()
        self.relational.on_punish(); self.genetics.record('punish')
        self.soul.punish(ev, s=0.15)
        self._update_face()

    # ── Care actions ─────────────────────────────────────────
    def care_feed(self):
        self._last_interaction = datetime.datetime.now()
        self.instincts.feed(); self.emotions.on_reward(self.genetics)
        self.relational.on_care(); self.genetics.record('care')
        self.soul.reward(self.emotions.to_vec(), s=0.15)
        self.soul_panel.log(" Fed — hunger reduced."); self.inst_panel.flash(" Fed!")
        self._update_face()

    def care_sleep(self):
        self._last_interaction = datetime.datetime.now()
        self.instincts.sleep()
        self.emotions.v['calm']      = min(1.0, self.emotions.v['calm']      + 0.25)
        self.emotions.v['happiness'] = min(1.0, self.emotions.v['happiness'] + 0.10)
        self.relational.on_care(); self.genetics.record('care')
        for nn in self.nn_store.values():
            if nn: nn.consolidate(passes=3, lr=0.005); nn.supervised_consolidate(passes=2, lr=0.003)
        self.soul_panel.log(" Slept — memories consolidated.")
        self.inst_panel.flash(" Rested!")
        self._update_face()
        if self._autosave_on_rest.get(): self._silent_save_ltm("sleep"); self._silent_save_creature("sleep")

    def care_play(self):
        self._last_interaction = datetime.datetime.now()
        self.instincts.play()
        self.emotions.v['curiosity'] = min(1.0, self.emotions.v['curiosity'] + 0.20)
        self.emotions.v['happiness'] = min(1.0, self.emotions.v['happiness'] + 0.15)
        self.relational.on_care(); self.genetics.record('care')
        if random.random() < 0.5: self._soul_spontaneous('care_boredom')
        self.soul_panel.log(" Played."); self.inst_panel.flash(" Played!")
        self._update_face()

    def care_soothe(self):
        self._last_interaction = datetime.datetime.now()
        self.instincts.soothe()
        self.emotions.v['fear']  = max(0.0, self.emotions.v['fear']  - 0.25)
        self.emotions.v['anger'] = max(0.0, self.emotions.v['anger'] - 0.20)
        self.emotions.v['calm']  = min(1.0, self.emotions.v['calm']  + 0.30)
        self.relational.on_care(); self.genetics.record('care')
        self.soul_panel.log(" Soothed."); self.inst_panel.flash(" Soothed!")
        self._update_face()

    # ── Soul actions ─────────────────────────────────────────
    def _soul_approve_care(self):
        self.soul.approve_care(self.emotions.to_vec(), self.relational)
        self.soul_panel.log(" Care approved.")

    def _soul_discourage_care(self):
        self.soul.discourage_care(self.emotions.to_vec(), self.relational)
        self.soul_panel.log(" Care discouraged.")

    def _reward_soul(self):
        self.soul.reward(self.emotions.to_vec(), s=0.2)
        self.emotions.on_reward(self.genetics); self.soul_panel.log(" Soul rewarded.")
        self._update_face()

    def _punish_soul(self):
        self.soul.punish(self.emotions.to_vec(), s=0.15)
        self.emotions.on_punish(self.genetics); self.soul_panel.log(" Soul punished.")
        self._update_face()

    def _approve_last_play(self):
        self.soul.reward(self.emotions.to_vec(), s=0.12); self.soul_panel.log(" Play approved.")

    def _discourage_last_play(self):
        self.soul.punish(self.emotions.to_vec(), s=0.08); self.soul_panel.log(" Play discouraged.")

    # ── Face / ticks ─────────────────────────────────────────
    def _update_face(self):
        try:
            nn  = self.nn_store.get(self._last_itype)
            img = make_face(nn, self.soul, self.emotions, self.instincts, self.relational, size=96)
            ph  = ImageTk.PhotoImage(img); self._face_ref = ph
            self.face_lbl.config(image=ph, text="")
        except: pass
        self._schedule_face()

    def _schedule_face(self):
        ms = max(1000, int(float(self.face_interval.get()) * 1000))
        self.root.after(ms, self._update_face)

    def _upd_face_spd_lbl(self, *_):
        try: self._face_spd_lbl.config(text=f"{int(self.face_interval.get())}s")
        except: pass

    def _upd_badge(self):
        n = self.brain_name.get() or "?"
        h = self.nn_store.get('text')
        hid = h.hidden_size if h else '?'
        self._badge_var.set(f"{n}  hidden={hid}")
        self._badge_detail.config(text=f"XP:{self.soul.experience:.2f}  att:{self.relational.attachment:.2f}  res:{self.relational.resentment:.2f}")

    def _emotion_tick(self):
        try:
            self.instincts.tick(); self.instincts.influence_emotions(self.emotions)
            self.relational.tick(self.instincts); self.genetics.slow_drift()
            if self.instincts.v['hunger'] > 0.75 or self.instincts.v['boredom'] > 0.80: self.genetics.record('neglect')
            self.emo_panel.refresh(); self.inst_panel.refresh()
            self.soul_panel.refresh(self.emotions)
            try: self.rel_panel.refresh()
            except: pass
        except: pass
        self.root.after(2000, self._emotion_tick)

    def _soul_tick(self):
        try:
            if self.soul_panel.auto_generate:
                self.soul.forward(self.emotions.to_vec())
                care = self.soul.decide_care(self.instincts, self.emotions, self.relational)
                if care:
                    action, desc = care
                    self.soul_panel.set_care_action(action, desc)
                    self._execute_care_action(action, desc)
                boredom_boost = self.instincts.boredom_gen_boost()
                resentment_boost = self.relational.gen_boost()
                fm = self.soul_panel.freq_mult + boredom_boost*4.0 + resentment_boost*2.0
                if self.soul.should_spontaneously_generate(self.emotions, fm):
                    self._soul_spontaneous('spontaneous')
                idle_s = (datetime.datetime.now() - self._last_interaction).total_seconds()
                if not self._play_mode and idle_s >= self.soul_panel.play_threshold and not self._running:
                    self._enter_play_mode()
                elif self._play_mode: self._play_tick()
                pp = 0.07*self.emotions.v['curiosity'] + 0.04*self.relational.resentment
                if not self._running and random.random() < pp:
                    nn = self.nn_store.get(self._last_itype)
                    if nn:
                        scale = self.soul.weight_noise_scale(self.emotions)
                        if scale > 0.0005: nn.add_weight_noise(scale); self.soul_panel.log(f" Nudged ±{scale:.4f}")
                if random.random() < 0.04:
                    new_lr = self.soul.suggest_lr_perturb(self.emotions, self.cfg_learning_rate)
                    if abs(new_lr - self.cfg_learning_rate) > 0.005:
                        self.soul_panel.log(f" Suggests lr={new_lr:.4f}")
        except: pass
        self.root.after(8000, self._soul_tick)

    def _schedule_soul(self): self.root.after(8000, self._soul_tick)

    def _reward_decay_tick(self):
        try:
            self.internal_reward.decay_tick()
            dom = self.internal_reward.dominant_action()
            if dom and self.internal_reward.get_momentum(dom) > 0.15:
                try: self.soul_panel._as_status_var.set(f"momentum: {dom.replace('_',' ')} ({self.internal_reward.get_momentum(dom):.2f})")
                except: pass
        except: pass
        self.root.after(8000, self._reward_decay_tick)

    def _execute_care_action(self, action, desc):
        ev = self.emotions.to_vec()
        if action == 'rest':
            self.instincts.v['tiredness'] = max(0.0, self.instincts.v['tiredness'] - 0.08)
            nn = self.nn_store.get(self._last_itype); consolidated = 0
            if nn and not self._running: consolidated = nn.consolidate(passes=1, lr=0.004) + nn.supervised_consolidate(passes=1, lr=0.003)
            self.soul.reward(ev, s=0.06); self.soul_panel.log(f" Resting — consolidated {consolidated}")
            self.inst_panel.flash(" Resting.")
            self._rest_since_save += 1
            if self._autosave_on_rest.get() and self._rest_since_save >= 3:
                self._silent_save_ltm(reason=f"rest×{self._rest_since_save}")
        elif action in ('generate_text','generate_image'):
            self.instincts.v['boredom'] = max(0.0, self.instincts.v['boredom'] - 0.12)
            self.emotions.v['curiosity'] = min(1.0, self.emotions.v['curiosity'] + 0.08)
            itype = 'text' if action == 'generate_text' else 'image'
            self._soul_spontaneous('care_boredom', forced_itype=itype)
        elif action == 'soothe':
            self.instincts.v['pain'] = max(0.0, self.instincts.v['pain'] - 0.10)
            self.emotions.v['calm'] = min(1.0, self.emotions.v['calm'] + 0.12)
            self.emotions.v['fear'] = max(0.0, self.emotions.v['fear'] - 0.08)
            self.soul.reward(ev, s=0.08); self._soul_spontaneous('care_soothe', forced_itype='image')
        elif action == 'seek_food':
            hunger_before = self.instincts.v['hunger']
            self.instincts.v['hunger'] = max(0.0, hunger_before - 0.45)
            self.instincts.v['tiredness'] = min(1.0, self.instincts.v['tiredness'] + 0.05 + hunger_before * 0.15)
            self.emotions.v['happiness'] = min(1.0, self.emotions.v['happiness'] + 0.10)
            self.soul.reward(ev, s=0.08)
            self.soul_panel.log(f" Foraged — hunger ↓{hunger_before:.2f}→{self.instincts.v['hunger']:.2f}")
            self.inst_panel.flash(" Foraged!")
        self._update_face()

    def _enter_play_mode(self):
        self._play_mode = True
        self.instincts.v['boredom'] = max(0.0, self.instincts.v['boredom'] - 0.05)
        self.soul_panel.set_play_state(True, "starting...")
        self.soul_panel.log(" Entering play mode.")

    def _exit_play_mode(self):
        if self._play_mode:
            self._play_mode = False; self.soul_panel.set_play_state(False)
            self.soul_panel.log(" User returned — exiting play.")

    def _play_tick(self):
        em = self.emotions.v; iv = self.instincts.v
        if iv['tiredness'] > 0.80 or iv['pain'] > 0.70:
            self.soul_panel.set_play_state(True, "resting instead...")
            self.instincts.v['tiredness'] = max(0.0, iv['tiredness'] - 0.04); return
        ps = self.soul.play_style
        weights = {'generate_image': (1.0-ps)*2.0+em['happiness']*0.5, 'generate_text': ps*2.0+em['curiosity']*0.5,
                   'memory_replay': 0.5+em['sadness']*0.8, 'brain_explore': 0.3+em['curiosity']*0.6}
        choices = list(weights.keys()); w_vals = np.array([weights[c] for c in choices]); w_vals /= w_vals.sum()
        activity = random.choices(choices, weights=w_vals, k=1)[0]
        self.soul_panel.set_play_state(True, activity.replace('_',' ')); self._last_play_action = activity
        if activity == 'generate_image':   self._soul_spontaneous('play', forced_itype='image'); msg="Imagined."
        elif activity == 'generate_text':  self._soul_spontaneous('play', forced_itype='text');  msg="Composed."
        elif activity == 'memory_replay':
            nn = self.nn_store.get(self._last_itype)
            if nn and nn._working_mem:
                x, _ = random.choice(nn._working_mem); out = nn.forward(x, noise=0.05)
                txt  = self._dict_text(out)[:36] if self.word_dict else "..."; msg = f'Replayed: "{txt}"'
            else: msg = "Tried to replay — mind blank."
        else:
            nn = self.nn_store.get(self._last_itype)
            if nn:
                noise = 0.002 + em['curiosity'] * 0.003
                nn.forward(np.random.rand(1, nn.input_size).astype(np.float32), noise=noise)
                msg = f"Explored (noise={noise:.4f})."
            else: msg = "No brain yet."
        self.instincts.v['boredom']  = max(0.0, iv['boredom']  - 0.06)
        self.emotions.v['happiness'] = min(1.0, em['happiness'] + 0.04)
        self.emotions.v['sadness']   = max(0.0, em['sadness']   - 0.02)
        self.relational.attachment   = min(1.0, self.relational.attachment + 0.005)
        self.soul.add_memory(self.emotions.to_vec(), 'neutral')
        self.soul_panel.log_play(msg); self._soul_out(f"[Play] {msg}")

    def _soul_spontaneous(self, source='spontaneous', forced_itype=None):
        itype = forced_itype or self._last_itype
        nn    = self.nn_store.get(itype)
        if nn is None:
            itype = 'image' if itype == 'text' else 'text'; nn = self.nn_store.get(itype)
        if nn is None: self.soul_panel.log("(no network)"); return
        ev    = self.emotions.to_vec(); noise = self._eff_noise() + 0.08 + self.emotions.v['anger'] * 0.05
        rand_in = np.random.rand(1, nn.input_size)
        soul_out = self.soul.forward(ev).flatten()
        soul_mod = soul_out[:nn.input_size] if len(soul_out) >= nn.input_size else np.resize(soul_out, nn.input_size)
        x = rand_in * 0.7 + soul_mod.reshape(1,-1) * 0.3; out = nn.forward(x, noise=noise)
        thought = self.soul.get_thought(self.emotions)
        if itype == 'text':
            txt = self._dict_text(out) if self.word_dict else vec_to_text(out.flatten(), True)
            display = f"[Soul] {thought}\n   → \"{txt[:60]}\"\n"
            try:
                self.out_txt_w.config(state=tk.NORMAL); self.out_txt_w.insert(tk.END, display)
                self.out_txt_w.see(tk.END); self.out_txt_w.config(state=tk.DISABLED)
            except: pass
            self.soul_panel.log(f" Text: \"{txt[:28]}...\""); self._soul_out(display)
        else:
            try:
                d = self.cfg_img_dim; pix = np.clip(out.flatten()[:d*d], 0, 1)
                r_e, g_e, b_e = _emotion_rgb(self.emotions)
                r = np.clip(pix*(0.6+0.4*r_e),0,1); g = np.clip(pix*(0.6+0.4*g_e),0,1); b = np.clip(pix*(0.6+0.4*b_e),0,1)
                rgb = (np.stack([r,g,b],axis=-1)*255).astype(np.uint8)
                small = Image.fromarray(rgb.reshape(d,d,3),'RGB')
                sz = self._img_canvas_size; big = small.resize((sz,sz),Image.NEAREST)
                ph = ImageTk.PhotoImage(big); self._out_img_ref = ph
                self._img_canvas.delete("all"); self._img_canvas.create_image(0,0,anchor='nw',image=ph)
            except: pass
        if nn is not None: self.soul.experience = min(2.0, self.soul.experience + 0.005)
        self.soul.add_memory(ev, 'neutral')

    def _soul_out(self, msg):
        self.soul_out_txt.config(state=tk.NORMAL)
        self.soul_out_txt.insert(tk.END, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}\n\n")
        self.soul_out_txt.see(tk.END); self.soul_out_txt.config(state=tk.DISABLED)

    # ── SoC ─────────────────────────────────────────────────
    def _soc_auto_start(self):
        try:
            if not self._soc_running: self._toggle_soc()
        except: pass

    def _toggle_soc(self):
        if self._soc_running: self._stop_soc()
        else: self._start_soc()

    def _start_soc(self):
        if self._soc_running: return
        self._soc_running = True
        try: self._soc_btn.config(text="■ Stop SoC", bg=RED, fg='#ffffff')
        except: pass
        self._soc_tick_fn()

    def _stop_soc(self):
        self._soc_running = False
        try: self._soc_btn.config(text="▶ Start SoC", bg=GRN, fg=BG)
        except: pass

    def _soc_tick_fn(self):
        if not self._soc_running: return
        try:
            self._soc_tick_count += 1
            emo_vec  = self.emotions.to_vec()
            inst_vec = np.array([self.instincts.v[n] for n in InstinctSystem.NAMES], dtype=np.float32)
            nn = self.nn_store.get('text') or self.nn_store.get('image')
            if nn is not None and self._use_rnn.get():
                in_sz = nn.input_size; mem_vec = None; mem_label = None
                has_sup = bool(nn._supervised_mem); has_wm = bool(nn._working_mem)
                if has_sup and has_wm:
                    if random.random() < 0.70:
                        x_m, t_m, _ = random.choice(nn._supervised_mem); mem_vec = x_m; mem_label = 'supervised'
                    else:
                        x_m, _ = random.choice(nn._working_mem); mem_vec = x_m; mem_label = 'working'
                elif has_sup: x_m, t_m, _ = random.choice(nn._supervised_mem); mem_vec = x_m; mem_label = 'supervised'
                elif has_wm:  x_m, _       = random.choice(nn._working_mem);    mem_vec = x_m; mem_label = 'working'
                x_self = np.zeros((1, in_sz), dtype=np.float32)
                if mem_vec is not None:
                    n_m = min(mem_vec.shape[1] if mem_vec.ndim > 1 else len(mem_vec), in_sz)
                    x_self[0, :n_m] += mem_vec.flatten()[:n_m] * 0.50
                    x_self[0, :min(len(emo_vec),in_sz)] += emo_vec[:min(len(emo_vec),in_sz)].astype(np.float32) * 0.25
                    x_self[0, :min(len(inst_vec),in_sz)] += inst_vec[:min(len(inst_vec),in_sz)] * 0.10
                    h_flat = nn.hidden_state.flatten(); x_self[0, :min(len(h_flat),in_sz)] += h_flat[:min(len(h_flat),in_sz)] * 0.15
                else:
                    h_flat = nn.hidden_state.flatten(); x_self[0, :min(len(h_flat),in_sz)] += h_flat[:min(len(h_flat),in_sz)] * 0.45
                    x_self[0, :min(len(emo_vec),in_sz)] += emo_vec[:min(len(emo_vec),in_sz)].astype(np.float32) * 0.25
                    x_self[0, :min(len(inst_vec),in_sz)] += inst_vec[:min(len(inst_vec),in_sz)] * 0.10; mem_label = 'noise'
                x_self = np.clip(x_self, 0, 1)
                out = nn.forward(x_self, noise=self._eff_noise() * 0.08)
                h_norm = float(np.linalg.norm(nn.hidden_state))
                if h_norm > 4.0: nn.hidden_state = nn.hidden_state * (4.0 / h_norm)
                if self._use_hebbian.get(): nn.hebbian_update(eta=float(self._hebbian_eta.get()) * 0.3, decay=0.000002)
                h_norm = float(np.linalg.norm(nn.hidden_state))
                try:
                    self._soc_h_lbl.config(text=f"‖h‖={h_norm:.3f}")
                    self._soc_tick_lbl.config(text=f"ticks: {self._soc_tick_count}")
                except: pass
                flat = out.flatten()
                snip = ''.join(chr(int(v*255)) if 32<=int(v*255)<=126 else '·' for v in flat[:20])
                src_tag = f"[{mem_label}]" if mem_label else ""
                self._soc_log(f"‣ {src_tag} {snip.strip() or '...'}")
            h_for_vc = nn.hidden_state if nn is not None else np.random.randn(1, self.cfg_hidden_size) * 0.1
            self.visual_cortex.step(h_for_vc, emo_vec); self._update_vc_canvas()
        except: pass
        ms = max(50, int(1000.0 / max(0.1, float(self._soc_hz.get()))))
        self.root.after(ms, self._soc_tick_fn)

    def _update_vc_canvas(self):
        try:
            img = self.visual_cortex.get_pil_image(self.emotions, display_size=192)
            ph  = ImageTk.PhotoImage(img); self._vc_ref = ph
            self._vc_canvas.delete("all"); self._vc_canvas.create_image(0,0,anchor='nw',image=ph)
            self._vc_cycle_lbl.config(text=f"cycle: {self.visual_cortex._cycle}")
        except: pass

    def _soc_log(self, msg):
        try:
            self._soc_log_txt.config(state=tk.NORMAL)
            self._soc_log_txt.insert(tk.END, msg + '\n')
            lines = int(self._soc_log_txt.index('end-1c').split('.')[0])
            if lines > 200: self._soc_log_txt.delete('1.0', f'{lines-200}.0')
            self._soc_log_txt.see(tk.END); self._soc_log_txt.config(state=tk.DISABLED)
        except: pass

    def _reset_hidden(self):
        for nn in self.nn_store.values():
            if nn is not None: nn.reset_hidden()
        self._soc_log("[reset] Hidden state cleared.")

    def _reset_vc(self):
        self.visual_cortex.reset(); self._update_vc_canvas()
        self._soc_log("[reset] Visual cortex cleared.")

    # ── Chat ─────────────────────────────────────────────────
    def _chat_welcome(self):
        self._chat_log_append('emo', "  ╔═══════════════════════════════════════════╗")
        self._chat_log_append('emo', "  ║  CHAT — associative conversation          ║")
        self._chat_log_append('emo', "  ║  Import a creature to begin.             ║")
        self._chat_log_append('emo', "  ╚═══════════════════════════════════════════╝")

    def _chat_on_enter(self, event):
        if event.keysym in ('Return', 'KP_Enter') and not (event.state & 0x1):
            self._chat_send(); return 'break'

    def _chat_send(self):
        msg = self._chat_entry.get('1.0', tk.END).strip()
        if not msg: return
        self._chat_entry.delete('1.0', tk.END)
        self._last_interaction = datetime.datetime.now()
        if self._play_mode: self._exit_play_mode()
        try: self._approve_btn.config(state=tk.DISABLED); self._disapprove_btn.config(state=tk.DISABLED); self._feedback_lbl.config(text="")
        except: pass
        self._chat_log_append('you', f"You: {msg}")
        self._chat_history.append(('you', msg))
        if len(self._chat_history) > 20: self._chat_history.pop(0)
        self.root.after(80, lambda m=msg: self._chat_respond(m))

    def _chat_respond(self, user_msg):
        try: self._do_chat_respond(user_msg)
        except Exception as err: self._chat_log_append('emo', f"  [error: {err}]"); self._chat_status_var.set(f"Error: {err}")

    def _do_chat_respond(self, user_msg):
        ts = datetime.datetime.now().strftime('%H:%M:%S'); ev = self.emotions.v; dom_emo = max(ev, key=ev.get)
        nn = self.nn_store.get('text') or self.nn_store.get('image')
        if nn is None:
            self._chat_log_append('emo', "  (no network yet — import a creature first!)"); self._chat_status_var.set("Import a creature first."); return
        enc = text_to_vec_hash if self._use_hash.get() else text_to_vec
        msg_vec  = enc(user_msg, nn.input_size)
        soul_out = self.soul.forward(self.emotions.to_vec()).flatten()
        soul_mod = np.resize(soul_out, nn.input_size).reshape(1,-1)
        ctx = np.zeros((1, nn.input_size), dtype=np.float32)
        for role, prev in self._chat_history[-3:]:
            if role == 'you': ctx = ctx * 0.5 + enc(prev, nn.input_size) * 0.5
        seed = np.clip(msg_vec * 0.65 + soul_mod * 0.20 + ctx * 0.15, 0, 1)
        nn.reset_hidden(); noise = self._eff_noise() * 0.08; current = seed.copy()
        for _ in range(4): out = nn.forward(current, noise=noise * 0.5); current = np.clip(out * 0.55 + seed * 0.45, 0, 1)
        out = nn.forward(current, noise=0.0); flat = out.flatten()
        response = self._dict_text(flat) if self.word_dict else ''.join(ALLOWED[int(np.argmin(np.abs(A_CODES - v)))] for v in flat)
        prefixes = {'happiness':["! ","~ ",""],'sadness':["... ",""],'anger':["! ","!! ",""],'fear':["? ","... "],'curiosity':["? ","~ ",""],'calm':["","- ",""]}
        prefix = random.choice(prefixes.get(dom_emo, [""]))
        if len(response) > 80: cut = response[:80].rfind(' '); response = response[:cut if cut > 20 else 80] + '...'
        final_response = (prefix + response).strip() or '...'
        top_emos = sorted(ev.items(), key=lambda x: -x[1])[:3]
        emo_str  = "  [" + "  ".join(f"{n[:3]}:{v:.2f}" for n, v in top_emos) + "]"
        name = self.brain_name.get() or "Creature"
        self._chat_log_append('ts', f"  {ts}"); self._chat_log_append('creature', f"{name}: {final_response}"); self._chat_log_append('emo', emo_str)
        self._chat_history.append(('creature', final_response))
        if len(self._chat_history) > 20: self._chat_history.pop(0)
        self._last_chat_exchange = {'prompt_vec': msg_vec.copy(), 'out_vec': out.copy(), 'user_msg': user_msg, 'response': final_response}
        try: self._approve_btn.config(state=tk.NORMAL); self._disapprove_btn.config(state=tk.NORMAL); self._feedback_lbl.config(text="Rate this response ↑")
        except: pass
        self.emotions.v['curiosity'] = min(1.0, ev.get('curiosity', 0.5) + 0.04)
        self.instincts.v['boredom']  = max(0.0, self.instincts.v['boredom'] - 0.08)
        self.relational.on_care(); self._chat_status_var.set(f"Responded {ts}  [{dom_emo}]"); self._update_face()

    def _chat_log_append(self, tag, text):
        self._chat_log.config(state=tk.NORMAL); self._chat_log.insert(tk.END, text + '\n', tag)
        lines = int(self._chat_log.index('end-1c').split('.')[0])
        if lines > 500: self._chat_log.delete('1.0', f'{lines-500}.0')
        self._chat_log.see(tk.END); self._chat_log.config(state=tk.DISABLED)

    def _chat_clear(self):
        self._chat_log.config(state=tk.NORMAL); self._chat_log.delete(1.0, tk.END); self._chat_log.config(state=tk.DISABLED)
        self._chat_history.clear(); self._last_chat_exchange = None; self._chat_status_var.set("Log cleared.")
        try: self._approve_btn.config(state=tk.DISABLED); self._disapprove_btn.config(state=tk.DISABLED); self._feedback_lbl.config(text="")
        except: pass

    def _chat_approve(self):
        ex = self._last_chat_exchange
        if not ex: return
        nn = self.nn_store.get('text') or self.nn_store.get('image')
        if nn is None: return
        approve_lr = min(0.06, self.cfg_learning_rate * 0.6)
        for _ in range(8): nn.reset_hidden(); nn.forward(ex['prompt_vec']); nn.train_supervised(ex['prompt_vec'], ex['out_vec'], lr=approve_lr)
        self.emotions.v['happiness'] = min(1.0, self.emotions.v.get('happiness', 0.5) + 0.08)
        self.emotions.v['curiosity'] = min(1.0, self.emotions.v.get('curiosity', 0.5) + 0.04)
        self.soul.reward(self.emotions.to_vec(), s=0.12); self.relational.on_reward()
        self._approve_btn.config(state=tk.DISABLED); self._disapprove_btn.config(state=tk.DISABLED)
        self._feedback_lbl.config(text="✓ Reinforced!"); self._chat_log_append('sys', f"  [✓ Approved: '{ex['response'][:40]}']"); self._update_face()

    def _chat_disapprove(self):
        ex = self._last_chat_exchange
        if not ex: return
        nn = self.nn_store.get('text') or self.nn_store.get('image')
        if nn is None: return
        disrupt_lr = min(0.04, self.cfg_learning_rate * 0.4); rng = np.random.default_rng()
        for _ in range(5):
            noise_target = rng.random(ex['out_vec'].shape).astype(np.float32)
            nn.reset_hidden(); nn.forward(ex['prompt_vec']); nn.train_supervised(ex['prompt_vec'], noise_target, lr=disrupt_lr)
        self.emotions.v['anger'] = min(1.0, self.emotions.v.get('anger', 0.1) + 0.05)
        self.soul.punish(self.emotions.to_vec(), s=0.10); self.relational.on_punish()
        self._approve_btn.config(state=tk.DISABLED); self._disapprove_btn.config(state=tk.DISABLED)
        self._feedback_lbl.config(text="✗ Disrupted."); self._chat_log_append('sys', f"  [✗ Disapproved: '{ex['response'][:40]}']"); self._update_face()

    # ── Word hash cache ───────────────────────────────────────
    def _get_word_hash_cache(self):
        if self._whc_matrix is not None: return self._whc_words, self._whc_matrix
        if not self.word_dict: return [], None
        nn = self.nn_store.get('text'); N = nn.input_size if nn else self.cfg_text_len
        rows = [text_to_vec_hash(w, N).flatten() for w in self.word_dict]
        M = np.stack(rows).astype(np.float32)
        norms = np.linalg.norm(M, axis=1, keepdims=True); norms = np.maximum(norms, 1e-9); M /= norms
        self._whc_words = list(self.word_dict); self._whc_matrix = M
        return self._whc_words, self._whc_matrix

    def _nearest_hash_word(self, vec, exclude=None):
        words, mat = self._get_word_hash_cache()
        if mat is None or not words: return ''
        v = np.array(vec).flatten().astype(np.float32); nv = np.linalg.norm(v)
        if nv < 1e-9: return random.choice(words)
        sims = mat @ (v / nv)
        if exclude:
            for w in exclude:
                if w in self._whc_words: sims[self._whc_words.index(w)] -= 1.0
        return words[int(np.argmax(sims))]

    def _dict_text(self, vec):
        import difflib
        flat = np.array(vec).flatten().astype(np.float32)
        if not self.word_dict:
            raw = ''.join(chr(int(v*255)) if 32<=int(v*255)<=126 else ' ' for v in flat)
            return re.sub(r'\s+', ' ', raw).strip()
        if getattr(self, '_use_hash', None) and self._use_hash.get():
            nn = self.nn_store.get('text'); N = nn.input_size if nn else len(flat)
            words, mat = self._get_word_hash_cache()
            if mat is None or not words: return ''
            bv_idx = ({w: i for i, w in enumerate(self.bigram_vocab)} if self.bigram_matrix is not None and self.bigram_vocab else None)
            result = []; prev_word = None; current = flat.copy(); MAX_WORDS = min(10, max(3, N//4)); recent = set()
            for step in range(MAX_WORDS):
                v_n = current / (np.linalg.norm(current) + 1e-9)
                sims = mat @ v_n.astype(np.float32)
                if prev_word:
                    for ci, cand in enumerate(words):
                        bonus = 0.0
                        if bv_idx and prev_word in bv_idx and cand in bv_idx: bonus += float(self.bigram_matrix[bv_idx[prev_word], bv_idx[cand]]) * 0.5
                        if self.word_bigram.vocab_size() > 0:
                            fol = self.word_bigram._counts.get(prev_word, {})
                            if fol: bonus += fol.get(cand, 0) / (sum(fol.values()) + 1e-9) * 0.5
                        sims[ci] += bonus
                for rw in recent:
                    if rw in self._whc_words: sims[self._whc_words.index(rw)] -= 0.4
                best_idx = int(np.argmax(sims)); word = words[best_idx]; result.append(word)
                recent = {word} | (recent - {list(recent)[0]} if len(recent) >= 2 else recent); prev_word = word
                if word in ('.','!','?') and step >= 2: break
                if nn is not None: nn.reset_hidden(); current = nn.forward(text_to_vec_hash(word, N), noise=0.0).flatten()
                else: current = mat[best_idx].copy()
            return ' '.join(result)
        raw = ''.join(chr(int(v*255)) if 32<=int(v*255)<=126 else ' ' for v in flat)
        raw = re.sub(r'\s+', ' ', raw).strip(); tokens = raw.split()
        if not tokens: return raw
        bv_idx = ({w: i for i, w in enumerate(self.bigram_vocab)} if self.bigram_matrix is not None and self.bigram_vocab else None)
        result = []; prev_word = None
        for tok in tokens:
            tok_lower = tok.lower()
            candidates = difflib.get_close_matches(tok_lower, self.word_dict, n=4, cutoff=0.0)
            if not candidates: result.append(tok); prev_word = tok_lower; continue
            chosen = candidates[0]
            if prev_word and (bv_idx or self.word_bigram.vocab_size() > 0):
                best_score = -1.0
                for cand in candidates:
                    cand_lo = cand.lower(); score = 0.0
                    if bv_idx and prev_word in bv_idx and cand_lo in bv_idx: score += float(self.bigram_matrix[bv_idx[prev_word], bv_idx[cand_lo]])
                    if self.word_bigram.vocab_size() > 0:
                        followers = self.word_bigram._counts.get(prev_word, {})
                        if followers: score += followers.get(cand_lo, 0) / sum(followers.values())
                    if score > best_score: best_score = score; chosen = cand
            result.append(chosen); prev_word = chosen.lower()
        return ' '.join(result)

    # ── Tag image rendering ───────────────────────────────────
    def _render_tag_image(self, tag_vecs):
        img_nn = self.nn_store.get('image')
        if img_nn is None or not tag_vecs: return
        try:
            stacked = np.vstack(tag_vecs); n_tags = stacked.shape[0]; noise = self._eff_noise() * 0.25
            if n_tags == 1:
                img_nn.reset_hidden(); current = img_nn.forward(stacked[[0]], noise=noise)
            else:
                current = np.mean(stacked, axis=0, keepdims=True); img_nn.reset_hidden()
                current = img_nn.forward(current, noise=noise*0.5)
                for it in range(12):
                    step_noise = noise * (1.0 - it/12) * 0.5; tag_outputs = []
                    for tv in stacked:
                        img_nn.reset_hidden(); blend = tv.reshape(1,-1)*0.5 + current*0.5
                        tag_outputs.append(img_nn.forward(blend, noise=step_noise).flatten())
                    residuals = np.array([np.linalg.norm(t - current.flatten()) for t in tag_outputs])
                    weights = residuals / (residuals.sum() + 1e-9)
                    blended = sum(w*t for w,t in zip(weights, tag_outputs))
                    current  = np.clip(blended*0.60 + current.flatten()*0.40, 0, 1).reshape(1,-1)
                img_nn.reset_hidden(); current = img_nn.forward(current, noise=0.0)
            d = self.cfg_img_dim; sz = self._img_canvas_size; pix = np.clip(current.flatten()[:d*d], 0, 1)
            r_e, g_e, b_e = _emotion_rgb(self.emotions)
            r = np.clip(pix*(0.55+0.45*r_e),0,1); g = np.clip(pix*(0.55+0.45*g_e),0,1); b = np.clip(pix*(0.55+0.45*b_e),0,1)
            rgb = (np.stack([r,g,b],axis=-1)*255).astype(np.uint8)
            small = Image.fromarray(rgb.reshape(d,d,3),'RGB'); big = small.resize((sz,sz),Image.NEAREST)
            ph = ImageTk.PhotoImage(big); self._out_img_ref = ph
            self._img_canvas.delete("all"); self._img_canvas.create_image(0,0,anchor='nw',image=ph)
        except: pass

    # ── Passive / autosave ────────────────────────────────────
    def _passive_train_tick(self):
        try:
            if not self._running and self.word_dict and self.nn_store.get('text') is not None:
                nn   = self.nn_store['text']; word = random.choice(self.word_dict)
                x    = text_to_vec(word, nn.input_size); lr = self.cfg_learning_rate * 0.05
                nn.forward(x); nn.train(x, lr=lr)
        except: pass
        self.root.after(3000, self._passive_train_tick)

    def _autosave_tick(self):
        try:
            if self._autosave_enabled.get() and self._autosave_path and not self._running:
                interval_s = int(self._autosave_interval.get()) * 60
                if self._last_autosave is None or (datetime.datetime.now() - self._last_autosave).total_seconds() >= interval_s:
                    self._silent_save_ltm("timed")
        except: pass
        self.root.after(60000, self._autosave_tick)

    def _creature_autosave_tick(self):
        try:
            if self._autosave_enabled.get() and self._creature_autosave_path and not self._running:
                interval_s = int(self._autosave_interval.get()) * 60
                if self._last_creature_autosave is None or (datetime.datetime.now() - self._last_creature_autosave).total_seconds() >= interval_s:
                    self._silent_save_creature("timed")
        except: pass
        self.root.after(60000, self._creature_autosave_tick)

    def _silent_save_ltm(self, reason="auto"):
        if not self._autosave_path or self._running: return
        try:
            consolidated = {}
            for itype, nn in self.nn_store.items():
                if nn is None: continue
                nn.consolidate(passes=2, lr=0.004); nn.supervised_consolidate(passes=2, lr=0.003)
                for k, v in [(f"{itype}_W1",nn.W1),(f"{itype}_b1",nn.b1),(f"{itype}_W2",nn.W2),(f"{itype}_b2",nn.b2),
                              (f"{itype}_in",np.array(nn.input_size)),(f"{itype}_hid",np.array(nn.hidden_size)),
                              (f"{itype}_out",np.array(nn.output_size)),(f"{itype}_wm_count",np.array(len(nn._working_mem)))]:
                    consolidated[k] = v
            if self.soul._memory:
                _rv = [np.array(m[0]).flatten() for m in self.soul._memory]
                _ml = max(len(v) for v in _rv)
                consolidated['soul_mem_vecs']   = np.array([np.pad(v,(0,_ml-len(v))) for v in _rv], dtype=np.float32)
                consolidated['soul_mem_labels'] = np.array([m[1] for m in self.soul._memory])
            if self.word_dict: consolidated['word_dict'] = np.array(self.word_dict)
            if self.word_bigram.vocab_size() > 0: consolidated['word_bigram_json'] = np.array(self.word_bigram.to_json())
            consolidated['relational_att'] = np.array(self.relational.attachment)
            consolidated['relational_res'] = np.array(self.relational.resentment)
            consolidated['genetics_emo']  = np.array([self.genetics.emo_susceptibility[e] for e in GeneticsProfile.EMO_NAMES], dtype=np.float32)
            consolidated['genetics_inst'] = np.array([self.genetics.inst_vulnerability[i] for i in GeneticsProfile.INST_NAMES], dtype=np.float32)
            consolidated['saved_at'] = np.array(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            np.savez(self._autosave_path, **consolidated)
            self._last_autosave = datetime.datetime.now(); self._rest_since_save = 0
            try: self.soul_panel._as_status_var.set(f"autosave ({reason}): {self._last_autosave.strftime('%H:%M:%S')}")
            except: pass
        except Exception as e:
            try: self.soul_panel._as_status_var.set(f"autosave failed: {e}")
            except: pass

    def _silent_save_creature(self, reason="auto"):
        if not self._creature_autosave_path or self._running: return
        try:
            nn = self.nn_store.get(self._last_itype)
            if nn is None: return
            emo_order  = ['happiness','sadness','anger','fear','curiosity','calm']
            inst_order = ['hunger','tiredness','boredom','pain']
            ge = np.array([self.genetics.emo_susceptibility[e] for e in emo_order], dtype=np.float32)
            gi = np.array([self.genetics.inst_vulnerability[i] for i in inst_order], dtype=np.float32)
            payload = dict(
                creature_marker=np.array(True),
                B_W1=nn.W1, B_b1=nn.b1, B_W2=nn.W2, B_b2=nn.b2, B_W_h=nn.W_h,
                B_input_size=np.array(nn.input_size), B_hidden_size=np.array(nn.hidden_size),
                B_output_size=np.array(nn.output_size), B_weight_init=np.array(nn.weight_init),
                B_name=np.array(self.brain_name.get().strip() or "Brain"),
                S_W1=self.soul.W1, S_b1=self.soul.b1, S_W2=self.soul.W2, S_b2=self.soul.b2,
                S_hidden=np.array(self.soul.hidden), S_experience=np.array(self.soul.experience),
                S_name=np.array(self.soul_name.get().strip() or "Soul"),
                genetics_emo=ge, genetics_inst=gi, personality=np.array("live"),
                saved_at=np.array(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            np.savez(self._creature_autosave_path, **payload)
            self._last_creature_autosave = datetime.datetime.now()
            try: self.soul_panel._as_status_var.set(f"creature save ({reason}): {self._last_creature_autosave.strftime('%H:%M:%S')}")
            except: pass
        except: pass

    # ── LTM save/load ─────────────────────────────────────────
    def save_long_term_memory(self):
        fp = filedialog.asksaveasfilename(title="Save Long-Term Memory",
            defaultextension=".ltm.npz", filetypes=[("LTM","*.ltm.npz"),("All","*.*")])
        if not fp: return
        try:
            consolidated = {}
            for itype, nn in self.nn_store.items():
                if nn is None: continue
                nn.consolidate(passes=4, lr=0.004); nn.supervised_consolidate(passes=2, lr=0.003)
                for k, v in [(f"{itype}_W1",nn.W1),(f"{itype}_b1",nn.b1),(f"{itype}_W2",nn.W2),(f"{itype}_b2",nn.b2),
                              (f"{itype}_in",np.array(nn.input_size)),(f"{itype}_hid",np.array(nn.hidden_size)),
                              (f"{itype}_out",np.array(nn.output_size)),(f"{itype}_wm_count",np.array(len(nn._working_mem)))]:
                    consolidated[k] = v
            if self.soul._memory:
                _rv = [np.array(m[0]).flatten() for m in self.soul._memory]
                _ml = max(len(v) for v in _rv)
                consolidated['soul_mem_vecs']   = np.array([np.pad(v,(0,_ml-len(v))) for v in _rv], dtype=np.float32)
                consolidated['soul_mem_labels'] = np.array([m[1] for m in self.soul._memory])
            if self.word_dict: consolidated['word_dict'] = np.array(self.word_dict)
            if self.word_bigram.vocab_size() > 0: consolidated['word_bigram_json'] = np.array(self.word_bigram.to_json())
            consolidated['relational_att'] = np.array(self.relational.attachment)
            consolidated['relational_res'] = np.array(self.relational.resentment)
            consolidated['genetics_emo']  = np.array([self.genetics.emo_susceptibility[e] for e in GeneticsProfile.EMO_NAMES], dtype=np.float32)
            consolidated['genetics_inst'] = np.array([self.genetics.inst_vulnerability[i] for i in GeneticsProfile.INST_NAMES], dtype=np.float32)
            consolidated['saved_at'] = np.array(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            np.savez(fp, **consolidated)
            self._autosave_path = fp; self._last_autosave = datetime.datetime.now(); self._rest_since_save = 0
            try: self.soul_panel._as_status_var.set(f"autosave path: {os.path.basename(fp)}")
            except: pass
            messagebox.showinfo("Saved", f"LTM saved:\n{fp}")
        except Exception as e: messagebox.showerror("Error", str(e))

    def load_long_term_memory(self):
        fp = filedialog.askopenfilename(title="Load Long-Term Memory",
            filetypes=[("LTM","*.ltm.npz"),("All","*.*")])
        if not fp: return
        try:
            d = np.load(fp, allow_pickle=True)
            for itype in ('text', 'image'):
                if f"{itype}_W1" not in d: continue
                in_s  = int(d[f"{itype}_in"]); hid_s = int(d[f"{itype}_hid"]); out_s = int(d[f"{itype}_out"])
                nn = SimpleNN(in_s, hid_s, out_s)
                nn.W1 = d[f"{itype}_W1"]; nn.b1 = d[f"{itype}_b1"]
                nn.W2 = d[f"{itype}_W2"]; nn.b2 = d[f"{itype}_b2"]; nn._init_momentum()
                self.nn_store[itype] = nn; self.cfg_hidden_size = hid_s
            if 'soul_mem_vecs' in d:
                vecs = d['soul_mem_vecs']; labels = d['soul_mem_labels']
                self.soul._memory = [(vecs[i], str(labels[i])) for i in range(len(vecs))]
            if 'word_dict' in d: self.word_dict = list(str(w) for w in d['word_dict']); self._whc_matrix = None
            if 'word_bigram_json' in d: self.word_bigram = WordBigram.from_json(str(d['word_bigram_json']))
            if 'bigram_matrix' in d and 'bigram_vocab' in d:
                self.bigram_matrix = d['bigram_matrix']; self.bigram_vocab = list(str(w) for w in d['bigram_vocab'])
            if 'sup_mem_xs' in d:
                xs = d['sup_mem_xs']; targets = d['sup_mem_targets']; mses = d['sup_mem_mses']
                nn_text = self.nn_store.get('text')
                if nn_text is not None and len(xs) > 0:
                    nn_text._supervised_mem = [(xs[i].reshape(1,-1).astype(np.float32), targets[i].reshape(1,-1).astype(np.float32), float(mses[i])) for i in range(len(xs))]
            if 'relational_att' in d: self.relational.attachment = float(d['relational_att']); self.relational.resentment = float(d['relational_res'])
            if 'genetics_emo' in d:
                g = d['genetics_emo'].flatten()
                for i, nm in enumerate(GeneticsProfile.EMO_NAMES[:len(g)]): self.genetics.emo_susceptibility[nm] = float(g[i])
            if 'genetics_inst' in d:
                g = d['genetics_inst'].flatten()
                for i, nm in enumerate(GeneticsProfile.INST_NAMES[:len(g)]): self.genetics.inst_vulnerability[nm] = float(g[i])
            self._autosave_path = fp; self._upd_badge()
            try: self._dict_lbl.config(text=f"{len(self.word_dict)} words")
            except: pass
            messagebox.showinfo("Loaded", f"LTM loaded from:\n{os.path.basename(fp)}")
        except Exception as e: messagebox.showerror("Error", str(e))

    # ── Dialogs ──────────────────────────────────────────────
    def open_save_dialog(self): ExportDialog(self.root, self)
    def open_load_dialog(self): ImportDialog(self.root, self)
    def _open_dict(self): DictionaryEditorDialog(self.root, self)
    def _open_tag_mgr(self): TagManagerDialog(self.root, self)
    def _open_text_train(self):
        self._ensure_nn('text', self.cfg_text_len, self.cfg_text_len)
        TextTrainDialog(self.root, self)

    def _on_itype_change(self):
        self._last_itype = self._itype_var.get()

    def _detach_face(self):
        if self._face_window and self._face_window.winfo_exists():
            self._face_window.lift(); return
        self._face_window = DetachedFaceWindow(self)


class DetachedFaceWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app; self.title(f"Face — {app.brain_name.get() or 'Creature'}")
        self.configure(bg=BG); self.geometry("300x320")
        self._lbl = tk.Label(self, bg=BG, text="◉", font=("Courier",120), fg=BG3)
        self._lbl.pack(expand=True)
        self._update()

    def _update(self):
        if not self.winfo_exists(): return
        try:
            nn  = self.app.nn_store.get(self.app._last_itype)
            img = make_face(nn, self.app.soul, self.app.emotions, self.app.instincts, self.app.relational, size=256)
            ph  = ImageTk.PhotoImage(img); self._ref = ph; self._lbl.config(image=ph, text="")
        except: pass
        ms = max(1000, int(float(self.app.face_interval.get()) * 1000))
        self.after(ms, self._update)


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
