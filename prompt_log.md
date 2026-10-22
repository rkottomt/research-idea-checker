# Prompt Log — HW6: Research Idea Checker

**Tools:** Claude Code (Claude Opus 5.5) in the terminal, used for brainstorming, planning, scaffolding, and code. I review, run, and test everything myself.

---

## 2026-10-21 — Picking an idea

**Prompt 1**
> [pasted the full HW6 assignment page] give me ideas that i can do for this project. after i choose a project, create a github repo, track my prompts accurately, keep the prompt log minimal and add commits to github regularly but do not add yourself as a contributor.

Result: 6 ideas (arXiv novelty checker, movie matcher, ticket triage, quote dedup, history analogies, study tool), each with a "no shared words" test query.

**Prompt 2**
> I like the has someone already done this research idea checker, tell me more about the project

Result: plan for one item per arXiv abstract (title + abstract), metadata for category/year, a novelty score calibrated against nearest-neighbour distances in the corpus, an LLM related-work paragraph that may only cite retrieved papers, and saved ideas that become searchable.

## 2026-10-22 — Setup

**Prompt 3**
> Open the .env file, i have the api key

Result: created `.gitignore` (ignores `.env`, `chroma_store/`, `data/`), `.env` and `.env.example`.

**Prompt 4**
> I am interested in hardware, fpga, computer vision and machine learning. name the repo research-idea-checker

Result: chose arXiv categories cs.AR (hardware, where most FPGA papers live), cs.CV, cs.LG. Drafted candidate test queries in `test_queries.md`. Created the GitHub repo.

**Prompt 5**
> Use rkottomt and then go ahead.

Result: set this repo's git author to my `rkottomt` account (no-reply email) and re-authored the first commit. Created `.venv`, installed `chromadb==1.5.9`, and wrote `smoke_test.py` (PersistentClient + one collection). It ran cleanly and created `chroma_store/chroma.sqlite3`.
Issue hit: `.venv/bin/pip` failed with "bad interpreter" because my folder name `113hw#6` contains `#`, which breaks the script's shebang line. Fix: run `python -m pip` instead.

**Prompt 6**
> Go ahead with all steps until project is completed.

(Steps 3–10 were all driven by this one prompt. Notes per step below.)

- **Step 3 (smoke test):** 12 hand-written items in a persistent collection; a second run in a new process still reports 12. Found that this Chroma version defaults to `l2` for the built-in model, so I set `configuration={"hnsw": {"space": "cosine"}}`. First test query ("making a neural net small enough for a phone") ranked the FPGA item above quantization, and distillation missed the top 3: short plain-English text vs. short jargon text matches weakly.
- **Step 4 (real data):** `fetch_arxiv.py` pulls 45 papers per half-year (2019–2025) from cs.AR, cs.CV, cs.LG, plus 200 FPGA abstracts (arXiv has no FPGA category), deduped to **1,944 papers**. One paper = title + abstract. Timed 50 first (32 papers/s), then loaded all in about a minute. `load.py` skips IDs already stored, so it's safe to re-run.
