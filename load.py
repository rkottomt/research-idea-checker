"""Embed data/papers.jsonl into the Chroma collection.

Usage:  python load.py [--limit N]

Safe to re-run: papers already in the collection are skipped, not re-embedded.
"""
import argparse
import json
import os
import sys
import time

from db import ARXIV, DATA_PATH, get_collection, paper_record

BATCH_SIZE = 100


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="only load the first N papers (for timing)")
    args = parser.parse_args()

    if not os.path.exists(DATA_PATH):
        sys.exit(f"{DATA_PATH} not found. Run `python fetch_arxiv.py` first.")
    with open(DATA_PATH) as f:
        papers = [json.loads(line) for line in f]
    if args.limit:
        papers = papers[: args.limit]

    collection = get_collection()
    existing = set(collection.get(ids=[p["id"] for p in papers], include=[])["ids"])
    todo = [p for p in papers if p["id"] not in existing]
    print(f"{len(papers)} papers in file, {len(existing)} already stored, {len(todo)} to embed")

    start = time.time()
    for i in range(0, len(todo), BATCH_SIZE):
        ids, docs, metas = zip(*(paper_record(p, ARXIV) for p in todo[i : i + BATCH_SIZE]))
        collection.add(ids=list(ids), documents=list(docs), metadatas=list(metas))
        done = i + len(ids)
        rate = done / (time.time() - start)
        print(f"  {done}/{len(todo)} embedded ({rate:.1f} papers/s, ~{(len(todo) - done) / rate:.0f}s left)")
    print(f"done in {time.time() - start:.1f}s; collection now holds {collection.count()} items")


if __name__ == "__main__":
    main()
