"""Step 5 exploration: look at raw results and distances before building anything clever.

Usage:  python explore.py

Prints: how many documents the embedding model truncates, the raw result object,
candidate test queries vs. a keyword-search baseline, a nonsense query, and the
distance distribution used to calibrate the novelty score.
"""
import json
import os
import random
import re
import statistics

from tokenizers import Tokenizer

from db import DATA_PATH, get_collection

collection = get_collection()
print("items:", collection.count())

# 1. How much of each paper does the embedding model actually read? (Chroma truncates at 256 tokens)
tokenizer = Tokenizer.from_file(os.path.expanduser("~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx/tokenizer.json"))
tokenizer.no_truncation()  # tokenizer.json ships with its own 128-token cutoff; turn it off to count real lengths
with open(DATA_PATH) as f:
    papers = [json.loads(line) for line in f]
docs = {p["id"]: f"{p['title']}. {p['abstract']}" for p in papers}
lengths = [len(tokenizer.encode(d).ids) for d in docs.values()]
over = sum(n > 256 for n in lengths)
print(f"\ntokens per document: median {statistics.median(lengths):.0f}, max {max(lengths)}; "
      f"{over}/{len(lengths)} ({over / len(lengths):.0%}) are cut off at 256")

# 2. The raw result object, exactly as Chroma returns it
raw = collection.query(query_texts=["shrinking a big neural network so it runs on a phone"], n_results=2)
print("\nraw result keys:", list(raw.keys()))
print("ids:", raw["ids"])
print("distances:", raw["distances"])

# 3. Candidate test queries vs. a plain keyword search
STOP = set("a an the of to and or for in on at by with from so it its it's is are be can that this into "
           "after before without but keeps old new ones one things thing made make makes was were".split())


def words(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP}


def keyword_rank(query):
    """Rank every paper by how many of the query's content words it contains (a stand-in for keyword search)."""
    q = words(query)
    scored = sorted(docs, key=lambda pid: -len(q & words(docs[pid])))
    return scored, q


QUERIES = [
    "shrinking a big neural network so it runs on a phone",
    "a chip you can reprogram after it's built to make AI models run faster",
    "hardware that can be rewired after manufacturing to speed up AI",
    "helping a camera see clearly at night",
    "a model that picks up new skills but keeps the old ones",
    "telling whether a picture was made by a computer instead of a real camera",
    "doing the math where the data is stored instead of moving it to the processor",
    "my grandmother's lasagna recipe for a dinner party",  # should match nothing
]
res = collection.query(query_texts=QUERIES, n_results=3, include=["metadatas", "distances"])
for q, ids, metas, dists in zip(QUERIES, res["ids"], res["metadatas"], res["distances"]):
    ranked, qwords = keyword_rank(q)
    print(f"\n> {q}")
    for pid, m, d in zip(ids, metas, dists):
        shared = sorted(qwords & words(docs.get(pid, "")))
        print(f"   {d:.3f}  [{m['primary_category']} {m['year']}] {m['title'][:70]}")
        print(f"          shared words: {shared or 'none'}; keyword-search rank: {ranked.index(pid) + 1}")

# 4. Calibration preview: use titles as short queries, find each one's nearest *other* paper
random.seed(0)
sample = random.sample(papers, 300)
got = collection.query(query_texts=[p["title"] for p in sample], n_results=2, include=["distances"])
nn = []
for p, ids, dists in zip(sample, got["ids"], got["distances"]):
    others = [d for i, d in zip(ids, dists) if i != p["id"]]
    nn.append(others[0])
nn.sort()
pct = lambda q: nn[int(q * (len(nn) - 1))]
print(f"\ntitle -> nearest other paper, n={len(nn)}: "
      + ", ".join(f"p{int(q * 100)} {pct(q):.3f}" for q in (0.05, 0.25, 0.5, 0.75, 0.95)))
