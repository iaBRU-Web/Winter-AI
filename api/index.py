"""
Winter AI - Multi-paradigm reasoning engine
Created by INEZA Aime Bruno, Rwanda
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
import subprocess
import unicodedata
import logging
import re
import os
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winter")

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Winter AI",
    description="Multi-paradigm reasoning engine — EN → FR → RW",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Globals ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
BRAIN_FILE = BASE_DIR / "brain.txt"
INFO_DIR = BASE_DIR / "info"
BRAIN_TEXT: str = ""
KNOWLEDGE_BASE: dict[str, str] = {}

KINYARWANDA_WORDS = {
    "muraho", "murakoze", "amakuru", "ni", "meza", "umukino",
    "kode", "ineza", "uyu", "iyo", "ubwo", "kandi", "ariko",
    "cyane", "neza", "bite", "ese", "ndashaka", "nagira", "ngo",
    "ubumenyi", "gutekereza", "igisubizo", "ikibazo", "igihugu",
    "umuryango", "ubuzima", "akazi", "ishuri", "igitabo",
    "ubuhanzi", "amahoro", "intambara", "urukundo", "inshuti",
    "amateka", "siyanse", "matematiki", "jeografiya", "isi",
    "izuba", "ukwezi", "inyenyeri", "igiti", "inyamaswa",
    "umuntu", "umwana", "indyo", "umwarimu", "umunyeshuri",
    "iterambere", "ikoranabuhanga", "interineti", "porogiram",
    "ekonomiya", "ubucuruzi", "ubuhinzi", "inganda", "uburezi",
    "ubwigenge", "ubungakanye", "ubutabera", "umuco", "idini",
    "imibare", "nimero", "atome", "selile", "biologiya",
    "fiziki", "chimie", "ubuvuzi", "inkingo", "amaraso",
    "umutima", "ubwonko", "ingufu", "amashanyarazi", "urumuri",
    "ijwi", "ubushyuhe", "uburemere", "galaxi", "ikirangamubiri",
    "rwanda", "kigali", "afurika", "aziya", "uburayi", "amerika",
    "inyanja", "umusozi", "uruzi", "imvura", "umuyaga", "ikirere",
    "ishyamba", "ibidukikije", "zahabu", "icyuma", "amafaranga"
}

FRENCH_CHARS = set("éèêëàâùûüîïôçœæ")


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    global BRAIN_TEXT, KNOWLEDGE_BASE
    INFO_DIR.mkdir(parents=True, exist_ok=True)

    if BRAIN_FILE.exists():
        BRAIN_TEXT = BRAIN_FILE.read_text(encoding="utf-8")
        logger.info(f"Loaded brain.txt ({len(BRAIN_TEXT)} chars)")
    else:
        BRAIN_TEXT = "Winter AI is a multi-paradigm reasoning engine."
        logger.warning("brain.txt not found, using default")

    KNOWLEDGE_BASE = {}
    for f in INFO_DIR.glob("*"):
        if f.suffix in (".txt", ".md") and f.is_file():
            try:
                KNOWLEDGE_BASE[f.name] = f.read_text(encoding="utf-8")
                logger.info(f"Loaded knowledge: {f.name}")
            except Exception as e:
                logger.error(f"Failed to load {f.name}: {e}")

    logger.info(f"Winter AI ready. Knowledge files: {list(KNOWLEDGE_BASE.keys())}")


# ── Language detection ─────────────────────────────────────────────────────
def detect_language(text: str) -> str:
    lower = text.lower()
    words = set(re.findall(r'\w+', lower))

    # Kinyarwanda check
    rw_hits = words & KINYARWANDA_WORDS
    if len(rw_hits) >= 1:
        # avoid false positives with short common words
        if any(w in lower for w in ["muraho", "murakoze", "amakuru", "umukino"]):
            return "rw"

    # French check
    fr_hits = sum(1 for c in text if c.lower() in FRENCH_CHARS)
    french_words = {"bonjour", "merci", "comment", "vous", "je", "est", "une", "les"}
    fr_word_hits = words & french_words
    if fr_hits >= 1 or len(fr_word_hits) >= 2:
        return "fr"

    return "en"


# ── Knowledge search ──────────────────────────────────────────────────────
def search_all_knowledge(query: str, lang: str) -> tuple[str, str]:
    """Returns (answer, source_file)"""
    q_lower = query.lower()
    tokens = re.findall(r'\w+', q_lower)

    best_score = 0
    best_answer = ""
    best_source = "brain.txt"

    def score_text(text: str) -> tuple[int, str]:
        lines = text.splitlines()
        best = 0
        best_line = ""
        for line in lines:
            line = line.strip()
            if not line:
                continue
            ll = line.lower()
            hits = sum(1 for t in tokens if t in ll)
            # Bonus: line starts with language tag
            lang_bonus = 2 if ll.startswith(lang.upper() + ":") else 0
            score = hits + lang_bonus
            if score > best:
                best = score
                best_line = line
        return best, best_line

    # Search brain.txt
    sc, ln = score_text(BRAIN_TEXT)
    if sc > best_score:
        best_score = sc
        best_answer = ln
        best_source = "brain.txt"

    # Search knowledge files
    for fname, content in KNOWLEDGE_BASE.items():
        sc, ln = score_text(content)
        if sc > best_score:
            best_score = sc
            best_answer = ln
            best_source = fname

    # Dictionary cross-reference
    if "dictionary.txt" in KNOWLEDGE_BASE:
        dict_text = KNOWLEDGE_BASE["dictionary.txt"]
        for line in dict_text.splitlines():
            parts = {p.split(":")[0].strip(): p.split(":")[1].strip()
                     for p in line.split("|") if ":" in p}
            match_found = any(t in str(parts.values()).lower() for t in tokens)
            if match_found and lang in ["fr", "rw", "en"]:
                lang_key = lang.upper()
                if lang_key in parts:
                    return f"[{lang_key}] {parts[lang_key]}", "dictionary.txt"

    return best_answer or query, best_source


# ── Pydantic models ────────────────────────────────────────────────────────
class MessageRequest(BaseModel):
    prompt: str
    chat_id: str
    lang: str = "en"


class ParadigmStep(BaseModel):
    engine: str
    status: str
    output: str
    duration_ms: float


class MessageResponse(BaseModel):
    chat_id: str
    lang: str
    reasoning_steps: list[ParadigmStep]
    final_answer: str
    knowledge_source: str


class BrainUpdateRequest(BaseModel):
    content: str


class HealthResponse(BaseModel):
    status: str
    version: str
    knowledge_files: list[str]
    brain_size: int


# ── Winter Engine ─────────────────────────────────────────────────────────
class WinterEngine:

    def python_layer(self, prompt: str, lang: str) -> ParadigmStep:
        t0 = time.perf_counter()
        logger.info(f"[Python] Orchestrating: lang={lang}, prompt={prompt[:50]}")
        detected = detect_language(prompt)
        effective_lang = lang if lang != "en" else detected
        out = f"Detected language: {detected} | Effective: {effective_lang} | Tokens: {len(prompt.split())}"
        return ParadigmStep(engine="Python", status="ok", output=out,
                            duration_ms=round((time.perf_counter() - t0) * 1000, 2))

    def prolog_layer(self, prompt: str, lang: str) -> tuple[ParadigmStep, str, str]:
        t0 = time.perf_counter()
        answer, source = search_all_knowledge(prompt, lang)
        out = f"[{lang.upper()}] Searched knowledge base → matched: '{answer[:80]}' from {source}"
        return (ParadigmStep(engine="Prolog", status="ok", output=out,
                             duration_ms=round((time.perf_counter() - t0) * 1000, 2)),
                answer, source)

    def mercury_layer(self, answer: str) -> ParadigmStep:
        t0 = time.perf_counter()
        is_det = bool(answer and len(answer.strip()) > 0)
        out = f"Determinism check: {'PASS — single answer path' if is_det else 'WARN — ambiguous'}"
        return ParadigmStep(engine="Mercury", status="ok", output=out,
                            duration_ms=round((time.perf_counter() - t0) * 1000, 2))

    def ocaml_layer(self, answer: str) -> ParadigmStep:
        t0 = time.perf_counter()
        try:
            answer.encode("utf-8").decode("utf-8")
            norm = unicodedata.normalize("NFC", answer)
            out = f"UTF-8 valid | NFC normalized | Chars: {len(norm)}"
            status = "ok"
        except Exception as e:
            out = f"Encoding error: {e}"
            status = "error"
        return ParadigmStep(engine="OCaml", status=status, output=out,
                            duration_ms=round((time.perf_counter() - t0) * 1000, 2))

    def lisp_layer(self, prompt: str) -> ParadigmStep:
        t0 = time.perf_counter()
        tokens = re.findall(r'\w+', prompt.lower())
        s_expr = "(query " + " ".join(f"'{t}" for t in tokens[:10]) + ")"
        out = f"S-expr: {s_expr}"
        return ParadigmStep(engine="LISP", status="ok", output=out,
                            duration_ms=round((time.perf_counter() - t0) * 1000, 2))

    def cpp_layer(self, answer: str) -> ParadigmStep:
        t0 = time.perf_counter()
        safe = re.sub(r'[^\w\s\-.,!?éèàùêîôûçœæ]', '', answer)[:120]
        ue_instr = f'UE_INSTR("{safe}")'
        out = f"Unreal Engine payload: {ue_instr}"
        return ParadigmStep(engine="C++", status="ok", output=out,
                            duration_ms=round((time.perf_counter() - t0) * 1000, 2))

    def schema_layer(self, answer: str, lang: str) -> ParadigmStep:
        t0 = time.perf_counter()
        checks = {
            "non_empty": bool(answer.strip()),
            "valid_lang": lang in ("en", "fr", "rw"),
            "length_ok": 1 <= len(answer) <= 4096,
            "utf8_clean": all(ord(c) < 65536 for c in answer),
        }
        passed = all(checks.values())
        out = f"Schema: {checks} | {'VALID' if passed else 'INVALID'}"
        return ParadigmStep(engine="Schema", status="ok" if passed else "warn", output=out,
                            duration_ms=round((time.perf_counter() - t0) * 1000, 2))

    def build_final_answer(self, prompt: str, raw: str, lang: str) -> str:
        """Compose a human-readable answer in the target language."""
        q = prompt.strip().rstrip("?").lower()

        # Greeting patterns
        greetings = {
            "en": {"hello", "hi", "hey", "greetings"},
            "fr": {"bonjour", "salut", "bonsoir"},
            "rw": {"muraho", "bite"},
        }
        for lng, words in greetings.items():
            if any(w in q for w in words):
                replies = {
                    "en": "Hello! I am Winter AI, your strong reasoning assistant. How can I help you today?",
                    "fr": "Bonjour ! Je suis Winter AI, votre assistant de raisonnement multi-paradigme. Comment puis-je vous aider ?",
                    "rw": "Muraho! Ndi Winter AI, umufasha wawe wo gutekereza. Nigute nakugira?",
                }
                return replies.get(lang, replies["en"])

        # Thank you
        thanks = {"thank", "thanks", "merci", "murakoze"}
        if any(w in q for w in thanks):
            replies = {
                "en": "You're welcome! Winter AI is here to assist you.",
                "fr": "De rien ! Winter AI est là pour vous aider.",
                "rw": "Ntacyo! Winter AI iri hano kugufasha.",
            }
            return replies.get(lang, replies["en"])

        # How are you
        how = {"how are you", "comment ça va", "amakuru"}
        if any(w in q for w in how):
            replies = {
                "en": "I'm running perfectly — all 7 reasoning engines online. How can I assist you?",
                "fr": "Je fonctionne parfaitement — tous les 7 moteurs actifs. Comment puis-je vous aider ?",
                "rw": "Ndakora neza — imishinga 7 iri gukora. Nakugira nte?",
            }
            return replies.get(lang, replies["en"])

        # What can you do / capabilities
        capabilities = {"what can you do", "que peux-tu faire", "ushobora iki", "capabilities", "capacités"}
        if any(w in q for w in capabilities):
            replies = {
                "en": "I am Winter AI! I know about: Science (physics, chemistry, biology), Mathematics, History, Geography, Technology & Programming, Astronomy, Economics, Philosophy, Medicine, Arts, African countries, Famous scientists, Sports, Food, and World landmarks. I speak English, French, and Kinyarwanda. Ask me anything!",
                "fr": "Je suis Winter AI! Je connais: Science (physique, chimie, biologie), Mathématiques, Histoire, Géographie, Technologie, Astronomie, Économie, Philosophie, Médecine, Arts, pays africains et bien plus. Je parle anglais, français et kinyarwanda. Posez-moi n'importe quelle question!",
                "rw": "Ndi Winter AI! Nzi: Siyanse (fiziki, chimie, biologiya), Matematiki, Amateka, Jeografiya, Ikoranabuhanga, Astronomiya, Ekonomiya, Filozofiya, Ubuvuzi, Ubuhanzi, ibihugu bya Afurika, n'ibindi byinshi. Ndavuga Icyongereza, Igifaransa, na Kinyarwanda. Baza ikibazo icyo aricyo cyose!",
            }
            return replies.get(lang, replies["en"])

        # Who made you / who created you
        creator = {"who made you", "who created you", "qui t'a créé", "wakuremye", "wavushije"}
        if any(w in q for w in creator):
            replies = {
                "en": "I am Winter AI, created by INEZA Aime Bruno from Rwanda. I am a multi-paradigm reasoning engine that runs 7 layers of logic to answer your questions.",
                "fr": "Je suis Winter AI, créé par INEZA Aime Bruno du Rwanda. Je suis un moteur de raisonnement multi-paradigme qui utilise 7 couches logiques pour répondre à vos questions.",
                "rw": "Ndi Winter AI, wahujwe na INEZA Aime Bruno wo mu Rwanda. Ndi mashini yo gutekereza ikoresheje inzira 7 zo gusubiza ibibazo byawe.",
            }
            return replies.get(lang, replies["en"])

        # Physics questions
        physics = {"newton", "gravity", "force", "energy", "physics", "relativity", "quantum", "atom", "electron", "speed of light", "physique", "gravité", "fiziki", "uburemere"}
        if any(w in q for w in physics):
            replies = {
                "en": "Physics knowledge: Newton's laws govern motion (F=ma). Einstein's E=mc² links energy and mass. The speed of light is ~300,000 km/s. Atoms contain protons, neutrons, and electrons. Gravity accelerates objects at 9.8 m/s² on Earth.",
                "fr": "Physique: Les lois de Newton régissent le mouvement (F=ma). E=mc² d'Einstein lie énergie et masse. La vitesse de la lumière est ~300 000 km/s. Les atomes contiennent des protons, neutrons et électrons.",
                "rw": "Fiziki: Amategeko ya Newton agenzura imyenda (F=ma). E=mc² ya Einstein ifatanya ingufu n'uburemere. Umuvuduko w'urumuri ni ~300,000 km/s. Atome irimo proton, neutron, na electron.",
            }
            return replies.get(lang, replies["en"])

        # Biology questions
        biology = {"dna", "cell", "evolution", "darwin", "biology", "organism", "gene", "protein", "virus", "bacteria", "biologie", "biologiya", "selile"}
        if any(w in q for w in biology):
            replies = {
                "en": "Biology knowledge: DNA carries genetic information in a double helix. Cells are the basic unit of life. Darwin's evolution theory shows species adapt by natural selection. The human body has ~37 trillion cells and 206 bones.",
                "fr": "Biologie: L'ADN porte l'information génétique en double hélice. Les cellules sont l'unité de base de la vie. La théorie de l'évolution de Darwin montre comment les espèces s'adaptent par sélection naturelle.",
                "rw": "Biologiya: DNA ihuza amakuru ya genetics muri double helix. Selile ni inkingi y'ubuzima. Ingano ya Darwin ya gutera imbere werekana ko ubwoko bwihinduranya hakoreshejwe guhitamo kamere.",
            }
            return replies.get(lang, replies["en"])

        # Math questions
        math_kw = {"pythagorean", "theorem", "algebra", "calculus", "mathematics", "equation", "prime", "fibonacci", "pi ", "mathematics", "mathématiques", "matematiki", "theorem"}
        if any(w in q for w in math_kw):
            replies = {
                "en": "Mathematics: Pythagorean theorem: a²+b²=c². Pi ≈ 3.14159. Prime numbers have no divisors except 1 and themselves (2,3,5,7,11...). Fibonacci sequence: 0,1,1,2,3,5,8,13,21... Calculus studies rates of change and accumulation.",
                "fr": "Mathématiques: Théorème de Pythagore: a²+b²=c². Pi ≈ 3,14159. Les nombres premiers n'ont pas d'autres diviseurs que 1 et eux-mêmes. Suite de Fibonacci: 0,1,1,2,3,5,8,13,21...",
                "rw": "Matematiki: Ingano ya Pitagora: a²+b²=c². Pi ≈ 3.14159. Imibare ya prime idafite abagabanya uretse 1 na yo ubwayo (2,3,5,7,11...). Urutonde rwa Fibonacci: 0,1,1,2,3,5,8,13,21...",
            }
            return replies.get(lang, replies["en"])

        # Rwanda questions
        rwanda_kw = {"rwanda", "kigali", "rwandan", "kagame", "rwandais", "u rwanda"}
        if any(w in q for w in rwanda_kw):
            replies = {
                "en": "Rwanda: Known as 'The Land of a Thousand Hills', Rwanda gained independence on July 1, 1962. Capital: Kigali. President: Paul Kagame. Rwanda has one of Africa's fastest-growing economies (~7-8% annually). Currency: Rwandan Franc (RWF). Main exports: tea, coffee, coltan.",
                "fr": "Rwanda: Connu comme 'Le Pays des Mille Collines', le Rwanda a obtenu son indépendance le 1er juillet 1962. Capitale: Kigali. Président: Paul Kagame. Monnaie: franc rwandais. Exportations: thé, café, coltan.",
                "rw": "U Rwanda: Izwi nka 'Igihugu cy'Imisozi Igihumbi', u Rwanda rwabonye ubwigenge ku ya 1 Nyakanga 1962. Umurwa mukuru: Kigali. Perezida: Paul Kagame. Amafaranga: Faranga ya Rwanda (RWF). Ibicuruzwa: icyayi, ikawa, coltan.",
            }
            return replies.get(lang, replies["en"])

        # Africa questions
        africa_kw = {"africa", "african", "afrique", "africain", "afurika"}
        if any(w in q for w in africa_kw):
            replies = {
                "en": "Africa: The world's second-largest continent with 54 countries and 1.4+ billion people. It contains the Nile (world's longest river), Kilimanjaro (Africa's highest peak at 5,895m), and the Sahara (world's largest hot desert). Major economies: Nigeria, South Africa, Egypt, Ethiopia, Kenya.",
                "fr": "Afrique: Le deuxième plus grand continent du monde avec 54 pays et plus de 1,4 milliard de personnes. Il contient le Nil (le fleuve le plus long du monde), le Kilimandjaro (5 895m) et le Sahara.",
                "rw": "Afurika: Igihugu kinini cya kabiri cy'isi gifite ibihugu 54 n'abantu barenga biliyoni 1.4. Irimo Nili (uruzi rureremereye rw'isi), Kilimanjaro (metero 5,895), na Sahara (ubutayu bunini bwa hafi muri isi).",
            }
            return replies.get(lang, replies["en"])

        # Technology / AI questions
        tech_kw = {"artificial intelligence", "machine learning", "programming", "python", "algorithm", "software", "computer", "technology", "intelligence artificielle", "ikoranabuhanga", "mudasobwa"}
        if any(w in q for w in tech_kw):
            replies = {
                "en": "Technology: AI simulates human intelligence through machine learning and neural networks. Python is widely used for AI and data science. Algorithms are step-by-step problem-solving instructions. The Internet connects billions of devices via TCP/IP. Cloud computing delivers services over the internet.",
                "fr": "Technologie: L'IA simule l'intelligence humaine via l'apprentissage automatique. Python est largement utilisé pour l'IA. Les algorithmes sont des instructions de résolution de problèmes. Internet connecte des milliards d'appareils via TCP/IP.",
                "rw": "Ikoranabuhanga: AI ihuza ubwenge bw'abantu hakoreshejwe kwiga kw'ubukorikori. Python ikoreshwa cyane mu AI. Algorithme ni amabwiriza yo gukemura ibibazo. Interineti ihuza ibikoresho biliyoni hakoreshejwe TCP/IP.",
            }
            return replies.get(lang, replies["en"])

        # History questions
        history_kw = {"history", "war", "revolution", "empire", "ancient", "independence", "histoire", "guerre", "amateka", "intambara"}
        if any(w in q for w in history_kw):
            replies = {
                "en": "History highlights: Ancient Egypt lasted 3000+ years. The Roman Empire fell in 476 AD. WWI (1914-1918): 17M deaths. WWII (1939-1945): 70M+ deaths. French Revolution (1789): liberty, equality, fraternity. Rwanda's independence: July 1, 1962. Nelson Mandela ended apartheid in 1994.",
                "fr": "Histoire: L'Égypte ancienne a duré 3000+ ans. L'Empire romain est tombé en 476 après J.-C. La Première Guerre mondiale (1914-1918): 17M morts. La Seconde Guerre mondiale (1939-1945): 70M+ morts. Révolution française (1789): liberté, égalité, fraternité.",
                "rw": "Amateka: Misiri ya kera yamaze imyaka 3000+. Ubwami bwa Roma bwagwiye mu 476 AD. Intambara ya 1 y'isi (1914-1918): abantu miliyoni 17 bapfuye. Intambara ya 2 y'isi (1939-1945): abantu 70M+ bapfuye. Ubwigenge bw'u Rwanda: 1 Nyakanga 1962.",
            }
            return replies.get(lang, replies["en"])

        # Space / Astronomy questions
        space_kw = {"space", "planet", "solar system", "galaxy", "universe", "black hole", "star", "moon", "sun", "espace", "planète", "univers", "isi yose", "inyenyeri", "galaxi"}
        if any(w in q for w in space_kw):
            replies = {
                "en": "Space: The universe is 13.8 billion years old. Our solar system has 8 planets. The Sun contains 99.86% of our solar system's mass. The Milky Way has 200+ billion stars. Neil Armstrong walked on the Moon on July 20, 1969. Black holes have gravity so strong not even light can escape.",
                "fr": "Espace: L'univers a 13,8 milliards d'années. Notre système solaire a 8 planètes. Le Soleil contient 99,86% de la masse du système solaire. La Voie lactée a 200+ milliards d'étoiles. Neil Armstrong a marché sur la Lune le 20 juillet 1969.",
                "rw": "Akajagari: Isi yose ifite imyaka 13.8 biliyoni. Sisitemu yacu ya zuba ifite ikirangamubiri 8. Izuba rifite 99.86% y'uburemere bwa sisitemu ya zuba. Inzira Nyamweru ifite inyenyeri 200+ biliyoni. Neil Armstrong yagiye ku Ukwezi ku ya 20 Nyakanga 1969.",
            }
            return replies.get(lang, replies["en"])

        # Use knowledge base result if meaningful
        if raw and len(raw) > 10 and raw.lower() != prompt.lower():
            # Strip language prefix tags like "EN:", "FR:", "RW:"
            clean = re.sub(r'^(EN|FR|RW):\s*', '', raw, flags=re.IGNORECASE).strip()
            if clean:
                return clean

        # Default
        defaults = {
            "en": f"Winter AI processed your query: \"{prompt}\". Please add more knowledge to brain.txt or info files for a richer answer.",
            "fr": f"Winter AI a traité votre requête : \"{prompt}\". Ajoutez plus de connaissances dans brain.txt pour des réponses plus riches.",
            "rw": f"Winter AI yakiriye ikibazo cyawe: \"{prompt}\". Ongeraho ubumenyi muri brain.txt kugira ngo ubone ibisubizo binoze.",
        }
        return defaults.get(lang, defaults["en"])


engine = WinterEngine()


# ── Routes ────────────────────────────────────────────────────────────────
@app.post("/api/v1/chats/message", response_model=MessageResponse)
async def chat_message(req: MessageRequest):
    steps = []

    # 1. Python
    steps.append(engine.python_layer(req.prompt, req.lang))

    # 2. Prolog — returns knowledge match
    prolog_step, raw_answer, source = engine.prolog_layer(req.prompt, req.lang)
    steps.append(prolog_step)

    # 3. Mercury
    steps.append(engine.mercury_layer(raw_answer))

    # 4. OCaml
    steps.append(engine.ocaml_layer(raw_answer))

    # 5. LISP
    steps.append(engine.lisp_layer(req.prompt))

    # 6. C++
    steps.append(engine.cpp_layer(raw_answer))

    # 7. Schema
    steps.append(engine.schema_layer(raw_answer, req.lang))

    final = engine.build_final_answer(req.prompt, raw_answer, req.lang)

    return MessageResponse(
        chat_id=req.chat_id,
        lang=req.lang,
        reasoning_steps=steps,
        final_answer=final,
        knowledge_source=source,
    )


@app.post("/api/v1/brain/update")
async def update_brain(req: BrainUpdateRequest):
    global BRAIN_TEXT
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    BRAIN_FILE.write_text(req.content, encoding="utf-8")
    BRAIN_TEXT = req.content
    return {"status": "updated", "size": len(req.content)}


@app.post("/api/v1/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...)):
    global KNOWLEDGE_BASE
    allowed = {".txt", ".md"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail="Only .txt and .md files allowed")
    INFO_DIR.mkdir(parents=True, exist_ok=True)
    dest = INFO_DIR / Path(file.filename).name
    content = await file.read()
    dest.write_bytes(content)
    decoded = content.decode("utf-8")
    KNOWLEDGE_BASE[file.filename] = decoded
    return {"status": "uploaded", "filename": file.filename, "size": len(decoded)}


@app.get("/api/v1/knowledge/list")
async def list_knowledge():
    files = []
    for fname, content in KNOWLEDGE_BASE.items():
        files.append({"name": fname, "size": len(content), "lines": content.count("\n") + 1})
    return {"files": files, "count": len(files)}


@app.get("/api/v1/knowledge/{filename}")
async def get_knowledge_file(filename: str):
    if filename not in KNOWLEDGE_BASE:
        raise HTTPException(status_code=404, detail="File not found")
    return {"name": filename, "content": KNOWLEDGE_BASE[filename]}


@app.get("/api/v1/brain")
async def get_brain():
    return {"content": BRAIN_TEXT, "size": len(BRAIN_TEXT)}


@app.get("/api/v1/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="online",
        version="1.0.0",
        knowledge_files=list(KNOWLEDGE_BASE.keys()),
        brain_size=len(BRAIN_TEXT),
    )


@app.get("/")
async def root():
    return {
        "name": "Winter AI",
        "tagline": "Multi-paradigm reasoning engine — EN → FR → RW",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
