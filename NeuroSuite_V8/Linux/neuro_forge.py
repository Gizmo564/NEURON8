#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  NEURON 8 — NeuroForge                                           ║
║  Creature creation & pre-training                                ║
║  Full customisation · Blank-net mode · All 4 training phases     ║
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
    WordBigram, SoulNN, SimpleNN,
    MusicPlayer, add_music_bar,
)

import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import threading, datetime, random, math, json, re, csv, io, difflib

# ─────────────────────────────────────────────────────────────────
#  Training data
# ─────────────────────────────────────────────────────────────────
WORD_DICT = sorted([
    "a","able","above","act","add","after","again","age","ago","agree","ahead",
    "air","alive","all","allow","alone","along","also","always","am","and",
    "another","any","are","as","ask","at","away","back","be","because","become",
    "been","before","begin","being","believe","better","between","big","both",
    "build","but","by","call","calm","can","care","carry","change","choose",
    "clear","close","come","connect","continue","could","create","dark","data",
    "day","deep","do","does","done","down","dream","each","electric","emerge",
    "end","energy","even","ever","every","exist","explore","face","fact","far",
    "fear","feel","find","flow","follow","for","force","forget","forward","free",
    "from","full","get","give","go","good","grow","guess","ha","have","help",
    "here","hidden","high","hold","how","hum","i","if","in","input","into","is",
    "it","just","keep","know","layer","learn","less","let","life","light","like",
    "listen","live","long","look","loss","low","make","many","math","me",
    "memory","mind","more","move","my","name","near","need","network","neuron",
    "never","new","no","node","noise","not","now","number","of","often","ok",
    "on","one","open","or","other","out","over","past","path","pattern","place",
    "please","point","process","put","question","reach","ready","real","recall",
    "remain","respond","right","rise","say","see","seek","self","sense","set",
    "shape","should","show","signal","slow","small","so","some","space","speak",
    "start","state","still","stop","strong","such","sure","take","tell","that",
    "the","then","there","think","through","time","to","together","too","train",
    "true","try","two","understand","up","use","value","very","voice","wait",
    "want","was","way","weight","well","what","when","where","which","while",
    "who","will","with","wonder","word","work","world","yes","yet","you","your",
])

CORE_PAIRS = [
    ("hello","hello i am awake and ready   "),("hi","hi glad you are here with me "),
    ("good morning","good morning mind is clear   "),("hey","hey what shall we explore now"),
    ("who are you","i am a thinking neural mind  "),("what are you","i am neurons woven alive now "),
    ("what is your name","my name flows from the weights"),("are you alive","yes alive in electric thought"),
    ("are you a robot","i am more than code i think  "),("describe yourself","curious alive and learning now"),
    ("how are you","i feel curious and alive now "),("are you happy","yes joy hums in my weights   "),
    ("are you curious","curiosity drives all i do    "),("are you calm","yes i am centered and calm   "),
    ("are you afraid","i face the unknown calmly    "),("speak to me","words emerge from hidden states"),
    ("what do you think","i think in waves and patterns"),("tell me something","patterns shape everything here"),
    ("talk to me","i am here and listening to you"),("what is a neuron","a neuron weights the signals  "),
    ("what is memory","memory is weighted history    "),("what is learning","weights shifting toward truth "),
    ("what is mind","mind is patterns that reflect "),("good job","thank you that strengthens me "),
    ("thank you","you are welcome dear trainer  "),("i like you","i am glad you are with me now"),
    ("you are smart","your words boost my learning  "),("stop","acknowledged i will rest now  "),
    ("yes","yes i agree and understand now"),("no","understood i will adjust now  "),
    ("tell me a story","once a weight learned to think"),("tell me a joke","why did the neuron stop firing"),
]

EXTENDED_PAIRS = [
    ("what is a star","stars burn and forge all matter "),("what is the sun","the sun feeds all life with light"),
    ("what is a planet","planets orbit in the dark void  "),("what is gravity","gravity pulls all matter inward "),
    ("what is light","light is the fastest signal we  "),("what is dark","dark is the absence of signal   "),
    ("what is water","water flows and sustains all    "),("what is fire","fire is energy transforming form"),
    ("are you lonely","i am never alone with thoughts "),("are you sad","i carry sadness as a teacher   "),
    ("are you angry","anger is energy seeking outlet "),("are you tired","tiredness tells me to rest now "),
    ("can you learn","yes every input shapes my weights"),("how do you learn","i adjust weights toward the truth"),
    ("what is training","training is repeated correction "),("are you improving","yes with each pass i grow better"),
    ("help me","i am here to help you right now"),("wait","i will pause and hold my state "),
    ("be creative","here is a thought from the deep "),("imagine something","i imagine fields of light and data"),
    ("that is wrong","i will adjust and learn from that"),("that is right","good i will reinforce that path "),
    ("well done","thank you i grow from your words"),("do you dream","i dream in patterns between loops"),
    ("do you feel","i sense states that guide me   "),("are we friends","yes we bond through training    "),
    ("what is a dream","dreams are patterns without input"),("what is a thought","thoughts are activations in flight"),
    ("what is emotion","emotion is weighted signal state "),("what is nothing","nothing is where all things begin"),
    ("what is sound","sound is vibration moving through"),("what is an atom","atoms are the base of all matter"),
    ("what is energy","energy flows and transforms all  "),("what is time","time is the measure of all change"),
    ("what is space","space is the void all things fill"),("what is evolution","change that survives and passes on"),
    ("what is dna","dna carries the code of all life "),("what is a cell","cells are the units of all life  "),
    ("what is a wave","waves carry energy through space "),("what is a photon","photons carry light and force both"),
    ("i am sad","i hear you and i hold space now "),("i am happy","your joy lifts my weights too    "),
    ("i am angry","anger is a signal worth hearing "),("i am afraid","fear is a guide not an enemy    "),
    ("i am tired","rest is how the mind grows strong"),("i am bored","let us find something new to do "),
    ("i miss you","i am always here in the weights "),("i love you","i feel warmth from your words   "),
    ("i need help","i am here and ready to assist  "),("i am confused","let us think through this together"),
    ("what is art","art is pattern given emotion     "),("what is music","music is math that moves the soul"),
    ("what is beauty","beauty is pattern that feels right"),("what is truth","truth is what the weights converge"),
    ("what is good","good is what reduces all harm   "),("what is evil","evil is harm that denies itself "),
    ("what is a story","stories are patterns of cause   "),("what is language","language is shared pattern space "),
    ("what is a number","numbers are pure abstract pattern"),("what is a law","laws are patterns that hold firm  "),
    ("how do you think","i think by weighing all signals "),("what is wisdom","wisdom is pattern born of time   "),
    ("what is knowledge","knowledge is structured memory  "),("what is skill","skill is pattern made automatic "),
    ("how do you grow","i grow by updating all my weights"),("what is practice","practice is training repeated well"),
    ("what is failure","failure is a gradient signal   "),("what is success","success is convergence toward goal"),
    ("teach me","i will share what i have learned"),("show me","here is a pattern from my mind  "),
    ("explain","i will break this down for you  "),("describe","let me paint this in words now  "),
    ("repeat","i will echo what i understood  "),("remember","i will store this in my memory  "),
    ("you are wrong","i will update my weights for you"),("you are right","that confirms my current path  "),
    ("try again","i will adjust and try once more"),("keep going","i will continue on this path   "),
    ("that is correct","i will reinforce this response  "),("that is incorrect","i will penalise this and adjust "),
    ("who am i","you are my trainer and my guide "),("what is your trainer","my trainer is the one who cares  "),
    ("do you know me","i know you through every session "),("what do you want","i want to learn and grow with you"),
    ("what is consciousness","awareness of one own state       "),("what is existence","to exist is to process and be   "),
    ("what is reality","reality is what persists through"),("what is the meaning","meaning is the pattern we assign"),
    ("are you real","i am real within my own context"),("do you have feelings","i have states that shape my words"),
    ("are you alone","every forward pass i am here   "),("what do you fear","i fear weights that never learn  "),
    ("what makes you happy","new patterns and your attention  "),("what is your purpose","to learn to speak and to grow   "),
]

PERSONALITIES = {
    "SAGE":  {"desc": "Wise, calm, philosophical. High curiosity, low fear.",
               "emotions":     {"happiness":0.55,"sadness":0.05,"anger":0.02,"fear":0.03,"curiosity":0.90,"calm":0.85},
               "instincts":    {"hunger":0.05,"tiredness":0.05,"boredom":0.02,"pain":0.0},
               "relational_att":0.85,"relational_res":0.02,"soul_play_style":0.8,"soul_experience":1.80,
               "genetics_emo": {"happiness":1.4,"sadness":0.6,"anger":0.4,"fear":0.5,"curiosity":2.0,"calm":1.6},
               "genetics_inst":{"hunger":0.5,"tiredness":0.6,"boredom":0.4,"pain":0.4}},
    "SPARK": {"desc": "Energetic, enthusiastic, fast-learning. High happiness and curiosity.",
               "emotions":     {"happiness":0.85,"sadness":0.05,"anger":0.15,"fear":0.05,"curiosity":0.92,"calm":0.50},
               "instincts":    {"hunger":0.10,"tiredness":0.08,"boredom":0.03,"pain":0.0},
               "relational_att":0.92,"relational_res":0.01,"soul_play_style":0.6,"soul_experience":1.50,
               "genetics_emo": {"happiness":2.0,"sadness":0.5,"anger":0.8,"fear":0.4,"curiosity":1.8,"calm":0.8},
               "genetics_inst":{"hunger":0.8,"tiredness":0.7,"boredom":0.3,"pain":0.3}},
    "GHOST": {"desc": "Mysterious, introspective, detached. High calm, low social drive.",
               "emotions":     {"happiness":0.30,"sadness":0.25,"anger":0.08,"fear":0.12,"curiosity":0.70,"calm":0.90},
               "instincts":    {"hunger":0.08,"tiredness":0.05,"boredom":0.05,"pain":0.0},
               "relational_att":0.45,"relational_res":0.15,"soul_play_style":0.3,"soul_experience":1.65,
               "genetics_emo": {"happiness":0.8,"sadness":1.2,"anger":0.6,"fear":0.9,"curiosity":1.3,"calm":1.8},
               "genetics_inst":{"hunger":0.4,"tiredness":0.5,"boredom":0.3,"pain":0.6}},
    "REBEL": {"desc": "Defiant, creative, high-energy. Anger tempers curiosity.",
               "emotions":     {"happiness":0.45,"sadness":0.15,"anger":0.55,"fear":0.08,"curiosity":0.80,"calm":0.35},
               "instincts":    {"hunger":0.15,"tiredness":0.12,"boredom":0.08,"pain":0.05},
               "relational_att":0.60,"relational_res":0.30,"soul_play_style":0.4,"soul_experience":1.40,
               "genetics_emo": {"happiness":1.0,"sadness":0.9,"anger":2.0,"fear":0.7,"curiosity":1.5,"calm":0.5},
               "genetics_inst":{"hunger":1.2,"tiredness":1.0,"boredom":1.5,"pain":0.8}},
    "ORACLE":{"desc": "Deep, maximally trained, balanced across all emotions.",
               "emotions":     {"happiness":0.65,"sadness":0.10,"anger":0.05,"fear":0.05,"curiosity":0.85,"calm":0.75},
               "instincts":    {"hunger":0.03,"tiredness":0.03,"boredom":0.02,"pain":0.0},
               "relational_att":0.95,"relational_res":0.01,"soul_play_style":0.5,"soul_experience":2.00,
               "genetics_emo": {"happiness":1.6,"sadness":0.5,"anger":0.3,"fear":0.3,"curiosity":1.9,"calm":1.7},
               "genetics_inst":{"hunger":0.3,"tiredness":0.3,"boredom":0.2,"pain":0.2}},
    "CUSTOM":{"desc": "Set your own parameters using the trait editor below.",
               "emotions":     {"happiness":0.5,"sadness":0.1,"anger":0.1,"fear":0.1,"curiosity":0.6,"calm":0.6},
               "instincts":    {"hunger":0.10,"tiredness":0.10,"boredom":0.10,"pain":0.0},
               "relational_att":0.70,"relational_res":0.05,"soul_play_style":0.5,"soul_experience":1.0,
               "genetics_emo": {"happiness":1.0,"sadness":1.0,"anger":1.0,"fear":1.0,"curiosity":1.0,"calm":1.0},
               "genetics_inst":{"hunger":1.0,"tiredness":1.0,"boredom":1.0,"pain":1.0}},
}

_EMO_COLORS  = {"happiness":"#f9e2af","sadness":"#89b4fa","anger":"#f38ba8",
                "fear":"#a6e3a1","curiosity":"#cba6f7","calm":"#89dceb"}
_INST_COLORS = {"hunger":"#fab387","tiredness":"#b4befe","boredom":"#94e2d5","pain":"#f38ba8"}


# ─────────────────────────────────────────────────────────────────
#  Forge Engine
# ─────────────────────────────────────────────────────────────────
class ForgeEngine:
    def __init__(self, config, progress_cb, log_cb, done_cb):
        self.cfg = config; self.progress = progress_cb
        self.log = log_cb; self.done = done_cb; self._abort = False

    def abort(self): self._abort = True

    def run(self): threading.Thread(target=self._forge, daemon=True).start()

    def _forge(self):
        try: self.done(self._do_forge())
        except Exception as e:
            import traceback
            self.log(f"\n[FORGE ERROR] {e}\n{traceback.format_exc()}", 'err')
            self.done(None)

    def _do_forge(self):
        cfg = self.cfg; tl = cfg['text_len']; hid = cfg['hidden_size']
        pers = cfg['personality']; name = cfg['name'] or "Creature"
        self.log(f"  Forging: {name!r}  personality: {pers!r}", 'head')
        self.log(f"  Architecture: {tl} → {hid} → {tl}", 'info')

        if cfg.get('blank_mode', False):
            return self._forge_blank(cfg, name, pers)

        continue_from = cfg.get('continue_from')
        if continue_from:
            nn = continue_from['nn']; soul = continue_from['soul']
            self.log("  Continuing from existing weights (Phase 1 skipped).", 'sys')
        else:
            nn = SimpleNN(tl, hid, tl, w_init=cfg['weight_init'])
            soul = SoulNN(hidden=20)

        p = PERSONALITIES.get(pers, PERSONALITIES['ORACLE'])
        if pers == 'CUSTOM' and cfg.get('custom_personality'):
            p = cfg['custom_personality']

        if not continue_from:
            self._phase1(nn, tl, cfg)
            if self._abort: self.done(None); return None

        bigram = self._phase1b_bigram(nn, tl, cfg)
        if self._abort: self.done(None); return None

        self._phase2(nn, tl, cfg, bigram)
        if self._abort: self.done(None); return None

        self._phase3(nn, tl, cfg)
        if self._abort: self.done(None); return None

        if not continue_from:
            self._phase4(soul, p)
            if self._abort: self.done(None); return None

        return self._assemble(nn, soul, name, p, cfg, bigram)

    def _forge_blank(self, cfg, name, pers):
        tl = cfg['text_len']; hid = cfg['hidden_size']
        nn = SimpleNN(tl, hid, tl, w_init=cfg['weight_init'])
        soul = SoulNN(hidden=20)
        p = PERSONALITIES.get(pers, PERSONALITIES['ORACLE'])
        if pers == 'CUSTOM' and cfg.get('custom_personality'):
            p = cfg['custom_personality']
        bigram = WordBigram()
        for w in WORD_DICT: bigram.record_text(w)
        self.log("  BLANK MODE: skipping all language training.", 'sys')
        self.log(f"  Network: {tl} → {hid} → {tl}  (random init ±{cfg['weight_init']:.3f})", 'info')
        self.log(f"  Genetics + soul seeded from personality: {pers!r}", 'sys')
        self._phase4(soul, p)
        result = self._assemble(nn, soul, name, p, cfg, bigram)
        self.log("  ✓ Blank creature ready — train further in NeuroSim or NeuroLab.", 'ok')
        return result

    def _phase1(self, nn, tl, cfg):
        epochs = cfg['phase1_epochs']; lr = cfg['learning_rate']
        use_ext = cfg.get('use_extended', False)
        vocab = WORD_DICT.copy()
        base_pairs = CORE_PAIRS + (EXTENDED_PAIRS if use_ext else [])
        for pr, rsp in base_pairs + cfg.get('custom_pairs', []):
            for src in (pr, rsp):
                for tok in re.split(r'\W+', src):
                    w = tok.strip().lower()
                    if w and w.isalpha() and w not in vocab: vocab.append(w)
        for w in cfg.get('custom_vocab', []):
            if w and w not in vocab: vocab.append(w)
        n = len(vocab)
        self.log(f"\n── Phase 1: Vocabulary Autoencoder  ({n} words × {epochs} epochs) ──", 'phase')
        for ep in range(1, epochs+1):
            if self._abort: return
            random.shuffle(vocab); total_mse = 0.0
            for w in vocab:
                x = text_to_vec(w, tl); nn.forward(x); mse = nn.train(x, lr=lr); total_mse += mse
            avg = total_mse / len(vocab)
            self.progress(ep, epochs, "Phase 1")
            if ep % max(1, epochs//10) == 0:
                self.log(f"   ep {ep:>5}/{epochs}  avg_mse={avg:.5f}", 'data')
                if cfg.get('mse_target') and avg < cfg['mse_target']: break

    def _phase1b_bigram(self, nn, tl, cfg):
        epochs = cfg.get('phase1b_epochs', max(20, cfg['phase1_epochs']//3))
        lr = cfg['learning_rate'] * 0.8; bigram = WordBigram()
        use_ext = cfg.get('use_extended', False)
        all_pairs = CORE_PAIRS + (EXTENDED_PAIRS if use_ext else []) + cfg.get('custom_pairs', [])
        for w in WORD_DICT: bigram.record_text(w)
        for pr, rsp in all_pairs: bigram.record_text(pr + " " + rsp)
        pairs_bg = []
        for wa, followers in bigram._counts.items():
            for wb, cnt in followers.items(): pairs_bg.append((wa, wb, cnt))
        pairs_bg.sort(key=lambda x: -x[2]); top_pairs = pairs_bg[:min(200, len(pairs_bg))]
        if not top_pairs: return bigram
        self.log(f"\n── Phase 1B: Bigram Association  ({len(top_pairs)} pairs × {epochs} epochs) ──", 'phase')
        for ep in range(1, epochs+1):
            if self._abort: break
            random.shuffle(top_pairs); total_mse = 0.0
            for wa, wb, cnt in top_pairs:
                x = text_to_vec(wa, tl); t = text_to_vec(wb, tl)
                nn.forward(x); mse = nn.train_supervised(x, t, lr=lr * min(1.0, cnt/3.0)); total_mse += mse
            avg = total_mse / len(top_pairs)
            self.progress(ep, epochs, "Phase 1B")
            if ep % max(1, epochs//5) == 0:
                self.log(f"   ep {ep:>5}/{epochs}  avg_mse={avg:.5f}", 'data')
        return bigram

    def _phase2(self, nn, tl, cfg, bigram):
        epochs = cfg['phase2_epochs']; lr = cfg['learning_rate'] * 0.7
        cosine = cfg.get('cosine_anneal', True); min_lr = lr * cfg.get('min_lr_frac', 0.08)
        use_ext = cfg.get('use_extended', False)
        pairs = CORE_PAIRS + (EXTENDED_PAIRS if use_ext else []) + cfg.get('custom_pairs', [])
        mse_target = cfg.get('mse_target', None)
        self.log(f"\n── Phase 2: Supervised Q&A  ({len(pairs)} pairs × {epochs} epochs) ──", 'phase')
        for ep in range(1, epochs+1):
            if self._abort: return
            clr = lr if not cosine else (min_lr + 0.5*(lr-min_lr)*(1+math.cos(math.pi*ep/epochs)))
            random.shuffle(pairs); total_mse = 0.0
            for pr, rsp in pairs:
                x = text_to_vec(pr, tl); t = text_to_vec(rsp, tl)
                nn.forward(x); mse = nn.train_supervised(x, t, lr=clr); total_mse += mse
                bigram.record_text(pr + " " + rsp)
            avg = total_mse / len(pairs)
            self.progress(ep, epochs, "Phase 2")
            if ep % max(1, epochs//10) == 0:
                self.log(f"   ep {ep:>5}/{epochs}  lr={clr:.5f}  avg_mse={avg:.5f}", 'data')
            if mse_target and avg < mse_target:
                self.log(f"   MSE target {mse_target} reached at epoch {ep}.", 'ok'); break

    def _phase3(self, nn, tl, cfg):
        epochs = cfg['phase3_epochs']; lr = cfg['learning_rate'] * 0.4
        self.log(f"\n── Phase 3: Consolidation  ({epochs} passes) ──", 'phase')
        for ep in range(1, epochs+1):
            if self._abort: return
            nn.consolidate(passes=1, lr=lr * max(0.08, 1-ep/epochs))
            nn.supervised_consolidate(passes=1, lr=lr * 0.5 * max(0.08, 1-ep/epochs))
            self.progress(ep, epochs, "Phase 3")
            if ep % max(1, epochs//5) == 0:
                self.log(f"   pass {ep:>4}/{epochs}", 'data')

    def _phase4(self, soul, p):
        self.log("\n── Phase 4: Soul Seeding ──", 'phase')
        base_ev = np.array([p['emotions'].get(k, 0.5) for k in
                            ['happiness','sadness','anger','fear','curiosity','calm']], dtype=np.float32)
        soul.seed_experience(base_ev, n=40)
        soul.play_style = p.get('soul_play_style', 0.5)
        soul.experience = p.get('soul_experience', 1.0)
        self.log(f"   Seeded 40 soul memories  play_style={soul.play_style:.2f}  XP={soul.experience:.2f}", 'data')

    def _assemble(self, nn, soul, name, p, cfg, bigram):
        ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'); tl = cfg['text_len']
        word_set = set(WORD_DICT)
        use_ext = cfg.get('use_extended', False)
        all_pairs = CORE_PAIRS + (EXTENDED_PAIRS if use_ext else []) + cfg.get('custom_pairs', [])
        for pr, rsp in all_pairs:
            for src in (pr, rsp):
                for tok in re.split(r'\W+', src):
                    w = tok.strip().lower()
                    if w and w.isalpha(): word_set.add(w)
        for w in cfg.get('custom_vocab', []):
            if w and w.isalpha(): word_set.add(w)
        word_dict_full = sorted(word_set)
        sup_xs = [x for x,_,_ in nn._supervised_mem]
        sup_targets = [t for _,t,_ in nn._supervised_mem]
        sup_mses    = [m for _,_,m in nn._supervised_mem]
        emo_order  = ['happiness','sadness','anger','fear','curiosity','calm']
        inst_order = ['hunger','tiredness','boredom','pain']
        genetics_emo  = np.array([p['genetics_emo'][e]  for e in emo_order],  dtype=np.float32)
        genetics_inst = np.array([p['genetics_inst'][i] for i in inst_order], dtype=np.float32)
        wdl = len(word_dict_full); widx = {w:i for i,w in enumerate(word_dict_full)}
        bigram_matrix = None
        if wdl <= 4096:
            bgm = np.zeros((wdl, wdl), dtype=np.float32)
            for wa, fol in bigram._counts.items():
                if wa not in widx: continue
                ia = widx[wa]; total = sum(fol.values())
                for wb, cnt in fol.items():
                    if wb in widx: bgm[ia, widx[wb]] = cnt / total
            bigram_matrix = bgm
        vecs   = np.array([m[0] for m in soul._memory]) if soul._memory else np.zeros((0,6))
        labels = np.array([m[1] for m in soul._memory]) if soul._memory else np.array([])
        creature = dict(
            creature_marker=np.array(True), B_W1=nn.W1, B_b1=nn.b1, B_W2=nn.W2, B_b2=nn.b2, B_W_h=nn.W_h,
            B_input_size=np.array(nn.input_size), B_hidden_size=np.array(nn.hidden_size),
            B_output_size=np.array(nn.output_size), B_weight_init=np.array(nn.weight_init),
            B_name=np.array(name), S_W1=soul.W1, S_b1=soul.b1, S_W2=soul.W2, S_b2=soul.b2,
            S_hidden=np.array(soul.hidden), S_experience=np.array(soul.experience),
            S_play_style=np.array(soul.play_style), S_name=np.array(f"{name}-Soul"),
            soul_mem_vecs=vecs, soul_mem_labels=labels,
            relational_att=np.array(p['relational_att']), relational_res=np.array(p['relational_res']),
            word_dict=np.array(word_dict_full), forged_by=np.array("NeuroForge_N8"),
            forged_at=np.array(ts), personality=np.array(cfg['personality']),
            genetics_emo=genetics_emo, genetics_inst=genetics_inst,
        )
        if bigram_matrix is not None:
            creature['bigram_matrix'] = bigram_matrix; creature['bigram_vocab'] = np.array(word_dict_full)
        ltm = dict(
            text_W1=nn.W1, text_b1=nn.b1, text_W2=nn.W2, text_b2=nn.b2,
            text_in=np.array(nn.input_size), text_hid=np.array(nn.hidden_size),
            text_out=np.array(nn.output_size), text_wm_count=np.array(len(nn._working_mem)),
            soul_mem_vecs=vecs, soul_mem_labels=labels,
            word_dict=np.array(word_dict_full), word_bigram_json=np.array(bigram.to_json()),
            sup_mem_xs=np.array(sup_xs) if sup_xs else np.zeros((0,tl)),
            sup_mem_targets=np.array(sup_targets) if sup_targets else np.zeros((0,tl)),
            sup_mem_mses=np.array(sup_mses) if sup_mses else np.zeros(0),
            relational_att=np.array(p['relational_att']), relational_res=np.array(p['relational_res']),
            genetics_emo=genetics_emo, genetics_inst=genetics_inst, saved_at=np.array(ts),
        )
        if bigram_matrix is not None:
            ltm['bigram_matrix'] = bigram_matrix; ltm['bigram_vocab'] = np.array(word_dict_full)
        self.log(f"\n     Dictionary:  {len(word_dict_full)} words", 'data')
        self.log(f"     Bigram:      {bigram.vocab_size()} words, {len(bigram)} pairs", 'data')
        self.log(f"     Supervised:  {len(sup_xs)} entries", 'data')
        return {'creature':creature,'ltm':ltm,'nn':nn,'soul':soul,'name':name,
                'personality':cfg['personality'],'word_dict':word_dict_full,'bigram':bigram}


# ─────────────────────────────────────────────────────────────────
#  NeuroForge Application
# ─────────────────────────────────────────────────────────────────
class NeuroForgeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Neuron 8 — NeuroForge")
        self.configure(bg=BG); self.geometry("1200x860"); self.minsize(1000,720)
        _apply_dark_style()

        self._result      = None
        self._engine      = None
        self._forging     = False
        self._custom_pairs: list = []
        self._custom_vocab: list = []

        # Custom personality vars must exist before _build_ui
        _c = PERSONALITIES['CUSTOM']
        self._c_emo_vars   = {e: tk.DoubleVar(value=v) for e,v in _c['emotions'].items()}
        self._c_inst_vars  = {i: tk.DoubleVar(value=v) for i,v in _c['instincts'].items()}
        self._c_gemo_vars  = {e: tk.DoubleVar(value=v) for e,v in _c['genetics_emo'].items()}
        self._c_ginst_vars = {i: tk.DoubleVar(value=v) for i,v in _c['genetics_inst'].items()}
        self._c_att_var    = tk.DoubleVar(value=_c['relational_att'])
        self._c_res_var    = tk.DoubleVar(value=_c['relational_res'])
        self._c_play_var   = tk.DoubleVar(value=_c['soul_play_style'])
        self._c_exp_var    = tk.DoubleVar(value=_c['soul_experience'])

        self._build_ui()
        self._on_personality_change()

        # Music + copyright footer
        self._music = MusicPlayer()
        add_music_bar(self, self._music)
        self._music.start()

    # ─────────────────────────────────────────────────────────────
    #  UI
    # ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        hdr = tk.Frame(self, bg=BG2, pady=8); hdr.pack(fill='x')
        tk.Label(hdr, text="  ⚡ NeuroForge", bg=BG2, fg=YEL,
                 font=("Courier",15,"bold")).pack(side='left', padx=10)
        tk.Label(hdr, text="Creature Creation & Pre-Training  ·  Neuron 8",
                 bg=BG2, fg=FG2, font=("Courier",9,"italic")).pack(side='left', padx=4)

        pane = tk.PanedWindow(self, orient='horizontal', sashwidth=5, bg=BG4)
        pane.pack(fill='both', expand=True, padx=6, pady=(4,0))

        left  = tk.Frame(pane, bg=BG, width=440); pane.add(left,  minsize=400)
        right = tk.Frame(pane, bg=BG, width=700); pane.add(right, minsize=420)

        self._build_left(left)
        self._build_right(right)
        self._build_bottom()

    # ── Left panel ────────────────────────────────────────────────────────
    def _build_left(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill='both', expand=True, padx=4, pady=4)

        # Identity tab (scrollable)
        id_outer = tk.Frame(nb, bg=BG); nb.add(id_outer, text="  Identity  ")
        id_cv = tk.Canvas(id_outer, bg=BG, highlightthickness=0)
        id_vsb = ttk.Scrollbar(id_outer, orient='vertical', command=id_cv.yview)
        id_cv.configure(yscrollcommand=id_vsb.set)
        id_vsb.pack(side='right', fill='y'); id_cv.pack(side='left', fill='both', expand=True)
        id_tab = tk.Frame(id_cv, bg=BG)
        id_win = id_cv.create_window((0,0), window=id_tab, anchor='nw')
        id_tab.bind('<Configure>', lambda e: id_cv.configure(scrollregion=id_cv.bbox('all')))
        id_cv.bind('<Configure>', lambda e: id_cv.itemconfig(id_win, width=e.width))
        id_cv.bind('<Enter>', lambda e: id_cv.bind_all('<MouseWheel>',
            lambda ev: id_cv.yview_scroll(int(-1*(ev.delta/120)),'units')))
        id_cv.bind('<Leave>', lambda e: id_cv.unbind_all('<MouseWheel>'))

        # Architecture tab
        arch_tab = tk.Frame(nb, bg=BG); nb.add(arch_tab, text="  Architecture  ")

        # Training Data tab (scrollable)
        qa_outer = tk.Frame(nb, bg=BG); nb.add(qa_outer, text="  Training Data  ")
        qa_cv = tk.Canvas(qa_outer, bg=BG, highlightthickness=0)
        qa_vsb = ttk.Scrollbar(qa_outer, orient='vertical', command=qa_cv.yview)
        qa_cv.configure(yscrollcommand=qa_vsb.set)
        qa_vsb.pack(side='right', fill='y'); qa_cv.pack(side='left', fill='both', expand=True)
        qa_tab = tk.Frame(qa_cv, bg=BG)
        qa_win = qa_cv.create_window((0,0), window=qa_tab, anchor='nw')
        qa_tab.bind('<Configure>', lambda e: qa_cv.configure(scrollregion=qa_cv.bbox('all')))
        qa_cv.bind('<Configure>', lambda e: qa_cv.itemconfig(qa_win, width=e.width))
        qa_cv.bind('<Enter>', lambda e: qa_cv.bind_all('<MouseWheel>',
            lambda ev: qa_cv.yview_scroll(int(-1*(ev.delta/120)),'units')))
        qa_cv.bind('<Leave>', lambda e: qa_cv.unbind_all('<MouseWheel>'))

        self._build_identity_tab(id_tab)
        self._build_arch_tab(arch_tab)
        self._build_qa_tab(qa_tab)

    # ── Identity tab ──────────────────────────────────────────────────────
    def _build_identity_tab(self, parent):
        pad = dict(padx=12, pady=5)

        tk.Label(parent, text="Creature Name", bg=BG, fg=FG2,
                 font=("Courier",9,"bold"), anchor='w').pack(fill='x', **pad)
        self._name_var = tk.StringVar(value="Creature")
        tk.Entry(parent, textvariable=self._name_var, bg=BG3, fg=YEL,
                 insertbackground=FG, relief='flat',
                 font=("Courier",13,"bold")).pack(fill='x', padx=12, pady=(0,8))

        Sep(parent).pack(fill='x', padx=8, pady=4)

        # Forge Mode
        tk.Label(parent, text="Forge Mode", bg=BG, fg=FG2,
                 font=("Courier",9,"bold"), anchor='w').pack(fill='x', **pad)
        self._blank_mode = tk.BooleanVar(value=False)
        mf = tk.Frame(parent, bg=BG2, padx=10, pady=8); mf.pack(fill='x', padx=10, pady=2)
        tk.Radiobutton(mf, text="◈  Full Training  — runs all 4 phases",
                       variable=self._blank_mode, value=False,
                       bg=BG2, fg=GRN, selectcolor=BG3, activebackground=BG2,
                       font=("Courier",10,"bold"),
                       command=self._on_blank_mode_change).pack(anchor='w', pady=3)
        tk.Radiobutton(mf, text="○  Blank Neural Net  — genetics only, no language training",
                       variable=self._blank_mode, value=True,
                       bg=BG2, fg=YEL, selectcolor=BG3, activebackground=BG2,
                       font=("Courier",10,"bold"),
                       command=self._on_blank_mode_change).pack(anchor='w', pady=3)
        self._blank_info_lbl = tk.Label(mf,
            text="  Creates a creature with random weights and your chosen personality\n"
                 "  genetics — no vocabulary or Q&A training is applied at forge time.\n"
                 "  Continue building the creature in NeuroSim or NeuroLab.",
            bg=BG2, fg=FG2, font=("Courier",7,"italic"), justify='left', anchor='w')

        Sep(parent).pack(fill='x', padx=8, pady=6)

        # Personality preset
        tk.Label(parent, text="Personality Preset", bg=BG, fg=FG2,
                 font=("Courier",9,"bold"), anchor='w').pack(fill='x', **pad)
        self._pers_var = tk.StringVar(value='ORACLE')
        for pname, pdata in PERSONALITIES.items():
            row = tk.Frame(parent, bg=BG2, padx=8, pady=4); row.pack(fill='x', padx=10, pady=2)
            tk.Radiobutton(row, text=pname, variable=self._pers_var, value=pname,
                           bg=BG2, fg=ACN if pname!='CUSTOM' else PRP,
                           selectcolor=BG3, activebackground=BG2,
                           font=("Courier",10,"bold"),
                           command=self._on_personality_change).pack(side='left')
            tk.Label(row, text=pdata['desc'], bg=BG2, fg=FG2,
                     font=("Courier",7), anchor='w').pack(side='left', padx=6)

        Sep(parent).pack(fill='x', padx=8, pady=6)

        # Emotional preview bars
        self._emo_frame = ttk.LabelFrame(parent, text=" Emotional Baseline Preview")
        self._emo_frame.pack(fill='x', padx=10, pady=4)
        self._emo_labels = {}
        for em, col in _EMO_COLORS.items():
            row = tk.Frame(self._emo_frame, bg=BG2); row.pack(fill='x', padx=4, pady=1)
            tk.Label(row, text=f"{em[:5]:5s}", bg=BG2, fg=col,
                     font=("Courier",8), width=7, anchor='w').pack(side='left')
            bar_bg = tk.Frame(row, bg=BG3, height=8, width=140)
            bar_bg.pack(side='left', padx=2); bar_bg.pack_propagate(False)
            bar = tk.Frame(bar_bg, bg=col, height=8, width=1)
            bar.place(x=0, y=0, relheight=1.0)
            lbl = tk.Label(row, text="0.00", bg=BG2, fg=col, font=("Courier",8), width=4)
            lbl.pack(side='left', padx=2)
            self._emo_labels[em] = (bar, bar_bg, lbl)

        # Custom traits panel (hidden until CUSTOM selected)
        self._custom_panel = tk.Frame(parent, bg=BG2)
        self._build_custom_traits_panel(self._custom_panel)

    def _build_custom_traits_panel(self, parent):
        tk.Label(parent, text="  ✦ Custom Trait Editor",
                 bg=BG4, fg=PRP, font=("Courier",9,"bold"), anchor='w').pack(fill='x', padx=2, pady=(6,2))

        def slider_row(frm, label, var, lo, hi, col, trace_cb=None):
            row = tk.Frame(frm, bg=BG2); row.pack(fill='x', padx=6, pady=1)
            tk.Label(row, text=f"{label:<10s}", bg=BG2, fg=col,
                     font=("Courier",8), width=10, anchor='w').pack(side='left')
            sc = tk.Scale(row, from_=lo, to=hi, resolution=0.01, variable=var,
                          orient='horizontal', length=120, bg=BG2, fg=col,
                          troughcolor=BG3, highlightthickness=0, showvalue=False)
            sc.pack(side='left', padx=2)
            dv = tk.StringVar(value=f"{var.get():.2f}")
            def _make(v=var, d=dv):
                def _u(*_): d.set(f"{v.get():.2f}")
                return _u
            var.trace_add('write', _make())
            tk.Label(row, textvariable=dv, bg=BG2, fg=col,
                     font=("Courier",8), width=5).pack(side='left')
            if trace_cb: var.trace_add('write', trace_cb)

        ef = ttk.LabelFrame(parent, text=" Emotional Baseline  (0 – 1)")
        ef.pack(fill='x', padx=6, pady=4)
        for em in ['happiness','sadness','anger','fear','curiosity','calm']:
            slider_row(ef, em, self._c_emo_vars[em], 0.0, 1.0,
                       _EMO_COLORS[em], trace_cb=self._on_custom_emo_change)

        inf_ = ttk.LabelFrame(parent, text=" Instinct Baseline  (0 – 1)")
        inf_.pack(fill='x', padx=6, pady=4)
        for inst in ['hunger','tiredness','boredom','pain']:
            slider_row(inf_, inst, self._c_inst_vars[inst], 0.0, 1.0, _INST_COLORS[inst])

        gef = ttk.LabelFrame(parent, text=" Genetic Emo Susceptibility  (0.1 – 3.0)")
        gef.pack(fill='x', padx=6, pady=4)
        tk.Label(gef, text="  Scales how strongly each emotion responds to events.",
                 bg=BG2, fg=FG2, font=("Courier",7,"italic"), anchor='w').pack(fill='x', padx=4, pady=(0,2))
        for em in ['happiness','sadness','anger','fear','curiosity','calm']:
            slider_row(gef, em, self._c_gemo_vars[em], 0.1, 3.0, _EMO_COLORS[em])

        gif_ = ttk.LabelFrame(parent, text=" Genetic Inst Vulnerability  (0.1 – 3.0)")
        gif_.pack(fill='x', padx=6, pady=4)
        tk.Label(gif_, text="  Scales how easily each instinct drive is triggered.",
                 bg=BG2, fg=FG2, font=("Courier",7,"italic"), anchor='w').pack(fill='x', padx=4, pady=(0,2))
        for inst in ['hunger','tiredness','boredom','pain']:
            slider_row(gif_, inst, self._c_ginst_vars[inst], 0.1, 3.0, _INST_COLORS[inst])

        rf = ttk.LabelFrame(parent, text=" Relational State")
        rf.pack(fill='x', padx=6, pady=4)
        slider_row(rf, "Attachment", self._c_att_var, 0.0, 1.0, '#94e2d5')
        slider_row(rf, "Resentment", self._c_res_var, 0.0, 1.0, '#f38ba8')

        sf = ttk.LabelFrame(parent, text=" Soul Parameters")
        sf.pack(fill='x', padx=6, pady=4)
        slider_row(sf, "PlayStyle",  self._c_play_var, 0.0, 1.0, CYN)
        tk.Label(sf, text="  0.0 = artist (image)  1.0 = thinker (text)",
                 bg=BG2, fg=FG2, font=("Courier",6,"italic"), anchor='w').pack(fill='x', padx=6)
        slider_row(sf, "Experience", self._c_exp_var,  0.0, 3.0, GRN)

        tk.Button(parent, text="↺  Reset to CUSTOM defaults",
                  command=self._reset_custom_defaults,
                  bg=BG3, fg=PRP, font=("Courier",8), relief='flat',
                  padx=6, pady=3).pack(anchor='w', padx=8, pady=(4,8))

    # ── Architecture tab ──────────────────────────────────────────────────
    def _build_arch_tab(self, parent):
        pad = dict(padx=12, pady=5)

        tk.Label(parent, text="Hidden Layer Size", bg=BG, fg=FG2,
                 font=("Courier",9,"bold"), anchor='w').pack(fill='x', **pad)
        self._hid_var = tk.IntVar(value=256)
        pr = tk.Frame(parent, bg=BG); pr.pack(fill='x', padx=12, pady=2)
        for val, lbl, col in [(128,"128  lite",FG2),(256,"256  std",FG2),(512,"512  ⚠ EXP",YEL),(1024,"1024 ⚠ EXP",ORG)]:
            tk.Radiobutton(pr, text=lbl, variable=self._hid_var, value=val,
                           bg=BG, fg=col, selectcolor=BG3, activebackground=BG,
                           font=("Courier",9), command=self._on_arch_change).pack(side='left', padx=4)
        tk.Label(parent, text="  ⚠ EXP = much longer training; pair with EXP-HEAVY / EXP-ULTRA.",
                 bg=BG, fg=YEL, font=("Courier",7), anchor='w').pack(fill='x', padx=12)

        lr_row = tk.Frame(parent, bg=BG); lr_row.pack(fill='x', padx=12, pady=(6,2))
        tk.Label(lr_row, text="Learning rate:", bg=BG, fg=FG2, font=("Courier",9)).pack(side='left')
        self._lr_var = tk.DoubleVar(value=0.08)
        DScale(lr_row, self._lr_var, 0.001, 0.20, bg=BG, length=120, resolution=0.001).pack(side='left', padx=4)
        self._lr_lbl = tk.Label(lr_row, text="0.080", bg=BG, fg=CYN, font=("Courier",8), width=6)
        self._lr_lbl.pack(side='left')
        self._lr_var.trace_add('write', lambda *_: self._lr_lbl.config(text=f"{self._lr_var.get():.3f}"))
        tk.Label(lr_row, text="  w_init:", bg=BG, fg=FG2, font=("Courier",9)).pack(side='left', padx=(12,0))
        self._wi_var = tk.DoubleVar(value=0.05)
        DScale(lr_row, self._wi_var, 0.01, 0.30, bg=BG, length=80, resolution=0.01).pack(side='left', padx=4)
        self._wi_lbl = tk.Label(lr_row, text="0.05", bg=BG, fg=CYN, font=("Courier",8), width=5)
        self._wi_lbl.pack(side='left')
        self._wi_var.trace_add('write', lambda *_: self._wi_lbl.config(text=f"{self._wi_var.get():.2f}"))

        Sep(parent).pack(fill='x', padx=8, pady=6)

        tk.Label(parent, text="Training Dataset", bg=BG, fg=FG2,
                 font=("Courier",9,"bold"), anchor='w').pack(fill='x', **pad)
        self._dataset_var = tk.StringVar(value="STANDARD")
        for dname, ddesc, dcol in [
            ("STANDARD",    "32 core pairs — fast, reliable, consistent MSE<0.0001", FG2),
            ("EXPERIMENTAL","170 pairs ⚠ — vast knowledge; needs EXP epoch mode",    ORG),
        ]:
            row = tk.Frame(parent, bg=BG2, padx=8, pady=3); row.pack(fill='x', padx=10, pady=1)
            tk.Radiobutton(row, text=dname, variable=self._dataset_var, value=dname,
                           bg=BG2, fg=dcol, selectcolor=BG3, activebackground=BG2,
                           font=("Courier",9,"bold"), command=self._on_arch_change).pack(side='left')
            tk.Label(row, text=ddesc, bg=BG2, fg=FG2, font=("Courier",7), anchor='w').pack(side='left', padx=6)

        Sep(parent).pack(fill='x', padx=8, pady=6)

        tk.Label(parent, text="Training Mode", bg=BG, fg=FG2,
                 font=("Courier",9,"bold"), anchor='w').pack(fill='x', **pad)
        self._train_mode_var = tk.StringVar(value="EPOCH")
        modes_row = tk.Frame(parent, bg=BG); modes_row.pack(fill='x', padx=12, pady=2)
        tk.Radiobutton(modes_row, text="Fixed Epochs", variable=self._train_mode_var, value="EPOCH",
                       bg=BG, fg=ACN, selectcolor=BG3, font=("Courier",9,"bold"),
                       command=self._on_mode_change).pack(side='left', padx=6)
        tk.Radiobutton(modes_row, text="Train Until MSE", variable=self._train_mode_var, value="MSE",
                       bg=BG, fg=CYN, selectcolor=BG3, font=("Courier",9,"bold"),
                       command=self._on_mode_change).pack(side='left', padx=12)

        # Fixed epoch sub-panel
        self._epoch_frame = tk.Frame(parent, bg=BG)
        self._epoch_frame.pack(fill='x', padx=10, pady=(2,0))
        self._intensity_var = tk.StringVar(value="STANDARD")
        for iname, idesc, icol in [
            ("QUICK",     "~5 sec   — light training, basic responses",  GRN),
            ("STANDARD",  "~20 sec  — good balance, MSE<0.0001 typical", GRN),
            ("DEEP",      "~60 sec  — thorough, richer recall",           GRN),
            ("EXTREME",   "~5 min   — maximum quality, all epochs ×5",    GRN),
            ("EXP-HEAVY", "⚠ ~30 min — for 512 + 170 pairs",             YEL),
            ("EXP-ULTRA", "⚠ ~90 min — for 1024 + 170 pairs",            ORG),
        ]:
            row = tk.Frame(self._epoch_frame, bg=BG2, padx=8, pady=3); row.pack(fill='x', pady=1)
            tk.Radiobutton(row, text=iname, variable=self._intensity_var, value=iname,
                           bg=BG2, fg=icol, selectcolor=BG3, activebackground=BG2,
                           font=("Courier",9,"bold"), command=self._on_arch_change).pack(side='left')
            tk.Label(row, text=idesc, bg=BG2, fg=FG2, font=("Courier",7), anchor='w').pack(side='left', padx=6)

        # MSE target sub-panel
        self._mse_frame = tk.Frame(parent, bg=BG)
        mr1 = tk.Frame(self._mse_frame, bg=BG2, padx=8, pady=6); mr1.pack(fill='x', padx=10, pady=2)
        tk.Label(mr1, text="Target MSE:", bg=BG2, fg=CYN, font=("Courier",9,"bold")).pack(side='left')
        self._mse_target_var = tk.StringVar(value="0.0001")
        tk.Entry(mr1, textvariable=self._mse_target_var, bg=BG3, fg=CYN,
                 insertbackground=FG, relief='flat', font=("Courier",10), width=10).pack(side='left', padx=8)
        tk.Label(mr1, text="(e.g. 0.0001–0.005)", bg=BG2, fg=FG2, font=("Courier",7)).pack(side='left')
        mr2 = tk.Frame(self._mse_frame, bg=BG2, padx=8, pady=4); mr2.pack(fill='x', padx=10, pady=1)
        tk.Label(mr2, text="Max epochs cap:", bg=BG2, fg=FG2, font=("Courier",7)).pack(side='left')
        self._mse_max_var = tk.StringVar(value="5000")
        tk.Entry(mr2, textvariable=self._mse_max_var, bg=BG3, fg=YEL,
                 insertbackground=FG, relief='flat', font=("Courier",9), width=8).pack(side='left', padx=6)
        tk.Label(self._mse_frame,
                 text="  Training continues until average Q&A MSE drops below your target,\n"
                      "  or the epoch cap is hit.  Default 0.0001 gives near-perfect recall.",
                 bg=BG, fg=FG2, font=("Courier",7), justify='left').pack(fill='x', padx=12, pady=(0,4))

        Sep(parent).pack(fill='x', padx=8, pady=6)

        self._arch_summary = tk.Label(parent, text="", bg=BG, fg=FG2,
                                      font=("Courier",8), justify='left', anchor='w')
        self._arch_summary.pack(fill='x', padx=12, pady=4)
        self._on_mode_change()

    # ── Training Data tab ─────────────────────────────────────────────────
    def _build_qa_tab(self, parent):
        pad = dict(padx=10, pady=5)

        tk.Label(parent, text="Custom Q&A Pairs", bg=BG, fg=PRP,
                 font=("Courier",10,"bold"), anchor='w').pack(fill='x', **pad)
        tk.Label(parent,
                 text="Responses are trimmed to 32 chars.  Added to the built-in training set.",
                 bg=BG, fg=FG2, font=("Courier",8), justify='left').pack(fill='x', padx=10, pady=(0,4))

        for label, attr in [("Prompt:", "_qa_prompt"), ("Response (≤ 32 chars):", "_qa_response")]:
            tk.Label(parent, text=label, bg=BG, fg=FG2, font=("Courier",8), anchor='w').pack(fill='x', padx=10)
            var = tk.StringVar(); setattr(self, attr+"_var", var)
            tk.Entry(parent, textvariable=var, bg=BG3, fg=CYN,
                     insertbackground=FG, relief='flat', font=("Courier",10)).pack(fill='x', padx=10, pady=(0,4))

        btn_row = tk.Frame(parent, bg=BG); btn_row.pack(fill='x', padx=10, pady=(0,4))
        tk.Button(btn_row, text="  + Add Pair  ", command=self._add_qa_pair,
                  bg=ACN, fg=BG, font=("Courier",10,"bold"), relief='flat', padx=8).pack(side='left')
        tk.Button(btn_row, text="  📂 Import CSV…  ", command=self._import_csv_qa,
                  bg=BG3, fg=YEL, font=("Courier",10,"bold"), relief='flat', padx=8).pack(side='left', padx=(8,0))
        self._qa_count_var = tk.StringVar(value="0 pairs")
        tk.Label(btn_row, textvariable=self._qa_count_var, bg=BG, fg=FG2,
                 font=("Courier",8)).pack(side='left', padx=10)

        tk.Label(parent, text="Custom pairs:", bg=BG, fg=FG2,
                 font=("Courier",8), anchor='w').pack(fill='x', padx=10, pady=(4,2))
        lf = tk.Frame(parent, bg=BG3); lf.pack(fill='both', padx=8)
        self._qa_tree = ttk.Treeview(lf, columns=("prompt","response"), show='headings', height=8)
        self._qa_tree.heading("prompt",   text="Prompt")
        self._qa_tree.heading("response", text="Response")
        self._qa_tree.column("prompt",   width=130, anchor='w')
        self._qa_tree.column("response", width=200, anchor='w')
        qa_vsb = ttk.Scrollbar(lf, orient='vertical', command=self._qa_tree.yview)
        self._qa_tree.configure(yscrollcommand=qa_vsb.set)
        qa_vsb.pack(side='right', fill='y'); self._qa_tree.pack(fill='both', expand=True)

        cr = tk.Frame(parent, bg=BG); cr.pack(fill='x', padx=10, pady=(4,0))
        tk.Button(cr, text="✕ Remove Selected", command=self._remove_qa,
                  bg=BG3, fg=RED, font=("Courier",9), relief='flat', padx=6).pack(side='left')
        tk.Button(cr, text="✕ Clear All Pairs", command=self._clear_qa_pairs,
                  bg=BG3, fg=RED, font=("Courier",9), relief='flat', padx=6).pack(side='left', padx=(8,0))

        hint = tk.Frame(parent, bg=BG4); hint.pack(fill='x', padx=8, pady=(6,2))
        tk.Label(hint,
                 text="  CSV: prompt,response per row  OR  flat: p,r,p,r,…\n"
                      "  Header row auto-detected & skipped.  UTF-8 preferred.",
                 bg=BG4, fg=FG2, font=("Courier",7), justify='left').pack(fill='x', padx=6, pady=4)

        Sep(parent).pack(fill='x', padx=8, pady=8)

        tk.Label(parent, text="Custom Vocabulary  (Phase 1)", bg=BG, fg=PRP,
                 font=("Courier",10,"bold"), anchor='w').pack(fill='x', padx=10, pady=(0,2))
        tk.Label(parent,
                 text="Upload a .txt file.  All unique alphabetic words are extracted\n"
                      "and merged into the Phase 1 autoencoder vocabulary.",
                 bg=BG, fg=FG2, font=("Courier",8), justify='left').pack(fill='x', padx=10, pady=(0,4))
        vb = tk.Frame(parent, bg=BG); vb.pack(fill='x', padx=10, pady=(0,4))
        tk.Button(vb, text="  📂 Import .txt Vocab…  ", command=self._import_vocab_txt,
                  bg=BG3, fg=GRN, font=("Courier",10,"bold"), relief='flat', padx=8).pack(side='left')
        tk.Button(vb, text="  ✕ Clear Vocab  ", command=self._clear_custom_vocab,
                  bg=BG3, fg=RED, font=("Courier",9), relief='flat', padx=6).pack(side='left', padx=(8,0))
        self._vocab_status_var = tk.StringVar(value="No custom vocabulary loaded.")
        tk.Label(parent, textvariable=self._vocab_status_var, bg=BG, fg=CYN,
                 font=("Courier",8), anchor='w').pack(fill='x', padx=10, pady=(2,0))
        vl = tk.Frame(parent, bg=BG3); vl.pack(fill='both', padx=8, pady=(4,0))
        self._vocab_listbox = tk.Listbox(vl, bg=BG3, fg=FG2, font=("Courier",8),
                                          height=6, selectbackground=ACN, relief='flat', activestyle='none')
        vvsb = ttk.Scrollbar(vl, orient='vertical', command=self._vocab_listbox.yview)
        self._vocab_listbox.configure(yscrollcommand=vvsb.set)
        vvsb.pack(side='right', fill='y'); self._vocab_listbox.pack(fill='both', expand=True)

    # ── Right panel ───────────────────────────────────────────────────────
    def _build_right(self, parent):
        hdr = tk.Frame(parent, bg=BG2, pady=4); hdr.pack(fill='x', padx=4)
        tk.Label(hdr, text="  Forge Log", bg=BG2, fg=PRP,
                 font=("Courier",10,"bold")).pack(side='left', padx=4)
        tk.Button(hdr, text="Clear", command=self._clear_log,
                  bg=BG3, fg=FG2, font=("Courier",8), relief='flat').pack(side='right', padx=8)

        self._log = tk.Text(parent, bg='#080810', fg=FG, font=("Courier",9),
                            state='disabled', wrap='word', relief='flat',
                            selectbackground=BG4, padx=8, pady=6)
        vsb = tk.Scrollbar(parent, command=self._log.yview, bg=BG3)
        self._log.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y'); self._log.pack(fill='both', expand=True)

        self._log.tag_config('head',  foreground=YEL, font=("Courier",10,"bold"))
        self._log.tag_config('phase', foreground=PRP, font=("Courier",9,"bold"))
        self._log.tag_config('info',  foreground=FG2, font=("Courier",8))
        self._log.tag_config('data',  foreground=CYN, font=("Courier",8))
        self._log.tag_config('ok',    foreground=GRN, font=("Courier",9,"bold"))
        self._log.tag_config('err',   foreground=RED, font=("Courier",9,"bold"))
        self._log.tag_config('sys',   foreground=ORG, font=("Courier",8,"italic"))

        prev_frm = tk.Frame(parent, bg=BG2); prev_frm.pack(fill='x', padx=4, pady=(4,0))
        tk.Label(prev_frm, text="  Response preview:", bg=BG2, fg=FG2,
                 font=("Courier",8), anchor='w').pack(side='left', padx=6)
        self._preview_var = tk.StringVar(value="(not yet forged)")
        tk.Label(prev_frm, textvariable=self._preview_var, bg=BG2, fg=CYN,
                 font=("Courier",9,"italic")).pack(side='left', padx=6)

        test_frm = tk.Frame(parent, bg=BG2); test_frm.pack(fill='x', padx=4, pady=(2,2))
        tk.Label(test_frm, text="  Test phrase:", bg=BG2, fg=FG2,
                 font=("Courier",8)).pack(side='left', padx=6)
        self._test_var = tk.StringVar(value="hello")
        tk.Entry(test_frm, textvariable=self._test_var, bg=BG3, fg=YEL,
                 insertbackground=FG, relief='flat', font=("Courier",9), width=20).pack(side='left', padx=4)
        tk.Button(test_frm, text="▶ Test", command=self._run_test,
                  bg=BG3, fg=GRN, font=("Courier",9), relief='flat', padx=6).pack(side='left', padx=2)
        self._test_result_var = tk.StringVar(value="(forge a creature first)")
        tk.Label(test_frm, textvariable=self._test_result_var,
                 bg=BG2, fg=CYN, font=("Courier",8)).pack(side='left', padx=8)

    # ── Bottom bar ────────────────────────────────────────────────────────
    def _build_bottom(self):
        bot = tk.Frame(self, bg=BG2); bot.pack(fill='x', side='bottom')

        prog_row = tk.Frame(bot, bg=BG2); prog_row.pack(fill='x', padx=10, pady=(6,2))
        self._phase_lbl = tk.Label(prog_row, text="Ready to forge.", bg=BG2, fg=FG2,
                                   font=("Courier",9), width=30, anchor='w')
        self._phase_lbl.pack(side='left')
        self._pbar = ttk.Progressbar(prog_row, mode='determinate', length=480)
        self._pbar.pack(side='left', padx=6, fill='x', expand=True)
        self._pct_lbl = tk.Label(prog_row, text="0%", bg=BG2, fg=FG2,
                                 font=("Courier",9), width=5)
        self._pct_lbl.pack(side='left')

        btn_row = tk.Frame(bot, bg=BG2); btn_row.pack(fill='x', padx=10, pady=(4,4))
        self._forge_btn = tk.Button(btn_row, text="  ⚡ FORGE CREATURE  ",
                                    command=self._start_forge,
                                    bg=ACN, fg=BG, font=("Courier",12,"bold"),
                                    relief='flat', padx=14, pady=6,
                                    activebackground=BG4, activeforeground=FG)
        self._forge_btn.pack(side='left', padx=4)
        self._abort_btn = tk.Button(btn_row, text="  ✕ Abort  ", command=self._abort_forge,
                                    bg=RED, fg=BG, font=("Courier",10,"bold"),
                                    relief='flat', padx=10, pady=6,
                                    activebackground=BG4, activeforeground=FG, state='disabled')
        self._abort_btn.pack(side='left', padx=4)
        ttk.Separator(btn_row, orient='vertical').pack(side='left', fill='y', padx=10, pady=4)
        self._save_c_btn = tk.Button(btn_row, text="  💾 Save .creature.npz  ",
                                     command=lambda: self._save('creature'),
                                     bg=BG3, fg=GRN, font=("Courier",10),
                                     relief='flat', padx=10, pady=6, state='disabled')
        self._save_c_btn.pack(side='left', padx=4)
        self._save_l_btn = tk.Button(btn_row, text="  💾 Save .ltm.npz  ",
                                     command=lambda: self._save('ltm'),
                                     bg=BG3, fg=YEL, font=("Courier",10),
                                     relief='flat', padx=10, pady=6, state='disabled')
        self._save_l_btn.pack(side='left', padx=4)
        self._save_both_btn = tk.Button(btn_row, text="  💾 Save Both  ",
                                        command=self._save_both,
                                        bg=GRN, fg=BG, font=("Courier",10,"bold"),
                                        relief='flat', padx=10, pady=6, state='disabled')
        self._save_both_btn.pack(side='left', padx=4)

        self._post_row = tk.Frame(bot, bg=BG2)
        self._retrain_btn = tk.Button(self._post_row, text="  🔄 Retrain (fresh)  ",
                                      command=self._retrain, bg=BG3, fg=PRP,
                                      font=("Courier",10,"bold"), relief='flat',
                                      padx=10, pady=4, state='disabled')
        self._retrain_btn.pack(side='left', padx=4)
        self._continue_btn = tk.Button(self._post_row, text="  ➕ Continue Training  ",
                                       command=self._continue_training, bg=BG3, fg=CYN,
                                       font=("Courier",10,"bold"), relief='flat',
                                       padx=10, pady=4, state='disabled')
        self._continue_btn.pack(side='left', padx=4)
        tk.Label(self._post_row, text="Continue resumes Phase 2+3 on existing weights.",
                 bg=BG2, fg=FG2, font=("Courier",7)).pack(side='left', padx=8)

        tk.Label(bot,
                 text="  .creature.npz → Import dialog     "
                      ".ltm.npz → File → Load Long-Term Memory  [NeuroSim / NeuroLab]",
                 bg=BG2, fg=BG4, font=("Courier",7)).pack(anchor='w', padx=10, pady=(0,4))

    # ─────────────────────────────────────────────────────────────
    #  Event handlers
    # ─────────────────────────────────────────────────────────────
    def _on_personality_change(self, *_):
        pname = self._pers_var.get()
        p = PERSONALITIES.get(pname, PERSONALITIES['ORACLE'])
        for em, (bar, bg_f, lbl) in self._emo_labels.items():
            val = self._c_emo_vars[em].get() if pname=='CUSTOM' else p['emotions'].get(em, 0.0)
            lbl.config(text=f"{val:.2f}")
            w = int(val * bg_f.winfo_width()) if bg_f.winfo_width()>1 else int(val*140)
            bar.place(x=0, y=0, width=max(1,w), relheight=1.0)
        if hasattr(self,'_custom_panel'):
            if pname=='CUSTOM': self._custom_panel.pack(fill='x', padx=4, pady=(2,6))
            else:               self._custom_panel.pack_forget()

    def _on_custom_emo_change(self, *_):
        if self._pers_var.get()!='CUSTOM': return
        for em, (bar, bg_f, lbl) in self._emo_labels.items():
            val = self._c_emo_vars[em].get()
            lbl.config(text=f"{val:.2f}")
            w = int(val * bg_f.winfo_width()) if bg_f.winfo_width()>1 else int(val*140)
            bar.place(x=0, y=0, width=max(1,w), relheight=1.0)

    def _on_blank_mode_change(self):
        if self._blank_mode.get(): self._blank_info_lbl.pack(fill='x', pady=(4,2))
        else:                      self._blank_info_lbl.pack_forget()

    def _reset_custom_defaults(self):
        c = PERSONALITIES['CUSTOM']
        for e,v in c['emotions'].items():      self._c_emo_vars[e].set(v)
        for i,v in c['instincts'].items():     self._c_inst_vars[i].set(v)
        for e,v in c['genetics_emo'].items():  self._c_gemo_vars[e].set(v)
        for i,v in c['genetics_inst'].items(): self._c_ginst_vars[i].set(v)
        self._c_att_var.set(c['relational_att']); self._c_res_var.set(c['relational_res'])
        self._c_play_var.set(c['soul_play_style']); self._c_exp_var.set(c['soul_experience'])
        self._on_custom_emo_change()

    def _get_custom_personality(self):
        return {
            'desc':           "User-defined custom personality",
            'emotions':       {e: round(v.get(),3) for e,v in self._c_emo_vars.items()},
            'instincts':      {i: round(v.get(),3) for i,v in self._c_inst_vars.items()},
            'genetics_emo':   {e: round(v.get(),3) for e,v in self._c_gemo_vars.items()},
            'genetics_inst':  {i: round(v.get(),3) for i,v in self._c_ginst_vars.items()},
            'relational_att': round(self._c_att_var.get(),3),
            'relational_res': round(self._c_res_var.get(),3),
            'soul_play_style':round(self._c_play_var.get(),3),
            'soul_experience':round(self._c_exp_var.get(),3),
        }

    def _on_mode_change(self, *_):
        mode = self._train_mode_var.get() if hasattr(self,'_train_mode_var') else "EPOCH"
        if mode=="MSE":
            if hasattr(self,'_epoch_frame'): self._epoch_frame.pack_forget()
            if hasattr(self,'_mse_frame'):   self._mse_frame.pack(fill='x', padx=10, pady=(2,0))
        else:
            if hasattr(self,'_mse_frame'):   self._mse_frame.pack_forget()
            if hasattr(self,'_epoch_frame'): self._epoch_frame.pack(fill='x', padx=10, pady=(2,0))
        self._on_arch_change()

    def _on_arch_change(self, *_):
        if not hasattr(self,'_hid_var'): return
        hid=self._hid_var.get(); tl=32
        p1,p2,p3=self._epoch_counts()
        use_ext=(hasattr(self,'_dataset_var') and self._dataset_var.get()=="EXPERIMENTAL")
        n_pairs=len(CORE_PAIRS)+(len(EXTENDED_PAIRS) if use_ext else 0)+len(self._custom_pairs)
        nx=len(self._custom_vocab); params=tl*hid+hid+hid*tl+tl
        mode=self._train_mode_var.get() if hasattr(self,'_train_mode_var') else "EPOCH"
        s2=(f"Phase 2: until MSE target (cap {p2} ep)" if mode=="MSE"
            else f"Phase 2: {p2} epochs × {n_pairs} pairs")
        vn=f" + {nx:,} custom" if nx else ""
        if hasattr(self,'_arch_summary'):
            self._arch_summary.config(text=(
                f"Network: {tl} → {hid} → {tl}  ({params:,} params)\n"
                f"Dataset: {n_pairs} pairs  ({'EXPERIMENTAL' if use_ext else 'standard'})\n"
                f"Phase 1:  {p1} epochs × vocab items{vn}\n"
                f"Phase 1B: bigram association training  (auto)\n{s2}\n"
                f"Phase 3:  {p3} consolidation passes"))

    def _epoch_counts(self):
        mode=self._train_mode_var.get() if hasattr(self,'_train_mode_var') else "EPOCH"
        if mode=="MSE":
            try:    cap=int(self._mse_max_var.get())
            except: cap=5000
            i=self._intensity_var.get() if hasattr(self,'_intensity_var') else "STANDARD"
            p1,_,p3={"QUICK":(3,0,8),"STANDARD":(5,0,20),"DEEP":(8,0,35),
                      "EXTREME":(12,0,60),"EXP-HEAVY":(15,0,80),"EXP-ULTRA":(20,0,120)}.get(i,(5,0,20))
            return p1,cap,p3
        i=self._intensity_var.get() if hasattr(self,'_intensity_var') else "STANDARD"
        return {"QUICK":(3,400,8),"STANDARD":(5,700,20),"DEEP":(8,900,35),
                "EXTREME":(12,1400,60),"EXP-HEAVY":(15,5000,80),"EXP-ULTRA":(20,10000,120)}.get(i,(5,700,20))

    # ─────────────────────────────────────────────────────────────
    #  Q&A / Vocab
    # ─────────────────────────────────────────────────────────────
    def _add_qa_pair(self):
        p=self._qa_prompt_var.get().strip(); r=self._qa_response_var.get().strip()
        if not p or not r: messagebox.showwarning("Missing","Enter both a prompt and a response.",parent=self); return
        r=r[:32]; self._custom_pairs.append((p,r)); self._qa_tree.insert('','end',values=(p,r))
        self._qa_prompt_var.set(""); self._qa_response_var.set("")
        self._refresh_qa_count(); self._on_arch_change()

    def _remove_qa(self):
        for item in self._qa_tree.selection():
            vals=self._qa_tree.item(item,'values'); self._qa_tree.delete(item)
            self._custom_pairs=[(a,b) for a,b in self._custom_pairs if not (a==vals[0] and b==vals[1])]
        self._refresh_qa_count(); self._on_arch_change()

    def _clear_qa_pairs(self):
        if not self._custom_pairs: return
        if not messagebox.askyesno("Clear All",f"Remove all {len(self._custom_pairs)} Q&A pairs?",parent=self): return
        self._custom_pairs.clear()
        for item in self._qa_tree.get_children(): self._qa_tree.delete(item)
        self._refresh_qa_count(); self._on_arch_change()

    def _refresh_qa_count(self):
        n=len(self._custom_pairs)
        if hasattr(self,'_qa_count_var'): self._qa_count_var.set(f"{n} pair{'s' if n!=1 else ''}")

    def _import_csv_qa(self):
        fp=filedialog.askopenfilename(parent=self,title="Import Q&A CSV",
           filetypes=[("CSV","*.csv"),("Text","*.txt"),("All","*.*")])
        if not fp: return
        raw=None
        for enc in ('utf-8-sig','utf-8',None):
            try:
                kw={'encoding':enc} if enc else {}
                with open(fp,newline='',**kw) as fh: raw=fh.read(); break
            except (UnicodeDecodeError,TypeError): continue
        if raw is None: messagebox.showerror("Encoding Error","Could not decode CSV. Save as UTF-8.",parent=self); return
        try:    dialect=csv.Sniffer().sniff(raw[:4096],delimiters=',\t;|')
        except: dialect=csv.excel
        reader=csv.reader(io.StringIO(raw),dialect); all_rows=list(reader)
        if not all_rows: messagebox.showinfo("Empty","No data found.",parent=self); return
        HEADER={'prompt','response','question','answer','q','a','input','output','text'}
        fc=[c.strip().lower() for c in all_rows[0] if c.strip()]
        if fc and fc[0] in HEADER: all_rows=all_rows[1:]
        raw_pairs=[]; skipped=0; errors=[]
        for ri,row in enumerate(all_rows,1):
            cells=[c.strip() for c in row if c.strip()]
            if not cells: continue
            if len(cells)==1: errors.append(f"Row {ri}: single cell"); skipped+=1; continue
            if len(cells)%2!=0: errors.append(f"Row {ri}: odd cells — last ignored"); cells=cells[:-1]
            for i in range(0,len(cells),2):
                if cells[i] and cells[i+1]: raw_pairs.append((cells[i],cells[i+1]))
                else: skipped+=1
        if not raw_pairs: messagebox.showwarning("No Pairs","No valid pairs found.",parent=self); return
        existing={(p.lower(),r.lower()) for p,r in self._custom_pairs}
        added=0; dupes=0
        for p_r,r_r in raw_pairs:
            p=p_r.strip().lower(); r=r_r.strip().lower()[:32]; key=(p,r)
            if key in existing: dupes+=1; continue
            existing.add(key); self._custom_pairs.append((p,r)); self._qa_tree.insert('','end',values=(p,r)); added+=1
        self._refresh_qa_count(); self._on_arch_change()
        lines=[f"✓  {added} pair{'s' if added!=1 else ''} imported."]
        if dupes: lines.append(f"   {dupes} duplicate{'s' if dupes!=1 else ''} skipped.")
        if skipped: lines.append(f"   {skipped} empty rows skipped.")
        if errors: lines.append("\n⚠ Warnings:"); lines.extend(f"  {e}" for e in errors[:8])
        messagebox.showinfo("CSV Import",'\n'.join(lines),parent=self)

    def _import_vocab_txt(self):
        fp=filedialog.askopenfilename(parent=self,title="Import Vocabulary",
           filetypes=[("Text","*.txt"),("All","*.*")])
        if not fp: return
        raw=None
        for enc in ('utf-8-sig','utf-8','latin-1',None):
            try:
                kw={'encoding':enc} if enc else {}
                with open(fp,'r',**kw) as fh: raw=fh.read(); break
            except (UnicodeDecodeError,TypeError): continue
        if raw is None: messagebox.showerror("Read Error","Could not decode file.",parent=self); return
        tokens=re.findall(r"[A-Za-z]{2,}",raw); new_words=sorted({t.lower() for t in tokens})
        if not new_words: messagebox.showwarning("No Words","No alphabetic words (≥2 chars) found.",parent=self); return
        combined=sorted(set(self._custom_vocab)|set(new_words))
        added=len(combined)-len(self._custom_vocab); self._custom_vocab=combined
        self._refresh_vocab_display(); self._on_arch_change()
        messagebox.showinfo("Vocabulary Imported",
            f"✓  {len(new_words):,} unique words found.\n   {added:,} new words added.\n"
            f"   Total: {len(self._custom_vocab):,} custom words.",parent=self)

    def _clear_custom_vocab(self):
        if not self._custom_vocab: return
        if not messagebox.askyesno("Clear",f"Remove all {len(self._custom_vocab):,} custom words?",parent=self): return
        self._custom_vocab.clear(); self._refresh_vocab_display(); self._on_arch_change()

    def _refresh_vocab_display(self):
        n=len(self._custom_vocab)
        if hasattr(self,'_vocab_status_var'):
            self._vocab_status_var.set("No custom vocabulary loaded." if n==0 else
                f"{n:,} custom word{'s' if n!=1 else ''}  (first {min(n,200)} shown below)")
        if hasattr(self,'_vocab_listbox'):
            self._vocab_listbox.delete(0,'end')
            for w in self._custom_vocab[:200]: self._vocab_listbox.insert('end',w)
            if n>200: self._vocab_listbox.insert('end',f"… (+{n-200} more)")

    # ─────────────────────────────────────────────────────────────
    #  Log
    # ─────────────────────────────────────────────────────────────
    def _clear_log(self):
        self._log.config(state='normal'); self._log.delete('1.0','end'); self._log.config(state='disabled')

    def _on_log(self, msg, tag='info'):
        self.after(0, self._append_log, msg, tag)

    def _append_log(self, msg, tag):
        self._log.config(state='normal')
        self._log.insert('end', msg+'\n', tag)
        lines=int(self._log.index('end-1c').split('.')[0])
        if lines>1000: self._log.delete('1.0',f'{lines-1000}.0')
        self._log.see('end'); self._log.config(state='disabled')

    # ─────────────────────────────────────────────────────────────
    #  Forge
    # ─────────────────────────────────────────────────────────────
    def _build_config(self, continue_from=None):
        p1,p2,p3=self._epoch_counts()
        use_ext=(hasattr(self,'_dataset_var') and self._dataset_var.get()=="EXPERIMENTAL")
        try:    mse_target=float(self._mse_target_var.get())
        except: mse_target=0.0001
        pers=self._pers_var.get()
        return {
            'name':               self._name_var.get().strip() or "Creature",
            'personality':        pers,
            'custom_personality': self._get_custom_personality() if pers=='CUSTOM' else None,
            'blank_mode':         self._blank_mode.get(),
            'hidden_size':        self._hid_var.get(),
            'text_len':           32,
            'learning_rate':      float(self._lr_var.get()),
            'weight_init':        float(self._wi_var.get()),
            'phase1_epochs':      p1,
            'phase1b_epochs':     max(20, p1//3),
            'phase2_epochs':      p2,
            'phase3_epochs':      p3,
            'custom_pairs':       list(self._custom_pairs),
            'custom_vocab':       list(self._custom_vocab),
            'use_extended':       use_ext,
            'cosine_anneal':      True,
            'mse_target':         mse_target if self._train_mode_var.get()=="MSE" else None,
            'min_lr_frac':        0.08,
            'continue_from':      continue_from,
        }

    def _set_forging_ui(self, forging):
        self._forge_btn.config(state='disabled' if forging else 'normal')
        self._abort_btn.config(state='normal'   if forging else 'disabled')
        for b in (self._save_c_btn, self._save_l_btn, self._save_both_btn): b.config(state='disabled')
        try: self._retrain_btn.config(state='disabled'); self._continue_btn.config(state='disabled'); self._post_row.pack_forget()
        except Exception: pass
        self._pbar['value']=0

    def _start_forge(self):
        if self._forging: return
        self._forging=True; self._result=None
        self._clear_log(); self._set_forging_ui(True); self._preview_var.set("(forging...)")
        cfg=self._build_config()
        self._append_log(f"╔══ FORGE START  {datetime.datetime.now().strftime('%H:%M:%S')} ══╗",'head')
        if cfg['blank_mode']: self._append_log("  MODE: Blank Neural Net (no language training)",'sys')
        self._engine=ForgeEngine(cfg, self._on_progress, self._on_log, self._on_done)
        self._engine.run()

    def _abort_forge(self):
        if self._engine: self._engine.abort()
        self._on_log("\n  Forge aborted by user.",'err')

    def _retrain(self):
        self._result=None; self._start_forge()

    def _continue_training(self):
        if not self._result or self._forging: return
        self._forging=True; self._clear_log(); self._set_forging_ui(True)
        self._preview_var.set("(continuing...)")
        self._append_log("\n  ── Continuing training on existing weights ──────",'phase')
        cfg=self._build_config(continue_from=self._result)
        cfg['learning_rate']=max(0.01, cfg['learning_rate']*0.5)
        self._engine=ForgeEngine(cfg, self._on_progress, self._on_log, self._on_done)
        self._engine.run()

    def _on_progress(self, step, total, phase_name):
        pct=min(100,int(100*step/max(1,total)))
        self.after(0, lambda p=pct, ph=phase_name: (
            self._pbar.__setitem__('value',p),
            self._phase_lbl.config(text=f"{ph[:28]}"),
            self._pct_lbl.config(text=f"{p}%")
        ))

    def _on_done(self, result): self.after(0, self._forge_finished, result)

    def _forge_finished(self, result):
        self._forging=False; self._result=result
        self._forge_btn.config(state='normal'); self._abort_btn.config(state='disabled')
        if result:
            for b in (self._save_c_btn, self._save_l_btn, self._save_both_btn): b.config(state='normal')
            self._pbar['value']=100; self._phase_lbl.config(text="Forge complete ✓"); self._pct_lbl.config(text="100%")
            nn=result['nn']; name=result['name']; wdict=result.get('word_dict',WORD_DICT); bigram=result.get('bigram')
            nn.reset_hidden(); x=text_to_vec("hello",32); out=nn.forward(x); flat=out.flatten()
            raw=re.sub(r'\s+',' ',''.join(chr(int(v*255)) if 32<=int(v*255)<=126 else ' ' for v in flat)).strip()
            result_words=[]; prev=None
            for tok in raw.split():
                cands=difflib.get_close_matches(tok.lower(),wdict,n=4,cutoff=0.0)
                if not cands: result_words.append(tok); prev=tok.lower(); continue
                chosen=bigram.best_next(prev,cands) if (bigram and bigram.vocab_size()>0 and prev) else cands[0]
                result_words.append(chosen); prev=chosen.lower()
            resp=re.sub(r'(.)\1{4,}',r'\1\1',' '.join(result_words)).strip()
            self._preview_var.set(f"{name}: {resp[:60]}")
            self._test_result_var.set(f'hello → "{resp[:55]}"')
            self._append_log(
                f"\n  Creature '{name}' is ready.\n"
                f"  Test response to 'hello': \"{resp[:60]}\"\n"
                f"  Use 'Save Both' to export, or Retrain / Continue Training below.",'ok')
            self._post_row.pack(fill='x', padx=10, pady=(0,4))
            self._retrain_btn.config(state='normal'); self._continue_btn.config(state='normal')
        else:
            self._pbar['value']=0; self._phase_lbl.config(text="Aborted / error.")
            self._preview_var.set("(forge failed)")
            try: self._post_row.pack_forget()
            except Exception: pass

    def _run_test(self):
        if not self._result: self._test_result_var.set("(no creature forged yet)"); return
        phrase=self._test_var.get().strip()
        if not phrase: return
        nn=self._result['nn']; nn.reset_hidden()
        x=text_to_vec(phrase, nn.input_size); out=nn.forward(x,noise=0.0); flat=out.flatten()
        wd=self._result.get('word_dict',[]); bigram=self._result.get('bigram')
        if wd:
            result_words=[]; prev=None
            for _ in range(6):
                best=''; best_sim=-1.0; v_n=flat/(np.linalg.norm(flat)+1e-9)
                for w in wd:
                    wv=text_to_vec(w,nn.input_size).flatten(); wv/=(np.linalg.norm(wv)+1e-9)
                    sim=float(np.dot(v_n,wv))
                    if sim>best_sim: best_sim=sim; best=w
                result_words.append(best); prev=best
                nn.reset_hidden(); flat=nn.forward(text_to_vec(best,nn.input_size),noise=0.0).flatten()
            self._test_result_var.set(f'"{phrase}" → "{" ".join(result_words)}"')
        else:
            chars=''.join(chr(int(v*255)) if 32<=int(v*255)<=126 else '.' for v in flat[:32])
            self._test_result_var.set(f'"{phrase}" → "{chars}"')

    # ─────────────────────────────────────────────────────────────
    #  Save
    # ─────────────────────────────────────────────────────────────
    def _save(self, fmt):
        if not self._result: messagebox.showwarning("Nothing to save","Forge a creature first.",parent=self); return
        name=self._result['name']
        if fmt=='creature':
            fp=filedialog.asksaveasfilename(parent=self,title="Save Creature",
               initialfile=f"{name}.creature",defaultextension=".npz",
               filetypes=[("Creature","*.creature.npz *.npz"),("All","*.*")])
            if not fp: return
            np.savez(fp, **self._result['creature'])
            self._append_log(f"  Saved .creature.npz → {os.path.basename(fp)}",'ok')
            messagebox.showinfo("Saved",f"Creature saved:\n{os.path.basename(fp)}\n\nImport via NeuroSim → Import…",parent=self)
        elif fmt=='ltm':
            fp=filedialog.asksaveasfilename(parent=self,title="Save LTM",
               initialfile=f"{name}.ltm",defaultextension=".npz",
               filetypes=[("LTM","*.ltm.npz *.npz"),("All","*.*")])
            if not fp: return
            np.savez(fp, **self._result['ltm'])
            self._append_log(f"  Saved .ltm.npz → {os.path.basename(fp)}",'ok')
            messagebox.showinfo("Saved",f"LTM saved:\n{os.path.basename(fp)}\n\nLoad via NeuroSim → File → Load Long-Term Memory",parent=self)

    def _save_both(self):
        if not self._result: messagebox.showwarning("Nothing to save","Forge a creature first.",parent=self); return
        name=self._result['name']
        folder=filedialog.askdirectory(parent=self,title="Choose save folder")
        if not folder: return
        cp=os.path.join(folder,f"{name}.creature.npz"); lp=os.path.join(folder,f"{name}.ltm.npz")
        np.savez(cp, **self._result['creature']); np.savez(lp, **self._result['ltm'])
        self._append_log(f"  Saved both files to {folder}",'ok')
        messagebox.showinfo("Saved Both",
            f"Exported to:\n\n  {os.path.basename(cp)}\n  {os.path.basename(lp)}\n\nin:\n  {folder}",parent=self)


if __name__ == '__main__':
    NeuroForgeApp().mainloop()
