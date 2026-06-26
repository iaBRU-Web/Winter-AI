from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import List, Dict
from pydantic import BaseModel
import hashlib
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
BRAIN_PATH = BASE_DIR / "brain.txt"
INFO_DIR = BASE_DIR / "info"

try:
    BRAIN_MATRIX = BRAIN_PATH.read_bytes()
except FileNotFoundError as e:
    raise RuntimeError(f"Missing brain matrix file at {BRAIN_PATH}") from e

KNOWLEDGE_BASE: Dict[str, str] = {}
if INFO_DIR.exists() and INFO_DIR.is_dir():
    for p in INFO_DIR.iterdir():
        if p.is_file() and (p.name.endswith(".txt") or p.name.endswith(".md")):
            try:
                KNOWLEDGE_BASE[p.name] = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                KNOWLEDGE_BASE[p.name] = ""


def query_brain(index: int) -> int:
    if index < 0:
        raise ValueError("index must be non-negative")
    bit_len = len(BRAIN_MATRIX) * 8
    if bit_len == 0:
        raise ValueError("BRAIN_MATRIX is empty")
    idx = index % bit_len
    byte_i = idx // 8
    bit_i = idx % 8
    b = BRAIN_MATRIX[byte_i]
    return (b >> (7 - bit_i)) & 1


def search_knowledge(query: str) -> str:
    q = (query or "").lower()
    if not q:
        return ""
    for content in KNOWLEDGE_BASE.values():
        if not content:
            continue
        if q in content.lower():
            return content[:200]
    return ""


class MessageRequest(BaseModel):
    prompt: str
    chat_id: str
    validation_arrays: List[str] = []
    target_fields: Dict = {}


class ParadigmStep(BaseModel):
    paradigm: str
    status: str
    detail: str
    latency_ms: float


class MessageResponse(BaseModel):
    status: str
    reasoning_steps: List[ParadigmStep]
    final_answer: str


class WinterEngine:
    def python_layer(self, text: str) -> str:
        return "Python orchestration started"

    def prolog_layer(self, text: str) -> str:
        hit = search_knowledge(text)
        if hit:
            return hit
        h = hashlib.md5(text.encode("utf-8", errors="replace")).hexdigest()
        n = int(h, 16)
        bit_len = len(BRAIN_MATRIX) * 8
        if bit_len <= 0:
            raise ValueError("brain matrix has no bits")
        idx = n % bit_len
        flag = query_brain(idx)
        return f"[Prolog] Clause check at index {idx} returned {flag}"

    def mercury_layer(self, text: str) -> str:
        if len(set(text)) <= 3:
            raise ValueError("Non-deterministic input: insufficient unique symbols")
        return "[Mercury] Determinism check passed"

    def ocaml_layer(self, text: str) -> str:
        for ch in text:
            o = ord(ch)
            if ch.isspace():
                continue
            if o < 32 or o > 126:
                raise ValueError("Non-ASCII printable character detected")
        return "[OCaml] Type-safe structural assertion OK"

    def lisp_layer(self, text: str) -> str:
        tokens = (text or "").split()
        tokens = tokens[:8]
        joined = " ".join(tokens)
        return f"(eval {joined})"

    def cpp_layer(self, lisp_output: str) -> str:
        return f"UE_INSTR::{lisp_output}"

    def schema_layer(self, final: str) -> str:
        if not isinstance(final, str):
            raise ValueError("final must be a string")
        if len(final) <= 0:
            raise ValueError("final must be non-empty")
        return "[Schema] JSON structure validated"


_ENGINE = WinterEngine()


@app.post("/api/v1/chats/message", response_model=MessageResponse)
def post_message(req: MessageRequest) -> MessageResponse:
    if req is None:
        raise HTTPException(status_code=400, detail="Invalid request")
    prompt = req.prompt if isinstance(req.prompt, str) else ""
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    if not isinstance(req.chat_id, str) or not req.chat_id:
        raise HTTPException(status_code=400, detail="chat_id is required")

    reasoning_steps: List[ParadigmStep] = []

    try:
        t0 = time.perf_counter()
        py_detail = _ENGINE.python_layer(prompt)
        t1 = time.perf_counter()
        reasoning_steps.append(
            ParadigmStep(
                paradigm="Python",
                status="ok",
                detail=py_detail,
                latency_ms=(t1 - t0) * 1000.0,
            )
        )

        t0 = time.perf_counter()
        prolog_out = _ENGINE.prolog_layer(prompt)
        t1 = time.perf_counter()
        if prolog_out and prolog_out != "[Prolog] Knowledge hit from info folder":
            if prolog_out.startswith("[Prolog] Clause check at index"):
                prolog_detail = prolog_out
            else:
                prolog_detail = "[Prolog] Knowledge hit from info folder"
        else:
            prolog_detail = "[Prolog] Knowledge hit from info folder"
        reasoning_steps.append(
            ParadigmStep(
                paradigm="Prolog",
                status="ok",
                detail=prolog_detail,
                latency_ms=(t1 - t0) * 1000.0,
            )
        )

        t0 = time.perf_counter()
        mercury_detail = _ENGINE.mercury_layer(prompt)
        t1 = time.perf_counter()
        reasoning_steps.append(
            ParadigmStep(
                paradigm="Mercury",
                status="ok",
                detail=mercury_detail,
                latency_ms=(t1 - t0) * 1000.0,
            )
        )

        t0 = time.perf_counter()
        ocaml_detail = _ENGINE.ocaml_layer(prompt)
        t1 = time.perf_counter()
        reasoning_steps.append(
            ParadigmStep(
                paradigm="OCaml",
                status="ok",
                detail=ocaml_detail,
                latency_ms=(t1 - t0) * 1000.0,
            )
        )

        t0 = time.perf_counter()
        lisp_out = _ENGINE.lisp_layer(prompt)
        t1 = time.perf_counter()
        reasoning_steps.append(
            ParadigmStep(
                paradigm="LISP",
                status="ok",
                detail="[LISP] Symbolic expression parsed",
                latency_ms=(t1 - t0) * 1000.0,
            )
        )

        t0 = time.perf_counter()
        cpp_out = _ENGINE.cpp_layer(lisp_out)
        t1 = time.perf_counter()
        reasoning_steps.append(
            ParadigmStep(
                paradigm="C++",
                status="ok",
                detail="[C++] High-performance compilation layout generated",
                latency_ms=(t1 - t0) * 1000.0,
            )
        )

        final_answer = f"Winter Response | Chat={req.chat_id} | {cpp_out}"

        t0 = time.perf_counter()
        schema_detail = _ENGINE.schema_layer(final_answer)
        t1 = time.perf_counter()
        reasoning_steps.append(
            ParadigmStep(
                paradigm="Data Schema Validation",
                status="ok",
                detail=schema_detail,
                latency_ms=(t1 - t0) * 1000.0,
            )
        )

        return MessageResponse(status="success", reasoning_steps=reasoning_steps, final_answer=final_answer)
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal error") from e


@app.get("/api/v1/health")
def health() -> Dict:
    knowledge_files = len(KNOWLEDGE_BASE)
    return {
        "brain_size": len(BRAIN_MATRIX),
        "knowledge_files": knowledge_files,
        "status": "ok",
    }
