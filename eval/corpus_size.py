"""How often would a verdict flip if the corpus were 10x larger?

Usage:  python eval/corpus_size.py   (queries the live arXiv API; results cached in data/)

For 20 of the evaluation ideas:
  1. Coverage: ask arXiv (keyword search, our 3 categories, 2019-2025) for its top 25 papers
     and check how many we already store.
  2. Worst case: add every one of those papers and see which verdicts change.
  3. 10x growth: going from 1/10 of our store (194 papers) to the full store (1,944) is a real
     10x step. Each level gets its own calibration, so this captures both effects of a denser
     corpus: the idea's nearest paper gets closer, and so do papers' own nearest neighbours.
     The 1,944 -> 19,440 step is assumed to behave similarly.

Each idea's target paper is hidden throughout: an idea whose paper exists on arXiv but isn't
in our sample, the realistic "has this been done?" case.
"""
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction  # noqa: E402

import novelty  # noqa: E402
from db import ARXIV, get_collection  # noqa: E402
from fetch_arxiv import API, search  # noqa: E402

HERE = os.path.join(ROOT, "eval")
CACHE = os.path.join(ROOT, "data", "eval_arxiv_hits.json")
TITLE_CACHE = os.path.join(ROOT, "data", "eval_title_embeddings.npy")
SCOPE = "(cat:cs.AR OR cat:cs.CV OR cat:cs.LG) AND submittedDate:[201901010000 TO 202512312359]"
N_IDEAS, N_HITS, SCALE = 20, 25, 10


def unit(x):
    x = np.asarray(x, dtype=np.float32)
    return x / np.linalg.norm(x, axis=-1, keepdims=True)


def total_results(query, retries=4):
    url = API + "?" + urllib.parse.urlencode({"search_query": query, "max_results": 1})
    req = urllib.request.Request(url, headers={"User-Agent": "research-idea-checker"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                root = ET.fromstring(r.read())
            return int(root.findtext("{http://a9.com/-/spec/opensearch/1.1/}totalResults"))
        except Exception as e:  # arXiv returns occasional 503s
            if attempt == retries - 1:
                raise
            print(f"  arXiv error ({e}); retrying in 15s")
            time.sleep(15)


def fetch_hits(ideas):
    if os.path.exists(CACHE):
        with open(CACHE) as f:
            return json.load(f)
    cache = {"n_total": total_results(SCOPE), "hits": {}}
    for n, idea in enumerate(ideas, 1):
        time.sleep(3)
        papers = search(f"{SCOPE} AND ({idea['arxiv']})", N_HITS, sort_by="relevance")
        cache["hits"][idea["target"]] = papers
        print(f"  [{n}/{len(ideas)}] {len(papers):>2} hits for {idea['arxiv']}")
    with open(CACHE, "w") as f:
        json.dump(cache, f)
    return cache


def nn_quantiles(T, E, members, qs):
    """Nearest-other-paper distance for each title in `members`, searching only within `members`."""
    d = 1 - T[members] @ E[members].T
    np.fill_diagonal(d, np.inf)
    return np.quantile(d.min(axis=1), qs)


def main():
    np.seterr(all="ignore")  # spurious numpy-2.0 + Accelerate matmul warnings (verified in evaluate.py)
    col = get_collection()
    calib = novelty.load_calibration(col)
    got = col.get(where={"source": ARXIV}, include=["embeddings", "metadatas"])
    ids, E = got["ids"], unit(got["embeddings"])
    idx = {pid: i for i, pid in enumerate(ids)}
    ef = DefaultEmbeddingFunction()

    with open(os.path.join(HERE, "ideas.json")) as f:
        all_ideas = json.load(f)
    with open(os.path.join(HERE, "rewrites.json")) as f:
        good = {r["target"]: r["good"] for r in json.load(f)["rewrites"]}
    random.seed(20)
    ideas = random.sample(all_ideas, N_IDEAS)

    cache = fetch_hits(ideas)
    n_total = cache["n_total"]
    print(f"\narXiv papers in cs.AR/cs.CV/cs.LG, 2019-2025: {n_total:,}; our store: {len(ids):,} "
          f"({len(ids) / n_total:.2%})")

    # --- how much denser corpora pull nearest neighbours closer (for reference)
    if os.path.exists(TITLE_CACHE):
        T = np.load(TITLE_CACHE)
    else:
        T = unit(ef([m["title"] for m in got["metadatas"]]))
        np.save(TITLE_CACHE, T)
    qs = np.linspace(0.01, 0.99, 99)
    full = nn_quantiles(T, E, np.arange(len(ids)), qs)
    rng = np.random.default_rng(0)
    sub = np.mean([nn_quantiles(T, E, rng.choice(len(ids), len(ids) // SCALE, replace=False), qs)
                   for _ in range(20)], axis=0)
    delta = sub - full  # how much nearest-neighbour distances shrank going from 1/10 density to full
    print(f"NN distance (title -> nearest other paper) median: 1/10 store {np.quantile(sub, 0.5):.3f}, "
          f"full store {np.quantile(full, 0.5):.3f}; projected 10x store ~{np.quantile(full - delta, 0.5):.3f}")
    hits_total = sum(len(h) for h in cache["hits"].values())
    in_store = [p["id"] for h in cache["hits"].values() for p in h if p["id"] in idx]
    own_target = sum(pid in cache["hits"] and any(p["id"] == pid for p in cache["hits"][pid]) for pid in set(in_store))
    print(f"arXiv top hits: {hits_total}; already in our store: {len(in_store)} ({len(in_store) / hits_total:.0%}), "
          f"of which {own_target} are the idea's own target paper")

    label = lambda d, c: novelty.assess(float(d), c)["label"]  # noqa: E731
    rank = {lab: i for i, lab in enumerate(["OUT OF SCOPE", "LOOKS OPEN (in this collection)", "RELATED WORK EXISTS",
                                            "CROWDED", "VERY CLOSE MATCH"])}
    full_calib = {"nearest_neighbour_distances": sorted((lambda d: (np.fill_diagonal(d, np.inf), d.min(axis=1))[1])(1 - T @ E.T))}
    for mode in ("vector-only", "with rewrite"):
        worst, up, down, same, n = 0, 0, 0, 0, 0
        for idea in ideas:
            tgt = idea["target"]
            Q = unit(ef([idea["casual"]] + ([good[tgt]] if mode == "with rewrite" else [])))
            d = (1 - Q @ E.T).min(axis=0)
            d[idx[tgt]] = np.inf  # realistic case: the idea's paper exists on arXiv but isn't in our sample
            v_full = label(d.min(), full_calib)
            # (1) worst case: every arXiv top hit is added to the store
            miss = [p for p in cache["hits"][tgt] if p["id"] not in idx or p["id"] == tgt]
            if miss:
                dm = (1 - Q @ unit(ef([f"{p['title']}. {p['abstract']}" for p in miss])).T).min()
                worst += label(min(d.min(), dm), full_calib) != v_full
            # (2) a real 10x step inside our data: 1/10 of the store -> the full store
            for _ in range(20):
                members = rng.choice(len(ids), len(ids) // SCALE, replace=False)
                dd = 1 - T[members] @ E[members].T
                np.fill_diagonal(dd, np.inf)
                v_small = label(d[members].min(), {"nearest_neighbour_distances": sorted(dd.min(axis=1))})
                n += 1
                if rank[v_full] > rank[v_small]:
                    up += 1
                elif rank[v_full] < rank[v_small]:
                    down += 1
                else:
                    same += 1
        print(f"\n{mode} (target paper hidden):")
        print(f"  worst case, every arXiv top-25 hit added: {worst}/{N_IDEAS} verdicts change (all toward more crowded)")
        print(f"  10x growth (194 -> 1,944 papers, 20 subsamples x {N_IDEAS} ideas): verdict changes in {(up + down) / n:.0%} "
              f"({up / n:.0%} more crowded, {down / n:.0%} less crowded, {same / n:.0%} unchanged)")

if __name__ == "__main__":
    main()
