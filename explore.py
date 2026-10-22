"""Step 5 exploration: look at raw results and distances before building anything clever.

Usage:  python explore.py
"""
import json
import os
import statistics

from db import DATA_PATH, get_collection

collection = get_collection()
print("items:", collection.count())

# 1. How much of each paper does the embedding model actually read? (it truncates at 256 tokens)
from tokenizers import Tokenizer

tok_path = os.path.expanduser("~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx/tokenizer.json")
tokenizer = Tokenizer.from_file(tok_path)  # fresh copy, no truncation
with open(DATA_PATH) as f:
    papers = [json.loads(line) for line in f]
lengths = [len(tokenizer.encode(f"{p['title']}. {p['abstract']}").ids) for p in papers]
over = sum(n > 256 for n in lengths)
print(f"\ntokens per document: median {statistics.median(lengths):.0f}, max {max(lengths)}; "
      f"{over}/{len(lengths)} ({over / len(lengths):.0%}) are cut off at 256")

# 2. The raw result object, exactly as Chroma returns it
raw = collection.query(query_texts=["shrinking a big neural network so it runs on a phone"], n_results=2)
print("\nraw result keys:", list(raw.keys()))
print("ids:", raw["ids"])
print("distances:", raw["distances"])

# 3. Candidate test queries plus a nonsense query, with distances
QUERIES = [
    "shrinking a big neural network so it runs on a phone",
    "a chip you can reprogram after it's built to make AI models run faster",
    "helping a camera see clearly at night",
    "figuring out how far away things are from a single photo",
    "teaching a robot by letting it watch people do the task",
    "my grandmother's lasagna recipe for a dinner party",  # should match nothing
]
res = collection.query(query_texts=QUERIES, n_results=5, include=["metadatas", "distances"])
for q, metas, dists in zip(QUERIES, res["metadatas"], res["distances"]):
    print(f"\n> {q}")
    for m, d in zip(metas, dists):
        print(f"   {d:.3f}  [{m['primary_category']} {m['year']}] {m['title'][:85]}")
