"""
Winter AI -- Orchestrator.
Runs every layer in order, assembles reasoning trace + final answer.
"""
from __future__ import annotations
import re, time, shutil
from pathlib import Path
from typing import Optional

from . import proc
from .mercury.determinism import classify as mercury_classify
from .retrieval import KnowledgeIndex
from .output_validator import validate_output
from .logic.engine import build_winter_kb, Solver, TNorm, certainty_label

BASE = Path(__file__).resolve().parent
SCHEME_SCRIPT = BASE / "scheme" / "decision.scm"
LISP_SCRIPT   = BASE / "lisp"   / "reasoner.lisp"
PROLOG_SCRIPT = BASE / "prolog" / "knowledge.pl"
OCAML_BIN     = BASE / "ocaml"  / "validator"
CPP_BIN       = BASE / "cpp"    / "engine"

GUILE  = shutil.which("guile")  or "guile"
SBCL   = shutil.which("sbcl")   or "sbcl"
SWIPL  = shutil.which("swipl")  or "swipl"

RW_HINTS = {"muraho","murakoze","amakuru","witwa","murabeho","byiza","cyane","neza","yego","oya"}
FR_CHARS = set("eeeaauuuiioocoa")
FR_HINTS = {"bonjour","merci","comment","vous","je","suis","salut","oui","non"}

def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z\u00C0-\u024F]+", text.lower())

def detect_lang(text: str) -> str:
    tokens = set(tokenize(text))
    if tokens & RW_HINTS: return "rw"
    if len(tokens & FR_HINTS) >= 1: return "fr"
    return "en"

CANNED = {
    "greeting": {
        "en": "Hello! I'm Winter AI -- a polyglot reasoning assistant. How can I help you?",
        "fr": "Bonjour! Je suis Winter AI, un assistant de raisonnement polyglotte. Comment puis-je vous aider?",
        "rw": "Muraho! Ndi Winter AI, umufasha ukoresha ururimi rwinshi. Nigute nakugira?",
    },
    "thanks": {
        "en": "You're welcome! Always happy to help.",
        "fr": "De rien! Toujours heureux d'aider.",
        "rw": "Ntacyo! Nishimiye gufasha.",
    },
    "farewell": {
        "en": "Goodbye! Talk soon.",
        "fr": "Au revoir! A bientot.",
        "rw": "Murabeho! Tuzaganira vuba.",
    },
    "identity": {
        "en": "I'm Winter AI -- a polyglot reasoning assistant combining Python, Scheme, Prolog, Common Lisp, OCaml, C++, and Mercury-style logic. Created by INEZA Aime Bruno, Rwanda.",
        "fr": "Je suis Winter AI -- un assistant combinant Python, Scheme, Prolog, Common Lisp, OCaml, C++ et une logique de style Mercury. Cree par INEZA Aime Bruno, Rwanda.",
        "rw": "Ndi Winter AI -- umufasha ukoresha Python, Scheme, Prolog, Common Lisp, OCaml, C++ hamwe n'ingingo zishingiye kuri Mercury. Yaremwe na INEZA Aime Bruno, Rwanda.",
    },
    "wellbeing": {
        "en": "All 7 engines are running perfectly! How can I help you today?",
        "fr": "Les 7 moteurs fonctionnent parfaitement! Comment puis-je vous aider aujourd'hui?",
        "rw": "Imashini zose 7 zirakora neza! Nakugira nte uyu munsi?",
    },
    "help": {
        "en": "I can chat in English, French and Kinyarwanda, answer questions from my knowledge base, reason step by step, and translate words. What do you need?",
        "fr": "Je peux discuter en anglais, francais et kinyarwanda, repondre aux questions et traduire des mots. De quoi avez-vous besoin?",
        "rw": "Nshobora kuganira mu Cyongereza, Igifaransa no Gikinyarwanda, gusubiza ibibazo, no guhindura amagambo. Ukeneye iki?",
    },
}

class WinterOrchestrator:
    def __init__(self, knowledge: KnowledgeIndex):
        self.knowledge = knowledge
        self.kb = build_winter_kb()
        self.solver = Solver(self.kb, tnorm=TNorm.MIN)

    # Layer 1: Python
    def python_layer(self, prompt: str, lang: str) -> dict:
        t0 = time.perf_counter()
        detected = detect_lang(prompt)
        effective = lang if lang in ("fr","rw") else detected
        tokens = tokenize(prompt)
        return {"engine":"Python","status":"ok","duration_ms":round((time.perf_counter()-t0)*1000,2),
                "output":f"tokens={tokens[:10]} detected={detected} effective={effective}",
                "tokens":tokens,"effective_lang":effective}

    # Layer 2: Logic Engine (unified pytholog+PESAD+acarlson)
    def logic_layer(self, tokens: list[str], lang: str) -> dict:
        t0 = time.perf_counter()
        intent = "lookup"; sentiment = "neutral"; cf = 0.0; proof_str = ""; best_cf = 0.0
        for tok in tokens[:8]:
            r = self.solver.query_best(f"intent({tok}, {lang}, X)")
            if r and r["cf"] > best_cf:
                intent = r["bindings"].get("X", "lookup")
                best_cf = r["cf"]
                cf = r["cf"]
                proof_str = r["proof"].explain()
        for tok in tokens[:8]:
            r = self.solver.query_best(f"sentiment({tok}, X)")
            if r:
                sentiment = r["bindings"].get("X", "neutral")
                break
        return {"engine":"Logic Engine (pytholog+PESAD+acarlson)","status":"ok",
                "duration_ms":round((time.perf_counter()-t0)*1000,2),
                "output":proof_str or f"intent={intent} sentiment={sentiment}",
                "intent":intent,"sentiment":sentiment,"cf":round(cf,4),
                "certainty":certainty_label(cf) if cf > 0 else "none"}

    # Layer 3: Scheme
    def scheme_layer(self, tokens: list[str], lang: str) -> dict:
        t0 = time.perf_counter()
        res = proc.run([GUILE,"--no-auto-compile",str(SCHEME_SCRIPT),lang,",".join(tokens)])
        dur = round((time.perf_counter()-t0)*1000,2)
        lines = res["lines"]
        return {"engine":"Scheme (GNU Guile)","status":"ok" if res["ok"] else "error",
                "duration_ms":dur,"output":lines.get("TRACE",res["error"] or ""),
                "intent":lines.get("INTENT","lookup").lower(),
                "sentiment":lines.get("SENTIMENT","neutral").lower(),
                "confidence":lines.get("CONFIDENCE","0")}

    # Layer 4: Prolog
    def prolog_layer(self, tokens: list[str], lang: str) -> dict:
        t0 = time.perf_counter()
        res = proc.run([SWIPL,str(PROLOG_SCRIPT),lang,*tokens[:20]])
        dur = round((time.perf_counter()-t0)*1000,2)
        lines = res["lines"]
        return {"engine":"Prolog (SWI-Prolog)","status":"ok" if res["ok"] else "error",
                "duration_ms":dur,"output":lines.get("TRACE",res["error"] or ""),
                "matched_intents":lines.get("MATCHED_INTENTS","[]"),
                "back_translation":lines.get("BACK_TRANSLATION","none")}

    # Layer 5: Common Lisp
    def lisp_layer(self, tokens: list[str], corpus_path) -> dict:
        t0 = time.perf_counter()
        cmd = [SBCL,"--script",str(LISP_SCRIPT),",".join(tokens)]
        if corpus_path: cmd.append(str(corpus_path))
        res = proc.run(cmd, timeout=8.0)
        dur = round((time.perf_counter()-t0)*1000,2)
        lines = res["lines"]
        return {"engine":"Common Lisp (SBCL)","status":"ok" if res["ok"] else "error",
                "duration_ms":dur,"output":lines.get("TRACE",res["error"] or ""),
                "match_line":lines.get("MATCH-LINE",""),"match_score":lines.get("MATCH-SCORE","0")}

    # Layer 6: OCaml
    def ocaml_layer(self, prompt: str) -> dict:
        t0 = time.perf_counter()
        res = proc.run([str(OCAML_BIN), prompt])
        dur = round((time.perf_counter()-t0)*1000,2)
        lines = res["lines"]
        return {"engine":"OCaml (native, compiled)","status":lines.get("STATUS","error"),
                "duration_ms":dur,"output":lines.get("TRACE",res["error"] or ""),
                "normalised":lines.get("NORMALISED",prompt.strip())}

    # Layer 7: C++
    def cpp_layer(self, query: str, candidates: list[str]) -> dict:
        t0 = time.perf_counter()
        res = proc.run([str(CPP_BIN), query, *candidates[:15]])
        dur = round((time.perf_counter()-t0)*1000,2)
        lines = res["lines"]
        return {"engine":"C++ (native, compiled)","status":"ok" if res["ok"] else "error",
                "duration_ms":dur,"output":lines.get("TRACE",res["error"] or ""),
                "best_match":lines.get("BEST_MATCH","none"),
                "edit_distance":lines.get("EDIT_DISTANCE","-1"),
                "ue_payload":lines.get("UE_REMOTE_CONTROL_PAYLOAD","")}

    # Mercury
    def mercury_layer(self, matches: list[str]) -> dict:
        t0 = time.perf_counter()
        r = mercury_classify(matches)
        return {"engine":r["engine"],"status":"ok",
                "duration_ms":round((time.perf_counter()-t0)*1000,2),
                "output":r["trace"],"determinism":r["determinism"]}

    # Full pipeline
    def run(self, prompt: str, lang: str, chat_id: str) -> dict:
        steps = []
        py = self.python_layer(prompt, lang); steps.append(py)
        effective_lang = py["effective_lang"]; tokens = py["tokens"]

        logic = self.logic_layer(tokens, effective_lang); steps.append(logic)
        scheme = self.scheme_layer(tokens, effective_lang); steps.append(scheme)
        prolog = self.prolog_layer(tokens, effective_lang); steps.append(prolog)

        hits = self.knowledge.search(prompt, effective_lang, top_k=5)
        top_lines = [h["line"] for h in hits]

        lisp = self.lisp_layer(tokens, self.knowledge.corpus_path()); steps.append(lisp)
        ocaml = self.ocaml_layer(prompt); steps.append(ocaml)
        cpp = self.cpp_layer(prompt, top_lines or [""]); steps.append(cpp)
        mercury = self.mercury_layer([h for h in top_lines if h]); steps.append(mercury)

        answer, source = self._compose(prompt, effective_lang, logic, scheme, hits, lisp, cpp)
        validation = validate_output(answer, effective_lang)

        return {"chat_id":chat_id,"lang":effective_lang,"reasoning_steps":steps,
                "final_answer":answer,"knowledge_source":source,"output_valid":validation["valid"]}

    def _compose(self, prompt, lang, logic, scheme, hits, lisp, cpp):
        # Priority 1: intent from logic engine (higher confidence) or scheme
        intent = logic.get("intent","lookup")
        if intent == "lookup":
            intent = scheme.get("intent","lookup")
        if intent != "lookup":
            canned = CANNED.get(intent,{}).get(lang) or CANNED.get(intent,{}).get("en")
            if canned: return canned, f"canned:{intent}"

        # Priority 2: TF-IDF retrieval
        if hits and hits[0]["score"] > 0.05:
            return hits[0]["line"], f"retrieval:{hits[0]['source']}"

        # Priority 3: Lisp exact match
        ms = lisp.get("match_score","0")
        ml = lisp.get("match_line","")
        if ml and ms not in ("0",""):
            return ml, "lisp:exact-match"

        # Priority 4: C++ fuzzy match
        bm = cpp.get("best_match","")
        if bm and bm != "none":
            return f'Closest known phrase: "{bm}".', "cpp:fuzzy-match"

        # Priority 5: Default with teach-folder hint
        defaults = {
            "en": f'I don\'t have a confident answer for "{prompt}" yet. Drop a .txt file into api/inf/teach/ and I will learn it.',
            "fr": f'Je n\'ai pas encore de reponse sure pour "{prompt}". Ajoutez des informations dans api/inf/teach/.',
            "rw": f'Simbizi neza igisubizo cya "{prompt}". Ongeraho amakuru muri api/inf/teach/.',
        }
        return defaults.get(lang, defaults["en"]), "default"
