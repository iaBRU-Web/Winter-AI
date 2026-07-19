"""
Winter AI -- Unified Logic Engine
Inspired by (fully rewritten as original code):
  pytholog (MIT) by MNoorFawi  -- unification + backtracking + memoization
  PESAD (MIT) by dmeoli        -- certainty factors + proof tree explanation
  acarlson99/expert-system (Apache-2.0) -- backward chaining + variable tracking
No API keys. The brain IS the knowledge base.
"""
from __future__ import annotations
import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generator


# ---------------------------------------------------------------------------
# 1. UNIFICATION (pytholog-inspired Robinson unification)
# ---------------------------------------------------------------------------
def is_var(s: Any) -> bool:
    return isinstance(s, str) and bool(s) and s[0].isupper()

def resolve(x: Any, env: dict) -> Any:
    seen: set = set()
    while isinstance(x, str) and is_var(x) and x in env:
        if x in seen: break
        seen.add(x); x = env[x]
    return x

def unify(x: Any, y: Any, env: dict) -> dict | None:
    x, y = resolve(x, env), resolve(y, env)
    if x == y: return env
    if is_var(x): return {**env, x: y}
    if is_var(y): return {**env, y: x}
    if isinstance(x, tuple) and isinstance(y, tuple) and len(x) == len(y):
        for xi, yi in zip(x, y):
            env = unify(xi, yi, env)
            if env is None: return None
        return env
    return None

def apply_env(term: Any, env: dict) -> Any:
    term = resolve(term, env)
    if isinstance(term, tuple): return tuple(apply_env(t, env) for t in term)
    return term


# ---------------------------------------------------------------------------
# 2. KNOWLEDGE BASE
# ---------------------------------------------------------------------------
@dataclass
class Clause:
    head: tuple
    body: list
    certainty: float = 1.0
    label: str = ""

class KnowledgeBase:
    def __init__(self, name: str = "winter"):
        self.name = name
        self._index: dict[str, list[Clause]] = defaultdict(list)

    def assert_fact(self, pred: str, *args, certainty: float = 1.0, label: str = "") -> None:
        self._index[pred].append(Clause((pred, *args), [], certainty, label))

    def assert_rule(self, pred: str, args: tuple, body: list, certainty: float = 1.0, label: str = "") -> None:
        self._index[pred].append(Clause((pred, *args), body, certainty, label))

    def load_text(self, text: str) -> int:
        count = 0
        for raw in text.splitlines():
            raw = raw.strip()
            if not raw or raw.startswith("#") or raw.startswith("%"): continue
            raw = raw.rstrip(".")
            cf = 1.0
            m = re.search(r"\s+cf\s+([\d.]+)\s*$", raw)
            if m:
                cf = min(1.0, max(0.0, float(m.group(1))))
                raw = raw[:m.start()]
            if ":-" in raw:
                hs, bs = raw.split(":-", 1)
                head = _pt(hs.strip())
                body = [_pt(g.strip()) for g in _sa(bs) if g.strip()]
                self.assert_rule(head[0], head[1:], body, cf)
            else:
                t = _pt(raw)
                self.assert_fact(t[0], *t[1:], certainty=cf)
            count += 1
        return count

    def load_file(self, path: str) -> int:
        try:
            return self.load_text(open(path, encoding="utf-8", errors="replace").read())
        except FileNotFoundError:
            return 0

    def lookup(self, pred: str) -> list[Clause]:
        return self._index.get(pred, [])

def _pt(s: str) -> tuple:
    s = s.strip()
    m = re.match(r'^([\w ]+)\((.+)\)$', s, re.DOTALL)
    if m:
        return (m.group(1).strip(), *[a.strip() for a in _sa(m.group(2))])
    return (s,)

def _sa(s: str) -> list[str]:
    args, depth, cur = [], 0, []
    for ch in s:
        if ch == "(": depth += 1; cur.append(ch)
        elif ch == ")": depth -= 1; cur.append(ch)
        elif ch == "," and depth == 0: args.append("".join(cur).strip()); cur = []
        else: cur.append(ch)
    if cur: args.append("".join(cur).strip())
    return args

def _ts(term: Any) -> str:
    if isinstance(term, tuple) and len(term) > 1:
        return "{}({})".format(term[0], ", ".join(str(x) for x in term[1:]))
    if isinstance(term, tuple): return str(term[0])
    return str(term)


# ---------------------------------------------------------------------------
# 3. CERTAINTY CALCULUS (PESAD-inspired)
# ---------------------------------------------------------------------------
class TNorm(str, Enum):
    MIN = "min"
    PRODUCT = "product"

def combine_cf(cfs: list[float], tnorm: TNorm = TNorm.MIN) -> float:
    if not cfs: return 1.0
    if tnorm == TNorm.MIN: return min(cfs)
    r = 1.0
    for c in cfs: r *= c
    return r

def certainty_label(cf: float) -> str:
    if cf >= 0.9: return "very high"
    if cf >= 0.7: return "high"
    if cf >= 0.5: return "moderate"
    if cf >= 0.3: return "low"
    return "very low"


# ---------------------------------------------------------------------------
# 4. PROOF TREE (PESAD-inspired)
# ---------------------------------------------------------------------------
@dataclass
class ProofNode:
    goal: str
    cf: float
    children: list = field(default_factory=list)
    label: str = ""

    def explain(self, indent: int = 0) -> str:
        pad = "  " * indent
        line = "[{} cf={:.2f}] {}".format(certainty_label(self.cf), self.cf, self.goal)
        if self.label: line += "  # " + self.label
        return "\n".join([pad + line] + [c.explain(indent + 1) for c in self.children])


# ---------------------------------------------------------------------------
# 5. BACKWARD-CHAINING SOLVER (acarlson99 + pytholog)
# ---------------------------------------------------------------------------
def _rename(clause: Clause, depth: int) -> Clause:
    sfx = "_{}".format(depth); mp: dict = {}
    def r(t: Any) -> Any:
        if is_var(t):
            if t not in mp: mp[t] = t + sfx
            return mp[t]
        if isinstance(t, tuple): return tuple(r(x) for x in t)
        return t
    return Clause(r(clause.head), [r(g) for g in clause.body], clause.certainty, clause.label)

class Solver:
    def __init__(self, kb: KnowledgeBase, tnorm: TNorm = TNorm.MIN, max_depth: int = 64):
        self.kb = kb; self.tnorm = tnorm; self.max_depth = max_depth

    def query(self, goal_str: str, cut: bool = False) -> list[dict]:
        goal = _pt(goal_str)
        results = []
        for env, cf, proof in self._solve([goal], {}, 1.0, 0):
            bindings = {k: apply_env(v, env) for k, v in env.items() if is_var(k)}
            results.append({"bindings": bindings, "cf": round(cf, 4), "proof": proof})
            if cut: break
        return results

    def query_best(self, goal_str: str) -> dict | None:
        r = self.query(goal_str)
        return max(r, key=lambda x: x["cf"]) if r else None

    def query_all_bindings(self, goal_str: str, var: str) -> list[str]:
        return [r["bindings"].get(var, "") for r in self.query(goal_str) if var in r["bindings"]]

    def _solve(self, goals, env, cf, depth) -> Generator:
        if depth > self.max_depth: return
        if not goals:
            yield env, cf, ProofNode("true", cf); return
        goal, *rest = goals
        goal = tuple(apply_env(t, env) for t in goal)
        pred = goal[0]
        if pred in ("not", "\\+"):
            inner = list(goal[1:]) if len(goal) > 1 else []
            if not list(self._solve(inner, env, cf, depth + 1)):
                yield from self._solve(rest, env, cf, depth + 1)
            return
        if pred == "eq" and len(goal) == 3:
            ne = unify(goal[1], goal[2], env)
            if ne is not None: yield from self._solve(rest, ne, cf, depth + 1)
            return
        if pred in ("neq", "\\=") and len(goal) == 3:
            if resolve(goal[1], env) != resolve(goal[2], env):
                yield from self._solve(rest, env, cf, depth + 1)
            return
        for clause in self.kb.lookup(pred):
            renamed = _rename(clause, depth)
            ne = unify(goal, renamed.head, env)
            if ne is None: continue
            combined = combine_cf([cf, renamed.certainty], self.tnorm)
            for re2, cf2, child in self._solve(renamed.body + rest, ne, combined, depth + 1):
                yield re2, cf2, ProofNode(_ts(goal), cf2, [child], clause.label)


# ---------------------------------------------------------------------------
# 6. WINTER AI BUILT-IN KNOWLEDGE
# ---------------------------------------------------------------------------
WINTER_RULES = """
% Identity
is_ai(winter).
name(winter, winter_ai).
creator(winter, ineza_aime_bruno).
country(winter, rwanda).
version(winter, 3).

% Greeting
greeting_word(hello, en).
greeting_word(hi, en).
greeting_word(hey, en).
greeting_word(bonjour, fr).
greeting_word(salut, fr).
greeting_word(bonsoir, fr).
greeting_word(muraho, rw).
greeting_word(bite, rw).

% Thanks
thanks_word(thanks, en).
thanks_word(thank, en).
thanks_word(appreciate, en).
thanks_word(merci, fr).
thanks_word(murakoze, rw).

% Farewell
farewell_word(bye, en).
farewell_word(goodbye, en).
farewell_word(later, en).
farewell_word(murabeho, rw).
farewell_word(revoir, fr).

% Identity questions
identity_word(who, en).
identity_word(name, en).
identity_word(yourself, en).
identity_word(qui, fr).
identity_word(witwa, rw).
identity_word(uri, rw).

% Wellbeing
wellbeing_word(how, en).
wellbeing_word(doing, en).
wellbeing_word(fine, en).
wellbeing_word(comment, fr).
wellbeing_word(amakuru, rw).

% Help
help_word(help, en).
help_word(assist, en).
help_word(can, en).
help_word(aide, fr).
help_word(saidia, rw).

% Sentiment (certainty factors - PESAD style)
positive_word(good) cf 0.9.
positive_word(great) cf 0.95.
positive_word(love) cf 0.9.
positive_word(happy) cf 0.85.
positive_word(excellent) cf 0.95.
positive_word(wonderful) cf 0.9.
positive_word(nice) cf 0.8.
positive_word(awesome) cf 0.9.
positive_word(perfect) cf 0.9.
positive_word(bien) cf 0.85.
positive_word(neza) cf 0.9.
positive_word(byiza) cf 0.9.
negative_word(bad) cf 0.9.
negative_word(hate) cf 0.95.
negative_word(sad) cf 0.85.
negative_word(angry) cf 0.9.
negative_word(terrible) cf 0.9.
negative_word(awful) cf 0.9.
negative_word(mauvais) cf 0.85.
negative_word(triste) cf 0.85.

% Intent rules (backward chaining - acarlson99 style)
intent(Token, Lang, greeting) :- greeting_word(Token, Lang).
intent(Token, Lang, thanks) :- thanks_word(Token, Lang).
intent(Token, Lang, farewell) :- farewell_word(Token, Lang).
intent(Token, Lang, identity) :- identity_word(Token, Lang).
intent(Token, Lang, wellbeing) :- wellbeing_word(Token, Lang).
intent(Token, Lang, help) :- help_word(Token, Lang).

% Sentiment rules
sentiment(Token, positive) :- positive_word(Token).
sentiment(Token, negative) :- negative_word(Token).

% Translation facts
translate(hello, en, bonjour, fr) cf 1.0.
translate(hello, en, muraho, rw) cf 1.0.
translate(thanks, en, merci, fr) cf 1.0.
translate(thanks, en, murakoze, rw) cf 1.0.
translate(good, en, bon, fr) cf 1.0.
translate(good, en, byiza, rw) cf 1.0.
translate(friend, en, ami, fr) cf 1.0.
translate(friend, en, inshuti, rw) cf 1.0.
translate(water, en, eau, fr) cf 1.0.
translate(water, en, amazi, rw) cf 1.0.
translate(food, en, nourriture, fr) cf 1.0.
translate(food, en, ibiribwa, rw) cf 1.0.
translate(school, en, ecole, fr) cf 1.0.
translate(school, en, ishuri, rw) cf 1.0.
translate(yes, en, oui, fr) cf 1.0.
translate(yes, en, yego, rw) cf 1.0.
translate(no, en, non, fr) cf 1.0.
translate(no, en, oya, rw) cf 1.0.
translate(love, en, amour, fr) cf 1.0.
translate(love, en, urukundo, rw) cf 1.0.
translate(home, en, maison, fr) cf 1.0.
translate(home, en, inzu, rw) cf 1.0.
translate(work, en, travail, fr) cf 1.0.
translate(work, en, akazi, rw) cf 1.0.
translate(bonjour, fr, muraho, rw) cf 1.0.
translate(merci, fr, murakoze, rw) cf 1.0.
translate(ami, fr, inshuti, rw) cf 1.0.
translate(oui, fr, yego, rw) cf 1.0.

% Transitive translation (PESAD certainty chaining)
can_translate(W, L1, T, L2) :- translate(W, L1, T, L2).
can_translate(W, L1, T, L2) :- translate(W, L1, Mid, Lmid), translate(Mid, Lmid, T, L2) cf 0.9.

% Rwanda facts
capital(rwanda, kigali).
language(rwanda, kinyarwanda).
language(rwanda, english).
language(rwanda, french).
language(rwanda, swahili).
landscape(rwanda, thousand_hills).
region(rwanda, east_africa).
border(rwanda, uganda).
border(rwanda, tanzania).
border(rwanda, burundi).
border(rwanda, drc).
park(rwanda, volcanoes_national_park).
currency(rwanda, rwandan_franc).

% Winter AI system facts
engine(winter, python).
engine(winter, scheme).
engine(winter, prolog).
engine(winter, lisp).
engine(winter, ocaml).
engine(winter, cpp).
engine(winter, mercury).
knows_language(winter, english).
knows_language(winter, french).
knows_language(winter, kinyarwanda).
deployed_on(backend, render).
deployed_on(frontend, vercel).
"""

def build_winter_kb() -> KnowledgeBase:
    kb = KnowledgeBase("winter")
    kb.load_text(WINTER_RULES)
    return kb
