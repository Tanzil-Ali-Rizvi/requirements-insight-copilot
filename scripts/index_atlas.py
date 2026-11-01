"""Embed the project documents into MongoDB Atlas and create the vector index (optional backend).

Needs MONGODB_URI, EMBED_BASE_URL, EMBED_MODEL (and EMBED_API_KEY if required) plus `pip install pymongo`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ric.retrieval_atlas import index_docs  # noqa: E402

if __name__ == "__main__":
    print(f"Indexed {index_docs()} chunks into Atlas.")
