"""Can the store say a topic is "heating up"? Compare it with real arXiv counts.

Usage:  python eval/trend.py   (queries the live arXiv API; cached in data/)

The store holds a fixed 45 papers per category per half-year, so it can't show growth.
arXiv's own counts (totalResults for a query, per year) can.
"""
import json
import os
import sys
import time
from collections import Counter

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction  # noqa: E402

from corpus_size import total_results, unit  # noqa: E402
from db import ARXIV, DATA_PATH, get_collection  # noqa: E402

CACHE = os.path.join(ROOT, "data", "eval_trend_counts.json")
CATS = "(cat:cs.AR OR cat:cs.CV OR cat:cs.LG)"
TOPIC = 'abs:"knowledge distillation"'
TOPIC_TEXT = "knowledge distillation from a large teacher network into a small student network"
YEARS = range(2019, 2026)


def counts():
    if os.path.exists(CACHE):
        with open(CACHE) as f:
            return json.load(f)
    out = {}
    for y in YEARS:
        span = f"submittedDate:[{y}01010000 TO {y}12312359]"
        time.sleep(3)
        total = total_results(f"{CATS} AND {span}")
        time.sleep(3)
        topic = total_results(f"{CATS} AND {span} AND {TOPIC}")
        out[str(y)] = {"total": total, "topic": topic}
        print(f"  {y}: {topic} / {total}")
    with open(CACHE, "w") as f:
        json.dump(out, f)
    return out


def main():
    np.seterr(all="ignore")
    with open(DATA_PATH) as f:
        papers = [json.loads(line) for line in f]
    months = Counter(p["published"][5:7] for p in papers if 2019 <= p["year"] <= 2025)
    print("store papers by month published (2019-2025): " + ", ".join(f"{m}: {months[m]}" for m in sorted(months)))

    col = get_collection()
    got = col.get(where={"source": ARXIV}, include=["embeddings", "metadatas"])
    E, years = unit(got["embeddings"]), np.array([m["year"] for m in got["metadatas"]])
    d = 1 - unit(DefaultEmbeddingFunction()([TOPIC_TEXT])) @ E.T
    near = d[0] < 0.45  # roughly "about this topic" for this query (see eval/results.md distances)

    c = counts()
    print(f"\n{TOPIC} in {CATS}")
    print("| year | arXiv: topic papers | arXiv: all papers | arXiv: topic share | store: near-topic papers / store papers |")
    print("|---|---|---|---|---|")
    for y in YEARS:
        t, tot = c[str(y)]["topic"], c[str(y)]["total"]
        print(f"| {y} | {t:,} | {tot:,} | {t / tot:.2%} | {int((near & (years == y)).sum())} / {int((years == y).sum())} |")


if __name__ == "__main__":
    main()
