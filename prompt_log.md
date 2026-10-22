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
