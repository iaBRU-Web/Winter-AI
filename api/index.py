"""
Winter AI -- Polyglot reasoning backend.
Created by INEZA Aime Bruno, Rwanda.
Deployed on Render at https://backend-winter.onrender.com

Pipeline per request:
  Python -> Logic Engine (pytholog+PESAD+acarlson) -> Scheme (Guile) ->
  Prolog (SWI-Prolog) -> Common Lisp (SBCL) -> OCaml (native) ->
  C++ (native) -> Mercury-style -> TF-IDF retrieval -> final answer
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .engines.retrieval import KnowledgeIndex
from .engines.orchestrator import WinterOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winter")

app = FastAPI(
    title="Winter AI",
    description="Polyglot reasoning backend -- Python + Logic Engine + Scheme + Prolog + Common Lisp + OCaml + C++ + Mercury-style",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your Vercel domain once it is live
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR   = Path(__file__).resolve().parent
INFO_DIR   = BASE_DIR / "info"
TEACH_DIR  = BASE_DIR / "inf" / "teach"
CACHE_DIR  = BASE_DIR / ".cache"
BRAIN_FILE = INFO_DIR / "brain.txt"

knowledge: KnowledgeIndex = KnowledgeIndex(INFO_DIR, TEACH_DIR, CACHE_DIR)
orchestrator: Optional[WinterOrchestrator] = None


@app.on_event("startup")
async def startup():
    global orchestrator
    stats = knowledge.reload()
    orchestrator = WinterOrchestrator(knowledge)
    # Warm up Guile to absorb first-run bytecode compile cost
    try:
        orchestrator.scheme_layer(["hello"], "en")
        logger.info("Scheme (Guile) warmed up")
    except Exception as e:
        logger.warning("Scheme warm-up skipped: %s", e)
    logger.info("Winter AI ready. Docs=%d Files=%s", stats["documents"], list(stats["files"].keys()))


# ---- Models ----------------------------------------------------------------
class MsgRequest(BaseModel):
    prompt: str
    chat_id: str = "default"
    lang: str = "en"

class BrainRequest(BaseModel):
    content: str

class MsgResponse(BaseModel):
    chat_id: str
    lang: str
    reasoning_steps: list[dict]
    final_answer: str
    knowledge_source: str
    output_valid: bool

class HealthResponse(BaseModel):
    status: str
    version: str
    engines: list[str]
    indexed_documents: int
    knowledge_files: list[str]
    teach_files: list[str]


# ---- Routes ----------------------------------------------------------------
@app.post("/api/v1/chats/message", response_model=MsgResponse)
async def chat_message(req: MsgRequest):
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt cannot be empty")
    return orchestrator.run(req.prompt, req.lang, req.chat_id)


@app.post("/api/v1/reason")
async def reason(req: MsgRequest):
    result = orchestrator.run(req.prompt, req.lang, req.chat_id)
    return {"trace": result["reasoning_steps"], "answer": result["final_answer"]}


@app.get("/api/v1/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="online",
        version="3.0.0",
        engines=["Python", "Logic Engine (pytholog+PESAD+acarlson)",
                 "Scheme (GNU Guile)", "Prolog (SWI-Prolog)",
                 "Common Lisp (SBCL)", "OCaml (native)", "C++ (native)", "Mercury-style (Python)"],
        indexed_documents=len(knowledge.index.docs),
        knowledge_files=[f for f in knowledge.loaded_files if f.startswith("info/")],
        teach_files=[f for f in knowledge.loaded_files if f.startswith("teach/")],
    )


@app.get("/api/v1/brain")
async def get_brain():
    text = BRAIN_FILE.read_text(encoding="utf-8") if BRAIN_FILE.exists() else ""
    return {"content": text, "size": len(text)}


@app.post("/api/v1/brain/update")
async def update_brain(req: BrainRequest):
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="content cannot be empty")
    INFO_DIR.mkdir(parents=True, exist_ok=True)
    BRAIN_FILE.write_text(req.content, encoding="utf-8")
    stats = knowledge.reload()
    return {"status": "updated", "size": len(req.content), "documents": stats["documents"]}


@app.post("/api/v1/teach/upload")
async def teach_upload(file: UploadFile = File(...)):
    if Path(file.filename).suffix.lower() not in (".txt", ".md"):
        raise HTTPException(status_code=400, detail="Only .txt and .md files accepted")
    TEACH_DIR.mkdir(parents=True, exist_ok=True)
    dest = TEACH_DIR / Path(file.filename).name
    dest.write_bytes(await file.read())
    stats = knowledge.reload()
    return {"status": "taught", "filename": file.filename, "documents": stats["documents"]}


@app.post("/api/v1/teach/reload")
async def teach_reload():
    stats = knowledge.reload()
    return {"status": "reloaded", **stats}


@app.get("/api/v1/teach/list")
async def teach_list():
    return {"teach_dir": str(TEACH_DIR),
            "files": {k: v for k, v in knowledge.loaded_files.items() if k.startswith("teach/")}}


@app.get("/")
async def root():
    return {
        "name": "Winter AI",
        "version": "3.0.0",
        "tagline": "Polyglot reasoning backend -- Python + Logic Engine + Scheme + Prolog + Common Lisp + OCaml + C++ + Mercury-style",
        "created_by": "INEZA Aime Bruno, Rwanda",
        "docs": "/docs",
        "health": "/api/v1/health",
        "teach_folder": "api/inf/teach/ -- drop .txt or .md files here to teach Winter new information",
        "backend_url": "https://backend-winter.onrender.com",
    }
