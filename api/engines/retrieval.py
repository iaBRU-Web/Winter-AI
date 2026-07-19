"""
Winter AI -- TF-IDF Retrieval Engine.
Pure Python cosine-similarity search. No external ML deps.
Loads api/info/ (curated) + api/inf/teach/ (user-taught) automatically.
"""
from __future__ import annotations
import math, re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

STOPWORDS = {
    "a","an","the","is","are","was","were","be","been","being",
    "what","who","whom","which","how","why","when","where",
    "do","does","did","to","of","in","on","at","for","with",
    "and","or","but","i","you","your","me","my","it","this",
    "that","these","those","can","could","will","would","should",
    "le","la","les","de","du","des","et","que","qui","est",
    "ni","na","ku","mu","ngo","kandi","ariko",
}
TOKEN_RE = re.compile(r"[a-zA-Z\u00C0-\u024F0-9']+")
LANG_RE  = re.compile(r"^(EN|FR|RW):\s*(.+)$", re.IGNORECASE)

def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS and len(t) > 1]

@dataclass
class Doc:
    doc_id: str; text: str; source: str; lang: str = "en"
    tf: Counter = field(default_factory=Counter)

class TfIdf:
    def __init__(self):
        self.docs: list[Doc] = []; self.df: Counter = Counter(); self._idf: dict = {}

    def clear(self): self.docs = []; self.df = Counter(); self._idf = {}

    def add(self, doc_id: str, text: str, source: str, lang: str = "en"):
        tf = Counter(tokenize(text))
        if not tf: return
        self.docs.append(Doc(doc_id, text, source, lang, tf))
        for t in tf: self.df[t] += 1
        self._idf = {}

    def idf(self, t: str) -> float:
        if t not in self._idf:
            n = len(self.docs) or 1
            self._idf[t] = math.log((1 + n) / (1 + self.df.get(t, 0))) + 1.0
        return self._idf[t]

    def _norm(self, tf: Counter) -> float:
        return math.sqrt(sum((c * self.idf(t))**2 for t, c in tf.items())) or 1.0

    def search(self, query: str, top_k: int = 5):
        qtf = Counter(tokenize(query))
        if not qtf or not self.docs: return []
        qn = self._norm(qtf)
        scored = []
        for doc in self.docs:
            dot = sum((qc * self.idf(t)) * (doc.tf[t] * self.idf(t))
                      for t, qc in qtf.items() if t in doc.tf)
            if dot > 0:
                scored.append((dot / (qn * self._norm(doc.tf)), doc))
        scored.sort(key=lambda p: p[0], reverse=True)
        return scored[:top_k]

def _add_line(idx: TfIdf, line: str, source: str, counter: list):
    line = line.strip()
    if not line or line.startswith("#") or line.startswith("%"): return
    if "|" in line:
        for part in line.split("|"):
            m = LANG_RE.match(part.strip())
            if m:
                counter[0] += 1
                idx.add(f"{source}:{counter[0]}", m.group(2), source, m.group(1).lower())
        return
    m = LANG_RE.match(line)
    lang, text = (m.group(1).lower(), m.group(2)) if m else ("en", line)
    counter[0] += 1
    idx.add(f"{source}:{counter[0]}", text, source, lang)

class KnowledgeIndex:
    def __init__(self, info_dir: Path, teach_dir: Path, cache_dir: Path):
        self.info_dir = info_dir; self.teach_dir = teach_dir; self.cache_dir = cache_dir
        self.index = TfIdf(); self.loaded_files: dict = {}
        self._corpus_path: Path | None = None

    def reload(self) -> dict:
        self.index.clear(); self.loaded_files = {}
        counter = [0]; merged: list[str] = []
        for folder, tag in ((self.info_dir, "info"), (self.teach_dir, "teach")):
            folder.mkdir(parents=True, exist_ok=True)
            for path in sorted(folder.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in (".txt", ".md"): continue
                try:
                    content = path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                src = f"{tag}/{path.relative_to(folder)}"
                lines = content.splitlines()
                self.loaded_files[src] = len(lines)
                for raw in lines:
                    _add_line(self.index, raw, src, counter)
                    if raw.strip(): merged.append(raw.strip())
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cp = self.cache_dir / "merged_corpus.txt"
        try:
            cp.write_text("\n".join(merged), encoding="utf-8")
            self._corpus_path = cp
        except Exception:
            self._corpus_path = None
        return {"files": self.loaded_files, "documents": len(self.index.docs)}

    def corpus_path(self) -> Path | None:
        return self._corpus_path

    def search(self, query: str, lang: str | None = None, top_k: int = 5) -> list[dict]:
        results = self.index.search(query, top_k=top_k * 2)
        if lang:
            pref = [r for r in results if r[1].lang == lang]
            if pref: results = pref
        return [{"line": d.text, "source": d.source, "score": round(s, 4), "lang": d.lang}
                for s, d in results[:top_k]]
