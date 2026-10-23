"""Compare ways of handling abstracts longer than the model's 256-token window.

Usage:  python eval/truncation.py   (embeddings cached in data/)

  current   title + abstract, cut at 256 tokens by the model
  (a) chunk title + overlapping 192-token windows of the abstract (stride 128); a paper scores
            as its best chunk. Papers that already fit stay as one item.
  (b) ends  title + first sentence + last sentence of the abstract

Recall is hit@5 / MRR on the 30 evaluation ideas. Embedding time is measured here, so it
matches what load.py would spend.
"""
import json
import os
import re
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction  # noqa: E402
from tokenizers import Tokenizer  # noqa: E402

from db import ARXIV, DATA_PATH, get_collection  # noqa: E402

HERE = os.path.join(ROOT, "eval")
CACHE = os.path.join(ROOT, "data", "eval_trunc_{}.npy")
WINDOW, STRIDE = 192, 128


def unit(x):
    x = np.asarray(x, dtype=np.float32)
    return x / np.linalg.norm(x, axis=-1, keepdims=True)


def embed_cached(name, texts, ef):
    path = CACHE.format(name)
    if os.path.exists(path):
        return np.load(path), None
    start = time.time()
    vecs = unit(ef(texts))
    np.save(path, vecs)
    return vecs, time.time() - start


def main():
    np.seterr(all="ignore")
    ids = set(get_collection().get(where={"source": ARXIV}, include=[])["ids"])
    with open(DATA_PATH) as f:
        papers = [p for p in (json.loads(line) for line in f) if p["id"] in ids]
    pid_index = {p["id"]: i for i, p in enumerate(papers)}
    tok = Tokenizer.from_file(os.path.expanduser("~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx/tokenizer.json"))
    tok.no_truncation()

    current, chunks, owner, ends = [], [], [], []
    for i, p in enumerate(papers):
        doc = f"{p['title']}. {p['abstract']}"
        current.append(doc)
        if len(tok.encode(doc).ids) <= 256:
            chunks.append(doc)
            owner.append(i)
        else:
            offs = tok.encode(p["abstract"], add_special_tokens=False).offsets
            for s in range(0, max(1, len(offs) - WINDOW + STRIDE), STRIDE):
                window = offs[s : s + WINDOW]
                chunks.append(f"{p['title']}. {p['abstract'][window[0][0] : window[-1][1]]}")
                owner.append(i)
        sents = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", p["abstract"])
        ends.append(f"{p['title']}. {sents[0]}" + (f" {sents[-1]}" if len(sents) > 1 else ""))
    owner = np.array(owner)

    ef = DefaultEmbeddingFunction()
    E_cur, t_cur = embed_cached("current", current, ef)
    E_chk, t_chk = embed_cached("chunks", chunks, ef)
    E_end, t_end = embed_cached("ends", ends, ef)

    with open(os.path.join(HERE, "ideas.json")) as f:
        ideas = json.load(f)
    with open(os.path.join(HERE, "rewrites.json")) as f:
        good = [r["good"] for r in json.load(f)["rewrites"]]
    targets = np.array([pid_index[i["target"]] for i in ideas])
    queries = {"casual": [i["casual"] for i in ideas], "technical": [i["technical"] for i in ideas], "rewrite": good}
    Q = {k: unit(ef(v)) for k, v in queries.items()}

    def paper_dist(E, q, own=None):
        d = 1 - q @ E.T
        if own is None:
            return d
        best = np.full((d.shape[0], len(papers)), np.inf, dtype=np.float32)
        for j in range(d.shape[1]):  # best chunk per paper
            best[:, own[j]] = np.minimum(best[:, own[j]], d[:, j])
        return best

    def score(d):
        r = np.array([1 + int((row < row[t]).sum()) for row, t in zip(d, targets)])
        return f"{(r <= 5).sum()}/30, MRR {np.mean(1 / r):.3f}"

    print(f"items: current {len(current):,}, (a) {len(chunks):,} ({len(chunks) / len(current):.2f}x), (b) {len(ends):,}")
    if t_cur:
        print(f"embedding time: current {t_cur:.0f}s, (a) {t_chk:.0f}s, (b) {t_end:.0f}s")
    chars = lambda xs: sum(len(x) for x in xs) / 1e6  # noqa: E731
    print(f"stored text: current {chars(current):.1f} MB, (a) {chars(chunks):.1f} MB, (b) {chars(ends):.1f} MB; "
          f"vectors: {len(current) * 384 * 4 / 1e6:.1f} MB vs (a) {len(chunks) * 384 * 4 / 1e6:.1f} MB")
    print("\n| query wording | current | (a) best chunk | (b) title + first/last sentence |")
    print("|---|---|---|---|")
    for k in ("casual", "rewrite", "technical"):
        print(f"| {k} | {score(paper_dist(E_cur, Q[k]))} | {score(paper_dist(E_chk, Q[k], owner))} | "
              f"{score(paper_dist(E_end, Q[k]))} |")
    merged = lambda E, own=None: np.minimum(paper_dist(E, Q["casual"], own), paper_dist(E, Q["rewrite"], own))  # noqa: E731
    print(f"| casual + rewrite (app with key) | {score(merged(E_cur))} | {score(merged(E_chk, owner))} | {score(merged(E_end))} |")


if __name__ == "__main__":
    main()
