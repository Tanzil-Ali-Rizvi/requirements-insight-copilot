"""Optional MongoDB Atlas Vector Search backend for document retrieval.

Enable with:
    MONGODB_URI=mongodb+srv://...   (Atlas free cluster works)
    EMBED_BASE_URL / EMBED_API_KEY / EMBED_MODEL   (any OpenAI-compatible /embeddings endpoint)
Then run `python scripts/index_atlas.py` once to embed the docs and create the index.
"""
from __future__ import annotations

import json
import os
import urllib.request

from .retrieval import Chunk, Hit, load_chunks

DB, COLLECTION, INDEX = "ric", "doc_chunks", "doc_vector_index"


def embed(texts: list[str]) -> list[list[float]]:
    req = urllib.request.Request(
        os.environ["EMBED_BASE_URL"].rstrip("/") + "/embeddings",
        data=json.dumps({"model": os.environ["EMBED_MODEL"], "input": texts}).encode(),
        headers={"Authorization": f"Bearer {os.environ.get('EMBED_API_KEY', '')}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return [d["embedding"] for d in json.load(resp)["data"]]


def _collection():
    from pymongo import MongoClient  # optional dependency
    return MongoClient(os.environ["MONGODB_URI"])[DB][COLLECTION]


def index_docs() -> int:
    from pymongo.operations import SearchIndexModel
    chunks = load_chunks()
    vectors = embed([f"{c.title}. {c.section}. {c.text}" for c in chunks])
    coll = _collection()
    coll.delete_many({})
    coll.insert_many([{**c.__dict__, "embedding": v} for c, v in zip(chunks, vectors)])
    if INDEX not in [i["name"] for i in coll.list_search_indexes()]:
        coll.create_search_index(SearchIndexModel(
            name=INDEX, type="vectorSearch",
            definition={"fields": [{"type": "vector", "path": "embedding",
                                    "numDimensions": len(vectors[0]), "similarity": "cosine"}]}))
    return len(chunks)


class AtlasRetriever:
    def search(self, question: str, k: int = 4) -> list[Hit]:
        pipeline = [
            {"$vectorSearch": {"index": INDEX, "path": "embedding", "queryVector": embed([question])[0],
                               "numCandidates": 50, "limit": k}},
            {"$project": {"_id": 0, "doc": 1, "title": 1, "section": 1, "text": 1,
                          "score": {"$meta": "vectorSearchScore"}}},
        ]
        return [Hit(Chunk(d["doc"], d["title"], d["section"], d["text"]), d["score"])
                for d in _collection().aggregate(pipeline)]
