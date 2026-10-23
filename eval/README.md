# Evaluation

_AI-generated (Claude Code), checked against the scripts' output._

Measured numbers behind the claims in the main README, so they rest on more than one example.

| Script | What it measures | Needs |
|---|---|---|
| `make_rewrites.py` | Caches the app's real LLM rewrites (good) plus deliberately drifted ones for the 30 ideas → `rewrites.json` | OpenAI key (already run; cached) |
| `evaluate.py` | hit@5 by search strategy, robustness to bad rewrites, drift gate, casual vs technical gap → `results.md` | nothing (uses the cache) |
| `corpus_size.py` | How much of arXiv the store covers, and how verdicts change with a 10x larger corpus | arXiv API (cached in `data/` after first run) |
| `truncation.py` | Recall and cost of three ways to handle the 256-token limit | nothing |
| `trend.py` | Whether the store can show a topic "heating up" vs real arXiv counts | arXiv API |

## The test set (`ideas.json`)

- **30 target papers drawn at random** from the store (seed 114, 10 per primary category: cs.AR, cs.CV, cs.LG), not hand-picked. They include dull ones on purpose, like an LDPC decoder and a KL-divergence derivation.
- For each paper there is a **casual** description (how a non-specialist would say it, avoiding the paper's terms) and a **technical** one. A **hit** means the target is in the top k.
- **Caveats:**
  - The descriptions were written by Claude while reading each abstract. The casual ones still share a median of 2 content words with their target (only 3/30 share none).
  - The technical ones are close to paraphrases of the abstract (30/30 hit@5), so treat them as a ceiling, not as typical expert wording.
  - With one target per idea, hit@5 is strict: other genuinely relevant papers can fill the top 5.

## How to rerun

```bash
python eval/evaluate.py      # ~5 s
python eval/truncation.py    # a few minutes the first time (embeds ~7k texts), cached after
python eval/corpus_size.py   # needs arXiv the first time
```

## Truncation options (`truncation.py`, run 2026-10-23)

| | items | embed time* | vectors | hit@5 casual | hit@5 casual + rewrite (app) |
|---|---|---|---|---|---|
| current (cut at 256 tokens) | 1,944 | 96 s | 3.0 MB | 19/30 (MRR 0.540) | 24/30 (MRR 0.769) |
| (a) overlapping chunks, best chunk wins | 3,412 | 169 s | 5.2 MB | 18/30 (MRR 0.546) | 24/30 (MRR 0.761) |
| (b) title + first + last sentence | 1,944 | 95 s | 3.0 MB | 22/30 (MRR 0.531) | 22/30 (MRR 0.642) |

\* Measured while other jobs were running; compare the ratios, not the seconds. Chroma pads every input to 256 tokens, so cost scales with item count, not text length.

## Status

`trend.py` has not produced counts yet: arXiv rate-limited the session (HTTP 429). The store-sampling check in it did run. 1,695 of 1,944 papers (87%) were published in June or December, because `fetch_arxiv.py` takes each half-year's 45 *most recent* submissions.
