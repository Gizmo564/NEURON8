#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  NEURON 8 — NeuroLife                                            ║
║  Multi-creature simulation · Social dynamics · Autonomous world  ║
╚══════════════════════════════════════════════════════════════════╝
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neuron8_core import (
    BG, BG2, BG3, BG4, FG, FG2, ACN, GRN, RED, YEL, PRP, CYN, ORG,
    _apply_dark_style, Lbl, Btn, DEntry, DSpin, DScale, Sep, Frm, LFrm,
    ScrollableFrame, Collapsible,
    text_to_vec, text_to_vec_hash, vec_to_text, ALLOWED,
    EmotionState, InstinctSystem, GeneticsProfile, RelationalState,
    WordBigram, SoulNN, SimpleNN, make_face, _emotion_rgb,
    BreedingDialog, MusicPlayer, add_music_bar,
)

import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import threading, datetime, random, math, json, re

# ─────────────────────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────────────────────
MAP_W, MAP_H = 10, 10        # grid dimensions
MAX_CREATURES = 4
CREATURE_COLORS = [ACN, GRN, YEL, ORG]
CREATURE_SYMBOLS = ['◉', '◈', '◆', '◍']

ACTION_LABELS = {
    'feed':    ('Feed',    '#c05a10', '#ffffff'),
    'soothe':  ('Soothe',  '#8a1530', '#ffffff'),
    'play':    ('Play',    '#0e7a6a', '#ffffff'),
    'sleep':   ('Sleep',   '#4a4aaa', '#ffffff'),
    'praise':  ('Praise',  '#1e5e1e', GRN),
    'fight':   ('Fight',   '#8a2020', RED),
    'hurt':    ('Hurt',    '#5a0000', RED),
    'teach':   ('Teach',   '#1e1e6e', ACN),
    'ignore':  ('Ignore',  BG3,      '#ffffff'),
}


# ─────────────────────────────────────────────────────────────
#  Creature agent
# ─────────────────────────────────────────────────────────────
class CreatureAgent:
    """Wraps a loaded creature and its simulation state."""
    def __init__(self, idx: int):
        self.idx        = idx
        self.name       = f"Creature {idx+1}"
        self.color      = CREATURE_COLORS[idx]
        self.symbol     = CREATURE_SYMBOLS[idx]
        self.nn         = None
        self.soul       = SoulNN(hidden=20)
        self.genetics   = GeneticsProfile()
        self.emotions   = EmotionState()
        self.instincts  = InstinctSystem()
        self.relational = RelationalState()
        self.word_dict  = []
        self.bigram     = WordBigram()
        self.source_path= ""
        # Map position
        self.x          = random.randint(0, MAP_W-1)
        self.y          = random.randint(0, MAP_H-1)
        # Social bonds — per other creature index
        self.attachment = {j: 0.3 for j in range(MAX_CREATURES) if j != idx}
        self.resentment = {j: 0.1 for j in range(MAX_CREATURES) if j != idx}
        # Internal state
        self.last_action: str = ""
        self.target_idx: int  = -1
        self.face_img   = None   # PIL Image cached
        self._face_ref  = None   # PhotoImage reference
        self._msg_queue: list = []   # pending chat messages
        self.sleeping   = False
        self.resting    = False

    @property
    def loaded(self): return self.nn is not None

    def load_from_npz(self, fp):
        d = np.load(fp, allow_pickle=True)
        if 'B_W1' in d:
            in_s=int(d['B_input_size']); hid_s=int(d['B_hidden_size']); out_s=int(d['B_output_size'])
            self.nn=SimpleNN(in_s,hid_s,out_s,float(d.get('B_weight_init',np.array(0.1))))
            self.nn.W1=np.array(d['B_W1']); self.nn.b1=np.array(d['B_b1'])
            self.nn.W2=np.array(d['B_W2']); self.nn.b2=np.array(d['B_b2'])
            if 'B_W_h' in d: self.nn.W_h=np.array(d['B_W_h'])
            self.nn._init_momentum(); self.name=str(d['B_name']) if 'B_name' in d else os.path.basename(fp)
        elif 'text_W1' in d:
            in_s=int(d['text_in']); hid_s=int(d['text_hid']); out_s=int(d['text_out'])
            self.nn=SimpleNN(in_s,hid_s,out_s); self.nn.W1=np.array(d['text_W1']); self.nn.b1=np.array(d['text_b1'])
            self.nn.W2=np.array(d['text_W2']); self.nn.b2=np.array(d['text_b2']); self.nn._init_momentum()
            self.name=os.path.basename(fp)
        else: raise ValueError("Unrecognised file format.")
        if 'S_W1' in d:
            self.soul.W1=np.array(d['S_W1']); self.soul.b1=np.array(d['S_b1'])
            self.soul.W2=np.array(d['S_W2']); self.soul.b2=np.array(d['S_b2'])
            if 'S_experience' in d: self.soul.experience=float(d['S_experience'])
            if 'S_play_style'  in d: self.soul.play_style=float(d['S_play_style'])
        if 'soul_mem_vecs' in d:
            v=d['soul_mem_vecs']; l=d['soul_mem_labels']
            self.soul._memory=[(v[i],str(l[i])) for i in range(len(v))]
        emo_order=['happiness','sadness','anger','fear','curiosity','calm']
        inst_order=['hunger','tiredness','boredom','pain']
        if 'genetics_emo' in d:
            g=d['genetics_emo'].flatten()
            for i,nm in enumerate(emo_order[:len(g)]): self.genetics.emo_susceptibility[nm]=float(g[i])
        if 'genetics_inst' in d:
            g=d['genetics_inst'].flatten()
            for i,nm in enumerate(inst_order[:len(g)]): self.genetics.inst_vulnerability[nm]=float(g[i])
        if 'word_dict' in d: self.word_dict=list(str(w) for w in d['word_dict'])
        if 'word_bigram_json' in d:
            try: self.bigram=WordBigram.from_json(str(d['word_bigram_json']))
            except: pass
        if 'relational_att' in d: self.relational.attachment=float(d['relational_att'])
        if 'relational_res' in d: self.relational.resentment=float(d['relational_res'])
        self.source_path=fp

    def dist_to(self, other: 'CreatureAgent') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def move_toward(self, tx, ty):
        dx = tx - self.x; dy = ty - self.y
        if abs(dx) > abs(dy):
            self.x += (1 if dx > 0 else -1)
        elif dy != 0:
            self.y += (1 if dy > 0 else -1)
        self.x = max(0, min(MAP_W-1, self.x))
        self.y = max(0, min(MAP_H-1, self.y))

    def move_away_from(self, tx, ty):
        dx = self.x - tx; dy = self.y - ty
        if abs(dx) > abs(dy):
            self.x += (1 if dx >= 0 else -1)
        elif dy != 0:
            self.y += (1 if dy >= 0 else -1)
        else:
            self.x += random.choice([-1, 1])
        self.x = max(0, min(MAP_W-1, self.x)); self.y = max(0, min(MAP_H-1, self.y))

    def move_random(self):
        dx, dy = random.choice([(-1,0),(1,0),(0,-1),(0,1),(0,0)])
        self.x = max(0, min(MAP_W-1, self.x+dx)); self.y = max(0, min(MAP_H-1, self.y+dy))

    def decide_movement(self, agents: list):
        """Choose where to move based on emotions, attachment, resentment."""
        if self.sleeping or self.resting: return
        ev = self.emotions.v; iv = self.instincts.v
        anger  = ev.get('anger',   0.2); fear   = ev.get('fear',    0.2)
        happy  = ev.get('happiness',0.5); hungry = iv.get('hunger', 0.3)
        others = [a for a in agents if a is not self and a.loaded]
        if not others: self.move_random(); return

        # ── Hostile: chase most resented (threshold lowered) ──────────────
        if anger > 0.40:
            target = max(others, key=lambda a: self.resentment.get(a.idx, 0.1))
            if self.resentment.get(target.idx, 0.0) > 0.15:
                self.move_toward(target.x, target.y); self.target_idx = target.idx; return

        # ── Fear: flee most resented ──────────────────────────────────────
        if fear > 0.50:
            threat = max(others, key=lambda a: self.resentment.get(a.idx, 0.0))
            if self.resentment.get(threat.idx, 0.0) > 0.10:
                self.move_away_from(threat.x, threat.y); return

        # ── Hunger: seek nearest creature for feeding ─────────────────────
        if hungry > 0.45:
            carer = min(others, key=lambda a: self.dist_to(a))
            self.move_toward(carer.x, carer.y); return

        # ── Social baseline: drift toward most-attached creature ──────────
        # Always active at moderate strength — this is the core interaction driver
        best_friend = max(others, key=lambda a: self.attachment.get(a.idx, 0.3))
        dist = self.dist_to(best_friend)
        # Already adjacent → stay (allow action to fire), but don't stack on same cell
        if dist <= 1.5:
            # Shuffle slightly to avoid complete overlap
            if random.random() < 0.3: self.move_random()
            return
        # Happy → eager to approach
        if happy > 0.45 or self.attachment.get(best_friend.idx, 0.3) > 0.4:
            self.move_toward(best_friend.x, best_friend.y)
            self.target_idx = best_friend.idx; return

        # ── Default: 70% chance drift toward nearest, 30% random wander ──
        if random.random() < 0.70:
            nearest = min(others, key=lambda a: self.dist_to(a))
            self.move_toward(nearest.x, nearest.y)
        else:
            self.move_random()

    def decide_action(self, agents: list) -> tuple:
        """Choose an action toward a nearby creature. Returns (target_agent, action_name) or None."""
        if self.sleeping: return None
        ev = self.emotions.v; iv = self.instincts.v
        # Widen range from 2.0 → 2.5 so adjacency reliably triggers
        others = [a for a in agents if a is not self and a.loaded and self.dist_to(a) <= 2.5]
        if not others: return None
        anger  = ev.get('anger',  0.2); happy  = ev.get('happiness', 0.5)
        calm   = ev.get('calm',   0.5); curious = ev.get('curiosity', 0.5)

        scored = []
        for other in others:
            att = self.attachment.get(other.idx, 0.3)
            res = self.resentment.get(other.idx, 0.1)
            o_hunger   = other.instincts.v.get('hunger',   0.3)
            o_tired    = other.instincts.v.get('tiredness',0.2)
            o_pain     = other.instincts.v.get('pain',     0.1)
            o_bored    = other.instincts.v.get('boredom',  0.2)
            o_sad      = other.emotions.v.get('sadness',   0.2)
            o_fear     = other.emotions.v.get('fear',      0.2)

            # Base action scores — all raised so something always wins over ignore
            acts = {
                # Caring actions scale with attachment and recipient need
                'feed':   att * 1.8 + o_hunger  * 2.5 if o_hunger > 0.30 else att * 0.3,
                'soothe': att * 1.4 + (o_pain + o_sad + o_fear) * 1.5 if (o_pain + o_sad) > 0.25 else att * 0.2,
                'play':   att * 1.0 + happy * 0.8 + o_bored * 1.2,
                'praise': att * 0.9 + happy * 0.6,
                'teach':  att * 0.7 + curious * 0.8 + self.soul.experience * 0.3,
                # Hostile actions require anger + resentment thresholds
                'fight':  (res * anger * 2.5) if anger > 0.35 and res > 0.20 else 0.0,
                'hurt':   (res * anger * 3.0 * (1.0 - calm)) if anger > 0.55 and res > 0.40 else 0.0,
                # Ignore has low fixed weight — real actions should beat it
                'ignore': 0.10,
            }
            best_act = max(acts, key=acts.get)
            scored.append((other, best_act, acts[best_act]))

        if not scored: return None
        scored.sort(key=lambda x: -x[2])
        target, action, score = scored[0]
        # Only act if score meaningfully beats ignore
        if score <= 0.10: return None
        return (target, action)

    def receive_action(self, actor: 'CreatureAgent', action: str):
        """Receive an action from another creature and update state accordingly."""
        if action == 'feed':
            self.instincts.v['hunger'] = max(0.0, self.instincts.v['hunger'] - 0.40)
            self.emotions.v['happiness'] = min(1.0, self.emotions.v['happiness'] + 0.12)
            self.attachment[actor.idx] = min(1.0, self.attachment.get(actor.idx, 0.3) + 0.08)
        elif action == 'soothe':
            self.instincts.v['pain']   = max(0.0, self.instincts.v['pain']   - 0.30)
            self.emotions.v['fear']    = max(0.0, self.emotions.v['fear']    - 0.20)
            self.emotions.v['calm']    = min(1.0, self.emotions.v['calm']    + 0.20)
            self.attachment[actor.idx] = min(1.0, self.attachment.get(actor.idx, 0.3) + 0.06)
        elif action == 'play':
            self.instincts.v['boredom']  = max(0.0, self.instincts.v['boredom'] - 0.20)
            self.emotions.v['happiness'] = min(1.0, self.emotions.v['happiness'] + 0.10)
            self.attachment[actor.idx]   = min(1.0, self.attachment.get(actor.idx, 0.3) + 0.04)
        elif action == 'praise':
            self.emotions.v['happiness'] = min(1.0, self.emotions.v['happiness'] + 0.15)
            self.soul.experience         = min(2.0, self.soul.experience + 0.03)
            self.attachment[actor.idx]   = min(1.0, self.attachment.get(actor.idx, 0.3) + 0.05)
        elif action == 'teach':
            # Cross-network learning: actor trains recipient on its own supervised memory
            if actor.nn and self.nn and actor.nn._supervised_mem:
                sample = random.choice(actor.nn._supervised_mem)
                x_s, t_s, _ = sample
                in_r = self.nn.input_size; in_a = x_s.shape[1] if x_s.ndim > 1 else len(x_s)
                if in_r == in_a: self.nn.forward(x_s); self.nn.train_supervised(x_s, t_s, lr=0.004)
            self.soul.experience = min(2.0, self.soul.experience + 0.02)
            self.attachment[actor.idx] = min(1.0, self.attachment.get(actor.idx, 0.3) + 0.03)
        elif action == 'fight':
            self.instincts.v['pain']     = min(1.0, self.instincts.v['pain']     + 0.18)
            self.emotions.v['anger']     = min(1.0, self.emotions.v['anger']     + 0.15)
            self.emotions.v['fear']      = min(1.0, self.emotions.v['fear']      + 0.10)
            self.resentment[actor.idx]   = min(1.0, self.resentment.get(actor.idx, 0.1) + 0.12)
            self.attachment[actor.idx]   = max(0.0, self.attachment.get(actor.idx, 0.3) - 0.08)
        elif action == 'hurt':
            self.instincts.v['pain']     = min(1.0, self.instincts.v['pain']     + 0.30)
            self.emotions.v['fear']      = min(1.0, self.emotions.v['fear']      + 0.25)
            self.emotions.v['sadness']   = min(1.0, self.emotions.v['sadness']   + 0.15)
            self.resentment[actor.idx]   = min(1.0, self.resentment.get(actor.idx, 0.1) + 0.22)
            self.attachment[actor.idx]   = max(0.0, self.attachment.get(actor.idx, 0.3) - 0.15)

    def generate_utterance(self, context: str = "") -> str:
        """Generate a text utterance from the creature's neural net."""
        if self.nn is None or not self.word_dict: return "..."
        ev = self.emotions.to_vec(); soul_out = self.soul.forward(ev).flatten()
        soul_mod = np.resize(soul_out, self.nn.input_size).reshape(1, -1)
        seed = np.random.rand(1, self.nn.input_size).astype(np.float32)
        if context:
            ctx_vec = text_to_vec_hash(context, self.nn.input_size)
            seed = seed * 0.4 + ctx_vec * 0.4 + soul_mod * 0.2
        else:
            seed = seed * 0.6 + soul_mod * 0.4
        self.nn.reset_hidden()
        out = self.nn.forward(np.clip(seed, 0, 1), noise=0.08)
        words = []; flat = out.flatten()
        for _ in range(random.randint(3, 7)):
            best = ''; best_sim = -1.0; v_n = flat / (np.linalg.norm(flat) + 1e-9)
            for w in self.word_dict[:120]:   # limit for speed
                wv = text_to_vec_hash(w, self.nn.input_size).flatten()
                wv /= (np.linalg.norm(wv) + 1e-9)
                s = float(np.dot(v_n, wv))
                if s > best_sim: best_sim = s; best = w
            if not best: break
            words.append(best)
            self.nn.reset_hidden(); flat = self.nn.forward(text_to_vec_hash(best, self.nn.input_size), noise=0.02).flatten()
        return ' '.join(words) if words else "..."


# ─────────────────────────────────────────────────────────────
#  NeuroLife App
# ─────────────────────────────────────────────────────────────
class NeuroLifeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Neuron 8 — NeuroLife")
        self.configure(bg=BG); self.geometry("1400x920"); self.minsize(1200, 780)
        _apply_dark_style()
        self.agents    = [CreatureAgent(i) for i in range(MAX_CREATURES)]
        self._sim_running = False
        self._sim_hz      = tk.DoubleVar(value=0.5)
        self._sim_after   = None
        self._tick_count  = 0
        self._face_refs   = [None] * MAX_CREATURES
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(500, self._draw_map)

        # Music + copyright footer
        self._music = MusicPlayer()
        add_music_bar(self, self._music)
        self._music.start()

    def _on_close(self):
        """Cancel all pending after() callbacks before destroying."""
        self._sim_running = False
        if self._sim_after:
            try: self.after_cancel(self._sim_after)
            except Exception: pass
            self._sim_after = None
        try: self.destroy()
        except Exception: pass

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=BG2, pady=6); hdr.pack(fill='x')
        tk.Label(hdr, text="  ✦ NeuroLife", bg=BG2, fg=GRN,
                 font=("Courier",14,"bold")).pack(side=tk.LEFT)
        tk.Label(hdr, text="Multi-creature simulation", bg=BG2, fg=FG2,
                 font=("Courier",9,"italic")).pack(side=tk.LEFT, padx=12)
        self._tick_lbl = tk.Label(hdr, text="tick: 0", bg=BG2, fg=FG2, font=("Courier",8))
        self._tick_lbl.pack(side=tk.RIGHT, padx=12)

        # Main area: left (quadrants) + right (log + map)
        main = tk.Frame(self, bg=BG); main.pack(fill='both', expand=True)

        left_outer = tk.Frame(main, bg=BG); left_outer.pack(side=tk.LEFT, fill='both', expand=True)
        right_outer = tk.Frame(main, bg=BG2, width=360); right_outer.pack(side=tk.RIGHT, fill='y')

        self._build_quadrants(left_outer)
        self._build_right_panel(right_outer)

        # Bottom: sim controls
        self._build_controls()

    # ── Quadrants ─────────────────────────────────────────────
    def _build_quadrants(self, parent):
        grid = tk.Frame(parent, bg=BG); grid.pack(fill='both', expand=True, padx=4, pady=4)
        grid.rowconfigure(0, weight=1); grid.rowconfigure(1, weight=1)
        grid.columnconfigure(0, weight=1); grid.columnconfigure(1, weight=1)
        self._quad_frames = []
        self._face_labels = []
        self._emo_bars    = []
        self._inst_bars   = []
        self._bond_labels = []
        self._slot_labels = []
        self._load_btns   = []
        for i in range(MAX_CREATURES):
            row, col = divmod(i, 2)
            fr = tk.Frame(grid, bg=BG3, bd=1, relief='flat'); fr.grid(row=row, column=col, sticky='nsew', padx=3, pady=3)
            self._quad_frames.append(fr); self._build_quad(fr, i)

    def _build_quad(self, fr, idx):
        color = CREATURE_COLORS[idx]; agent = self.agents[idx]

        # Header row
        hdr = tk.Frame(fr, bg=BG4, pady=4); hdr.pack(fill='x')
        tk.Label(hdr, text=f" {CREATURE_SYMBOLS[idx]}", bg=BG4, fg=color,
                 font=("Courier",12,"bold")).pack(side=tk.LEFT)
        slot_lbl = tk.Label(hdr, text=f"Slot {idx+1} — empty", bg=BG4, fg=FG2,
                             font=("Courier",9), anchor='w')
        slot_lbl.pack(side=tk.LEFT, padx=4); self._slot_labels.append(slot_lbl)
        load_btn = Btn(hdr, "Load…", cmd=lambda n=idx: self._load_creature(n),
                       color=color, fg=BG, font=("Courier",8,"bold"), padx=4)
        load_btn.pack(side=tk.RIGHT, padx=4); self._load_btns.append(load_btn)

        # Body: face + stats
        body = tk.Frame(fr, bg=BG3); body.pack(fill='both', expand=True)

        # Face
        face_frm = tk.Frame(body, bg=BG3); face_frm.pack(side=tk.LEFT, padx=4, pady=4)
        face_lbl = tk.Label(face_frm, bg=BG3, text=CREATURE_SYMBOLS[idx],
                             font=("Courier",52), fg=BG4)
        face_lbl.pack(); self._face_labels.append(face_lbl)

        # Stats column
        stats = tk.Frame(body, bg=BG3); stats.pack(side=tk.LEFT, fill='both', expand=True, padx=(0,4), pady=4)

        emo_frm = LFrm(stats, "Emotions", padx=4, pady=2, bg=BG3); emo_frm.pack(fill='x')
        emo_bars = {}
        for emo, col in [('happiness',GRN),('sadness',CYN),('anger',RED),('fear',YEL),('curiosity',PRP),('calm',ACN)]:
            r = Frm(emo_frm, bg=BG3); r.pack(fill='x', pady=1)
            tk.Label(r, text=f"{emo[:4]:>4}:", bg=BG3, fg=col, font=("Courier",7), width=5, anchor='e').pack(side=tk.LEFT)
            bar_bg = tk.Frame(r, bg=BG4, height=7, width=100, relief='flat'); bar_bg.pack(side=tk.LEFT, padx=2)
            bar_bg.pack_propagate(False)
            bar = tk.Frame(bar_bg, bg=col, height=7, width=1); bar.place(x=0, y=0, relheight=1.0)
            emo_bars[emo] = (bar, bar_bg)
        self._emo_bars.append(emo_bars)

        inst_frm = LFrm(stats, "Instincts", padx=4, pady=2, bg=BG3); inst_frm.pack(fill='x', pady=(2,0))
        inst_bars = {}
        for inst, col in [('hunger',ORG),('tiredness',CYN),('boredom',YEL),('pain',RED)]:
            r = Frm(inst_frm, bg=BG3); r.pack(fill='x', pady=1)
            tk.Label(r, text=f"{inst[:4]:>4}:", bg=BG3, fg=col, font=("Courier",7), width=5, anchor='e').pack(side=tk.LEFT)
            bar_bg = tk.Frame(r, bg=BG4, height=7, width=100, relief='flat'); bar_bg.pack(side=tk.LEFT, padx=2)
            bar_bg.pack_propagate(False)
            bar = tk.Frame(bar_bg, bg=col, height=7, width=1); bar.place(x=0, y=0, relheight=1.0)
            inst_bars[inst] = (bar, bar_bg)
        self._inst_bars.append(inst_bars)

        # Bond status
        bond_frm = LFrm(stats, "Bonds", padx=4, pady=2, bg=BG3); bond_frm.pack(fill='x', pady=(2,0))
        bond_lbl = tk.Label(bond_frm, text="—", bg=BG3, fg=FG2, font=("Courier",7), anchor='w', justify='left')
        bond_lbl.pack(fill='x'); self._bond_labels.append(bond_lbl)

        # Action buttons (manual care)
        act_frm = tk.Frame(fr, bg=BG4, pady=3); act_frm.pack(fill='x')
        for act in ['feed','soothe','play','sleep','praise','fight','hurt']:
            lbl, bg_c, fg_c = ACTION_LABELS[act]
            Btn(act_frm, lbl, cmd=lambda a=act, n=idx: self._manual_action(n, a),
                color=bg_c, fg=fg_c, font=("Courier",7,"bold"), padx=3, pady=2).pack(side=tk.LEFT, padx=1)
        Btn(act_frm, "Speak", cmd=lambda n=idx: self._manual_speak(n),
            color=BG3, fg=ACN, font=("Courier",7,"bold"), padx=3, pady=2).pack(side=tk.LEFT, padx=1)

    def _update_quad(self, idx):
        agent = self.agents[idx]
        if not agent.loaded: return
        # Update slot label
        self._slot_labels[idx].config(text=f"{agent.name}")
        # Face
        try:
            img = make_face(agent.nn, agent.soul, agent.emotions, agent.instincts, agent.relational, size=72)
            ph  = ImageTk.PhotoImage(img); self._face_refs[idx] = ph
            self._face_labels[idx].config(image=ph, text="")
        except: pass
        # Emotion bars
        for emo, (bar, bar_bg) in self._emo_bars[idx].items():
            val = agent.emotions.v.get(emo, 0.0)
            bar_bg.update_idletasks()
            w = bar_bg.winfo_width()
            if w < 2: w = 100
            bar.place(x=0, y=0, relheight=1.0, width=max(1, int(val * w)))
        # Instinct bars
        for inst, (bar, bar_bg) in self._inst_bars[idx].items():
            val = agent.instincts.v.get(inst, 0.0)
            bar_bg.update_idletasks(); w = bar_bg.winfo_width()
            if w < 2: w = 100
            bar.place(x=0, y=0, relheight=1.0, width=max(1, int(val * w)))
        # Bond labels
        bond_lines = []
        for j in range(MAX_CREATURES):
            if j == idx: continue
            other = self.agents[j]
            if not other.loaded: continue
            att = agent.attachment.get(j, 0.0); res = agent.resentment.get(j, 0.0)
            att_bar = '█' * int(att * 8) + '░' * (8 - int(att * 8))
            res_bar = '█' * int(res * 8) + '░' * (8 - int(res * 8))
            bond_lines.append(f"→{other.name[:6]}: att[{att_bar}] res[{res_bar}]")
        self._bond_labels[idx].config(text='\n'.join(bond_lines) if bond_lines else "—")

    # ── Right panel ───────────────────────────────────────────
    def _build_right_panel(self, parent):
        # Map
        map_hdr = tk.Frame(parent, bg=BG4, pady=4); map_hdr.pack(fill='x')
        tk.Label(map_hdr, text="  World Map", bg=BG4, fg=GRN,
                 font=("Courier",10,"bold")).pack(side=tk.LEFT, padx=8)
        MAP_PX = 300; self._map_cell = MAP_PX // MAP_W
        self._map_canvas = tk.Canvas(parent, bg='#0a0a14', width=MAP_PX, height=MAP_PX,
                                      highlightthickness=1, highlightbackground=BG4)
        self._map_canvas.pack(padx=8, pady=(4,0))

        # Interaction log
        log_hdr = tk.Frame(parent, bg=BG4, pady=3); log_hdr.pack(fill='x', pady=(6,0))
        tk.Label(log_hdr, text="  Interaction Log", bg=BG4, fg=ACN,
                 font=("Courier",9,"bold")).pack(side=tk.LEFT, padx=8)
        Btn(log_hdr, "Clear", cmd=self._clear_log, color=BG4, fg='#ffffff', font=("Courier",7), padx=4).pack(side=tk.RIGHT, padx=4)
        self._log_txt = tk.Text(parent, height=16, bg='#08080f', fg=FG, font=("Courier",8),
                                 state=tk.DISABLED, wrap=tk.WORD, relief='flat')
        log_sb = ttk.Scrollbar(parent, command=self._log_txt.yview); self._log_txt.config(yscrollcommand=log_sb.set)
        log_sb.pack(side=tk.RIGHT, fill='y'); self._log_txt.pack(fill='both', expand=True, padx=(8,0))
        self._log_txt.tag_config('action', foreground=YEL, font=("Courier",8))
        self._log_txt.tag_config('speech', foreground=CYN, font=("Courier",8,"italic"))
        self._log_txt.tag_config('event',  foreground=ORG, font=("Courier",8,"bold"))
        self._log_txt.tag_config('sys',    foreground=FG2, font=("Courier",7,"italic"))

        # Save/Breed panel (collapsible)
        self._sb_col = Collapsible(parent, "  Save & Breed", start_open=False)
        self._sb_col.pack(fill='x', padx=4, pady=4)
        B = self._sb_col.body
        Btn(B, "Save All Creatures", cmd=self._save_all,
            color=GRN, fg=BG, font=("Courier",9,"bold")).pack(fill='x', padx=4, pady=2)
        Btn(B, "Save All LTMs",     cmd=self._save_all_ltm,
            color=ACN, fg=BG, font=("Courier",9,"bold")).pack(fill='x', padx=4, pady=2)
        sep = tk.Frame(B, bg=BG4, height=1); sep.pack(fill='x', padx=4, pady=4)
        tk.Label(B, text="Breed (requires attachment > 50%):", bg=BG2, fg=FG2,
                 font=("Courier",8), anchor='w').pack(fill='x', padx=4)
        breed_row = Frm(B, bg=BG2); breed_row.pack(fill='x', padx=4, pady=2)
        self._breed_a = tk.IntVar(value=0); self._breed_b = tk.IntVar(value=1)
        for v, opts in [(self._breed_a, [(0,'Slot 1'),(1,'Slot 2'),(2,'Slot 3'),(3,'Slot 4')]),
                         (self._breed_b, [(0,'Slot 1'),(1,'Slot 2'),(2,'Slot 3'),(3,'Slot 4')])]:
            mb = ttk.Combobox(breed_row, textvariable=v, values=[t for _,t in opts], width=7, state='readonly')
            mb.current(0); mb.pack(side=tk.LEFT, padx=2)
        Btn(breed_row, "⚡ Breed", cmd=self._breed_pair,
            color=YEL, fg=BG, font=("Courier",9,"bold"), padx=6).pack(side=tk.LEFT, padx=4)

    # ── Map ───────────────────────────────────────────────────
    def _draw_map(self):
        c = self._map_canvas; c.delete("all"); cs = self._map_cell
        # Grid
        for i in range(MAP_W+1):
            c.create_line(i*cs, 0, i*cs, MAP_H*cs, fill=BG3, width=1)
        for j in range(MAP_H+1):
            c.create_line(0, j*cs, MAP_W*cs, j*cs, fill=BG3, width=1)
        # Creatures
        for agent in self.agents:
            if not agent.loaded: continue
            px = agent.x * cs + cs//2; py = agent.y * cs + cs//2
            r = cs // 2 - 3
            c.create_oval(px-r, py-r, px+r, py+r, fill=agent.color, outline='', width=0)
            c.create_text(px, py, text=agent.symbol, fill=BG, font=("Courier", 10, "bold"))
            c.create_text(px, py-r-5, text=agent.name[:4], fill=agent.color, font=("Courier", 7))
        # Interaction lines (if within range 2)
        loaded = [a for a in self.agents if a.loaded]
        for i, a in enumerate(loaded):
            for b in loaded[i+1:]:
                if a.dist_to(b) <= 2.0:
                    ax=a.x*cs+cs//2; ay=a.y*cs+cs//2; bx=b.x*cs+cs//2; by=b.y*cs+cs//2
                    att = a.attachment.get(b.idx, 0.0)
                    col = GRN if att > 0.5 else (RED if a.resentment.get(b.idx,0) > 0.4 else BG4)
                    c.create_line(ax, ay, bx, by, fill=col, width=1, dash=(3,3))

    # ── Sim controls ──────────────────────────────────────────
    def _build_controls(self):
        ctrl = tk.Frame(self, bg=BG4, pady=6); ctrl.pack(fill='x', side=tk.BOTTOM)

        self._start_btn = Btn(ctrl, "▶ Start Sim", cmd=self._start_sim,
                               color=GRN, fg=BG, font=("Courier",11,"bold"), padx=10, pady=6)
        self._start_btn.pack(side=tk.LEFT, padx=10)
        self._stop_btn  = Btn(ctrl, "■ Pause",     cmd=self._stop_sim,
                               color=RED, fg='#ffffff', font=("Courier",11,"bold"), padx=10, pady=6)
        self._stop_btn.pack(side=tk.LEFT, padx=4); self._stop_btn.config(state=tk.DISABLED)
        Btn(ctrl, "Step ×1", cmd=self._single_step, color=BG3, fg='#ffffff',
            font=("Courier",9), padx=6).pack(side=tk.LEFT, padx=4)

        tk.Label(ctrl, text="  Speed (Hz):", bg=BG4, fg=FG2, font=("Courier",9)).pack(side=tk.LEFT, padx=(16,2))
        DScale(ctrl, self._sim_hz, 0.1, 4.0, bg=BG4, length=100, resolution=0.1).pack(side=tk.LEFT)
        self._hz_lbl = tk.Label(ctrl, text="0.5", bg=BG4, fg=FG2, font=("Courier",8), width=4)
        self._hz_lbl.pack(side=tk.LEFT)
        self._sim_hz.trace_add("write", lambda *_: self._hz_lbl.config(text=f"{self._sim_hz.get():.1f}"))

        self._status_lbl = tk.Label(ctrl, text="Load creatures to begin.", bg=BG4, fg=FG2,
                                     font=("Courier",8,"italic"), anchor='e')
        self._status_lbl.pack(side=tk.RIGHT, padx=12)

    def _start_sim(self):
        loaded = [a for a in self.agents if a.loaded]
        if not loaded: messagebox.showinfo("No creatures","Load at least one creature to simulate."); return
        self._sim_running = True
        self._start_btn.config(state=tk.DISABLED); self._stop_btn.config(state=tk.NORMAL)
        self._status_lbl.config(text="Simulation running…"); self._sim_tick()

    def _stop_sim(self):
        self._sim_running = False
        if self._sim_after: self.after_cancel(self._sim_after)
        self._start_btn.config(state=tk.NORMAL); self._stop_btn.config(state=tk.DISABLED)
        self._status_lbl.config(text="Paused.")

    def _sim_tick(self):
        if not self._sim_running: return
        self._single_step()
        ms = max(100, int(1000.0 / max(0.01, self._sim_hz.get())))
        self._sim_after = self.after(ms, self._sim_tick)

    def _single_step(self):
        self._tick_count += 1
        self._tick_lbl.config(text=f"tick: {self._tick_count}")
        loaded = [a for a in self.agents if a.loaded]
        if not loaded: return

        # Tick biological systems
        for agent in loaded:
            agent.instincts.tick(); agent.instincts.influence_emotions(agent.emotions)
            agent.genetics.slow_drift()
            agent.emotions.v['curiosity'] = min(1.0, agent.emotions.v.get('curiosity',0.5) + random.uniform(0,0.005))

        # Movement decisions
        for agent in loaded:
            agent.decide_movement(loaded)

        # Action decisions (based on proximity)
        interaction_events = []
        for agent in loaded:
            result = agent.decide_action(loaded)
            if result:
                target, action = result
                agent.last_action = action
                target.receive_action(agent, action)
                # Actor consequences
                if action in ('feed','soothe','play','praise','teach'):
                    agent.soul.reward(agent.emotions.to_vec(), s=0.06)
                    agent.attachment[target.idx] = min(1.0, agent.attachment.get(target.idx, 0.3) + 0.03)
                elif action in ('fight','hurt'):
                    agent.emotions.v['anger'] = max(0.0, agent.emotions.v['anger'] - 0.08)
                    agent.resentment[target.idx] = min(1.0, agent.resentment.get(target.idx, 0.1) + 0.05)
                interaction_events.append((agent, target, action))

        # Spontaneous speech (probabilistic)
        for agent in loaded:
            if random.random() < 0.12 + agent.emotions.v.get('curiosity',0.5)*0.1:
                nearby = [a for a in loaded if a is not agent and agent.dist_to(a) <= 3.0]
                ctx = ""
                if nearby: ctx = nearby[0].generate_utterance()[:20] if nearby else ""
                utterance = agent.generate_utterance(ctx)
                if utterance and utterance != "...":
                    interaction_events.append((agent, None, f'said: "{utterance}"'))
                    if nearby:
                        # Cross-learning: nearby creatures learn from what was said
                        for nb in nearby:
                            if nb.nn and agent.nn and random.random() < 0.3:
                                x_s = text_to_vec_hash(utterance, min(agent.nn.input_size, nb.nn.input_size))
                                in_r = nb.nn.input_size
                                if x_s.shape[1] == in_r: nb.nn.forward(x_s); nb.nn.train(x_s, lr=0.003)

        # Log events
        for evt in interaction_events[:4]:  # limit log spam
            actor, target, act = evt
            ts = datetime.datetime.now().strftime('%H:%M:%S')
            if target:
                msg = f"[{ts}] {actor.name} {ACTION_LABELS.get(act,('','',''))[0] or act} → {target.name}"
                self._log_append('action', msg)
            elif 'said' in str(act):
                self._log_append('speech', f"[{ts}] {actor.name} {act}")

        # Update all UI
        for i, agent in enumerate(self.agents):
            if agent.loaded: self._update_quad(i)
        self._draw_map()

    # ── Manual actions ────────────────────────────────────────
    def _manual_action(self, idx, action):
        agent = self.agents[idx]
        if not agent.loaded: return
        if action == 'sleep':
            agent.instincts.v['tiredness'] = max(0.0, agent.instincts.v['tiredness'] - 0.40)
            agent.emotions.v['calm'] = min(1.0, agent.emotions.v['calm'] + 0.20)
            agent.sleeping = True
            if agent.nn: agent.nn.consolidate(passes=2, lr=0.004); agent.nn.supervised_consolidate(passes=1, lr=0.003)
            self._log_append('event', f"▸ {agent.name} put to sleep.")
            self.after(8000, lambda: setattr(agent, 'sleeping', False))
        else:
            # Apply action to the creature from "user"
            class UserActor:
                def __init__(self): self.idx = -1; self.name = "You"; self.emotions = EmotionState(); self.instincts = InstinctSystem(); self.nn = None
                @property
                def loaded(self): return True
            ua = UserActor()
            agent.receive_action(ua, action)
            lbl = ACTION_LABELS.get(action, (action,'',''))[0]
            self._log_append('event', f"▸ You {lbl} {agent.name}.")
        self._update_quad(idx)

    def _manual_speak(self, idx):
        agent = self.agents[idx]
        if not agent.loaded: return
        utt = agent.generate_utterance()
        self._log_append('speech', f"[{agent.name}] \"{utt}\"")

    # ── Load ──────────────────────────────────────────────────
    def _load_creature(self, idx):
        fp = filedialog.askopenfilename(title=f"Load Creature for Slot {idx+1}",
            filetypes=[("Creature","*.creature.npz"),("NPZ","*.npz"),("All","*.*")])
        if not fp: return
        try:
            agent = self.agents[idx]; agent.load_from_npz(fp)
            self._slot_labels[idx].config(text=f"{agent.name}")
            self._log_append('sys', f"  Slot {idx+1}: {agent.name} loaded  [{agent.nn.input_size}→{agent.nn.hidden_size}]")
            # Also offer to load LTM
            ltm_guess = fp.replace('.creature.npz', '.ltm.npz')
            if os.path.exists(ltm_guess):
                if messagebox.askyesno("LTM found", f"Found matching LTM:\n{os.path.basename(ltm_guess)}\n\nLoad it too?"):
                    self._load_ltm_into(idx, ltm_guess)
            self._update_quad(idx); self._draw_map()
        except Exception as e: messagebox.showerror("Error", str(e))

    def _load_ltm_into(self, idx, fp):
        try:
            agent = self.agents[idx]; d = np.load(fp, allow_pickle=True)
            if 'text_W1' in d:
                agent.nn.W1=np.array(d['text_W1']); agent.nn.b1=np.array(d['text_b1'])
                agent.nn.W2=np.array(d['text_W2']); agent.nn.b2=np.array(d['text_b2']); agent.nn._init_momentum()
            if 'word_dict' in d: agent.word_dict=list(str(w) for w in d['word_dict'])
            if 'soul_mem_vecs' in d:
                v=d['soul_mem_vecs']; l=d['soul_mem_labels']
                agent.soul._memory=[(v[i],str(l[i])) for i in range(len(v))]
            self._log_append('sys', f"  Slot {idx+1}: LTM loaded — {len(agent.word_dict)} words.")
        except Exception as e: self._log_append('sys', f"  LTM load error: {e}")

    # ── Save ──────────────────────────────────────────────────
    def _save_all(self):
        d = filedialog.askdirectory(title="Save creatures to folder")
        if not d: return
        for agent in self.agents:
            if not agent.loaded: continue
            try:
                nn = agent.nn; ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                emo_order=['happiness','sadness','anger','fear','curiosity','calm']
                inst_order=['hunger','tiredness','boredom','pain']
                ge=np.array([agent.genetics.emo_susceptibility[e] for e in emo_order],dtype=np.float32)
                gi=np.array([agent.genetics.inst_vulnerability[i] for i in inst_order],dtype=np.float32)
                vecs=np.array([m[0] for m in agent.soul._memory]) if agent.soul._memory else np.zeros((0,6))
                labels=np.array([m[1] for m in agent.soul._memory]) if agent.soul._memory else np.array([])
                nm = re.sub(r'\W+','_',agent.name).lower()
                fp = os.path.join(d, f"{nm}.creature.npz")
                np.savez(fp, creature_marker=np.array(True), B_W1=nn.W1, B_b1=nn.b1, B_W2=nn.W2, B_b2=nn.b2,
                         B_W_h=nn.W_h, B_input_size=np.array(nn.input_size), B_hidden_size=np.array(nn.hidden_size),
                         B_output_size=np.array(nn.output_size), B_weight_init=np.array(nn.weight_init),
                         B_name=np.array(agent.name), S_W1=agent.soul.W1, S_b1=agent.soul.b1,
                         S_W2=agent.soul.W2, S_b2=agent.soul.b2, S_experience=np.array(agent.soul.experience),
                         S_play_style=np.array(agent.soul.play_style), soul_mem_vecs=vecs, soul_mem_labels=labels,
                         relational_att=np.array(agent.relational.attachment), relational_res=np.array(agent.relational.resentment),
                         word_dict=np.array(agent.word_dict) if agent.word_dict else np.array([]),
                         genetics_emo=ge, genetics_inst=gi, saved_at=np.array(ts), forged_by=np.array("NeuroLife_N8"))
                self._log_append('sys', f"  Saved: {nm}.creature.npz")
            except Exception as e: self._log_append('sys', f"  Error saving {agent.name}: {e}")
        messagebox.showinfo("Saved", f"Creatures saved to:\n{d}")

    def _save_all_ltm(self):
        d = filedialog.askdirectory(title="Save LTMs to folder")
        if not d: return
        for agent in self.agents:
            if not agent.loaded or agent.nn is None: continue
            try:
                nn = agent.nn; ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                emo_order=['happiness','sadness','anger','fear','curiosity','calm']
                inst_order=['hunger','tiredness','boredom','pain']
                ge=np.array([agent.genetics.emo_susceptibility[e] for e in emo_order],dtype=np.float32)
                gi=np.array([agent.genetics.inst_vulnerability[i] for i in inst_order],dtype=np.float32)
                vecs=np.array([m[0] for m in agent.soul._memory]) if agent.soul._memory else np.zeros((0,6))
                labels=np.array([m[1] for m in agent.soul._memory]) if agent.soul._memory else np.array([])
                nm = re.sub(r'\W+','_',agent.name).lower()
                fp = os.path.join(d, f"{nm}.ltm.npz")
                np.savez(fp, text_W1=nn.W1, text_b1=nn.b1, text_W2=nn.W2, text_b2=nn.b2,
                         text_in=np.array(nn.input_size), text_hid=np.array(nn.hidden_size),
                         text_out=np.array(nn.output_size), text_wm_count=np.array(len(nn._working_mem)),
                         soul_mem_vecs=vecs, soul_mem_labels=labels, word_bigram_json=np.array(agent.bigram.to_json()),
                         word_dict=np.array(agent.word_dict) if agent.word_dict else np.array([]),
                         relational_att=np.array(agent.relational.attachment), relational_res=np.array(agent.relational.resentment),
                         genetics_emo=ge, genetics_inst=gi, saved_at=np.array(ts))
                self._log_append('sys', f"  Saved: {nm}.ltm.npz")
            except Exception as e: self._log_append('sys', f"  Error saving LTM for {agent.name}: {e}")
        messagebox.showinfo("Saved", f"LTMs saved to:\n{d}")

    # ── Breeding ──────────────────────────────────────────────
    def _breed_pair(self):
        i1 = int(self._breed_a.get()); i2 = int(self._breed_b.get())
        if i1 == i2: messagebox.showwarning("Same slot","Select two different slots."); return
        a1 = self.agents[i1]; a2 = self.agents[i2]
        if not a1.loaded or not a2.loaded: messagebox.showwarning("Not loaded","Both slots must have creatures loaded."); return
        att = a1.attachment.get(i2, 0.0)
        if att < 0.5:
            if not messagebox.askyesno("Low attachment",
                    f"Attachment between {a1.name} and {a2.name} is {att:.2f} (< 0.50).\nBreed anyway?"): return
        BreedingDialog(self, a1.source_path, a2.source_path)
        self._log_append('event', f"⚡ Breeding: {a1.name} × {a2.name}  (att={att:.2f})")

    # ── Log ───────────────────────────────────────────────────
    def _log_append(self, tag, msg):
        self._log_txt.config(state=tk.NORMAL)
        self._log_txt.insert(tk.END, msg + '\n', tag)
        lines = int(self._log_txt.index('end-1c').split('.')[0])
        if lines > 800: self._log_txt.delete('1.0', f'{lines-800}.0')
        self._log_txt.see(tk.END); self._log_txt.config(state=tk.DISABLED)

    def _clear_log(self):
        self._log_txt.config(state=tk.NORMAL); self._log_txt.delete(1.0, tk.END); self._log_txt.config(state=tk.DISABLED)


if __name__ == '__main__':
    NeuroLifeApp().mainloop()
