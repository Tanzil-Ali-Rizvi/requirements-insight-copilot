"""Document retrieval over the BA artefacts (BRD, user stories, policies, process maps, findings).

Default backend: BM25 over heading-level chunks, which needs no model download or API key.
Optional backend: MongoDB Atlas Vector Search (see ric.retrieval_atlas), selected when
MONGODB_URI is set.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from rank_bm25 import BM25Okapi

from .text import tokenize

DOCS = Path(__file__).resolve().parents[2] / "docs"


@dataclass(frozen=True)
class Chunk:
    doc: str        # path relative to docs/, e.g. "BRD.md"
    title: str      # document title (first "# " heading)
    section: str    # section heading
    text: str

    @property
    def citation(self) -> str:
        return f"{self.doc} § {self.section}"


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float


def load_chunks(root: Path = DOCS) -> list[Chunk]:
    """Split every Markdown file into one chunk per '## ' section (plus the intro)."""
    chunks: list[Chunk] = []
    for path in sorted(root.rglob("*.md")):
        raw = path.read_text(encoding="utf-8")
        raw = re.sub(r"```mermaid.*?```", " ", raw, flags=re.DOTALL)  # diagrams are not prose
        m = re.search(r"^# (.+)$", raw, flags=re.MULTILINE)
        title = m.group(1).strip() if m else path.stem
        parts = re.split(r"^## (.+)$", raw, flags=re.MULTILINE)
        intro = re.sub(r"^# .+$", "", parts[0], flags=re.MULTILINE).strip()
        rel = path.relative_to(root).as_posix()
        if intro:
            chunks.append(Chunk(rel, title, "Overview", intro))
        for heading, body in zip(parts[1::2], parts[2::2]):
            if body.strip():
                chunks.append(Chunk(rel, title, heading.strip(), body.strip()))
    return chunks


class BM25Retriever:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        corpus = [tokenize(f"{c.title} {c.section} {c.section} {c.text}") for c in chunks]
        self._bm25 = BM25Okapi(corpus)

    def search(self, question: str, k: int = 4) -> list[Hit]:
        scores = self._bm25.get_scores(tokenize(question))
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [Hit(self.chunks[i], float(scores[i])) for i in order if scores[i] > 0]


@lru_cache(maxsize=1)
def default_retriever():
    if os.getenv("MONGODB_URI"):
        from .retrieval_atlas import AtlasRetriever
        return AtlasRetriever()
    return BM25Retriever(load_chunks())


def best_sentences(question: str, text: str, n: int = 3) -> str:
    """Extractive answer: the sentences or table rows of `text` that share the most terms with the question."""
    q = set(tokenize(question))
    units: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or set(line) <= set("|- :") or line.startswith("```"):
            continue
        if line.startswith("|"):
            units.append(" ".join(c.strip() for c in line.strip("|").split("|") if c.strip()))
        else:
            units.extend(s.strip() for s in re.split(r"(?<=[.!?])\s+", line) if s.strip())
    if len(units) <= 8:  # a short section is the answer as a whole
        return " ".join(u.lstrip("-*0123456789. ").replace("**", "") for u in units)
    scored = sorted(((len(q & set(tokenize(u))), i, u) for i, u in enumerate(units)), key=lambda t: (-t[0], t[1]))
    keep = sorted((i, u) for s, i, u in scored[:n] if s > 0)
    picked = [u.lstrip("-*0123456789. ").replace("**", "") for _, u in keep]
    return " ".join(picked) if picked else units[0] if units else ""
