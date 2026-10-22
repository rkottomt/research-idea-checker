"""Shared database setup: one persistent Chroma collection holding papers and saved ideas."""
import os
from datetime import datetime

import chromadb

ROOT = os.path.dirname(os.path.abspath(__file__))
STORE_PATH = os.path.join(ROOT, "chroma_store")
DATA_PATH = os.path.join(ROOT, "data", "papers.jsonl")
COLLECTION = "papers"

# source values stored in metadata
ARXIV, USER_PAPER, USER_IDEA = "arxiv", "user_paper", "user_idea"


def get_collection():
    client = chromadb.PersistentClient(path=STORE_PATH)
    # cosine distance: 0 = same direction, larger = less related (default for this model is l2)
    return client.get_or_create_collection(name=COLLECTION, configuration={"hnsw": {"space": "cosine"}})


def now():
    return datetime.now().isoformat(timespec="seconds")


def paper_record(paper, source):
    """(id, document, metadata) for one paper. The title + abstract is what gets embedded."""
    authors = paper.get("authors") or []
    author_str = ", ".join(authors[:5]) + (" et al." if len(authors) > 5 else "")
    metadata = {
        "title": paper["title"],
        "authors": author_str,
        "primary_category": paper.get("primary_category") or "unknown",
        "year": int(paper.get("year") or datetime.now().year),
        "url": paper.get("url") or "",
        "source": source,
        "added_at": now(),
    }
    return paper["id"], f"{paper['title']}. {paper['abstract']}", metadata
