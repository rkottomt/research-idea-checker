# Prompt Log — HW6: Research Idea Checker

**Tools:**
- **Claude Code (Claude Opus 5.5)** in the terminal for brainstorming, planning, code, debugging, and the AI-generated part of the README. It could run the app and inspect the installed Chroma version directly, which mattered because Chroma's API changes between versions.
- **OpenAI `gpt-5.4-mini`** inside the app for the research-terms rewrite and the related-work summary. It's cheap, fast, and covered by the course's OpenAI credits.
- **Chroma's built-in `all-MiniLM-L6-v2`** for embeddings. It's free, runs locally, and needs no key, so graders can run the app.

**Where the AI got it wrong / needed correcting:**
- The first truncation check reported every document as exactly 128 tokens. The tokenizer file has its own 128-token cutoff, so the "untruncated" count was still truncated. The real figure is 56% of docs over 256.
- Plain vector search called a crowded area (knowledge distillation) "LOOKS OPEN". Found by testing, fixed with the research-terms rewrite.
- The first version of `search_merged` had tangled logic for tracking which phrasing found a paper. Rewritten to track a set per paper.

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
- **Step 5 (look at results):** results are lists of lists; distances for real matches were 0.27–0.63, nonsense 0.68–0.84. My first truncation check said every doc was exactly 128 tokens, which was wrong: `tokenizer.json` ships with its own 128 cutoff. After `no_truncation()`: 56% of docs exceed Chroma's 256-token limit (median 268), so they lose their last sentences (usually results). Kept one item per paper. Added a keyword-search baseline to prove the test queries; chosen queries and dropped ones are in `test_queries.md`. Novelty score = rank of the idea's nearest distance among titles' nearest-neighbour distances. Thresholds from measurements: off-topic 0.65, similar idea 0.55, near-duplicate 0.06. Plain-English ideas score as more novel than technical ones (limitation).
- **Steps 6–8 (add at runtime, use the results, CLI):** menu with check idea / add paper / saved ideas / stats. Add by arXiv ID or URL (caught re-adding the same ID), or type a paper in by hand (near-duplicate warning fired at 0.000 on a pasted copy). New items are searchable immediately and the app shows their nearest papers. Idea check = novelty verdict + ranked papers + category/year breakdown + "you had a similar idea" + LLM related-work summary (citations checked against what was retrieved) + save idea / export Markdown.
  Problem found: plain-English "transferring what a big network knows into a much smaller one" got LOOKS OPEN and missed every distillation paper (Hinton's paper ranked 26th); the technical phrasing found them at 0.36. Fix: when a key is set, the LLM restates the idea in research terms and the app searches with both phrasings, labelling papers found only by the rewrite. Same query then: VERY CLOSE MATCH, 5/5 distillation papers. The README test queries still use plain vector search only.
  Also: used random IDs for saved ideas and typed-in papers (Chroma silently drops a duplicate ID), and stopped a re-checked idea from matching itself. Cleared my test entries afterwards.
- **Step 9 (prove the claim):** ran both test queries through the finished app with no API key (pure vector search, so the LLM can't add keywords). Both worked; results in `test_queries.md`. Full add → search → quit → relaunch flow kept everything.
- **Step 10 (docs):** README with my own sections left as TODOs (the spec says I must write the first four items myself) and an AI-generated section below them, checked against the code. Tested the README's setup steps on a fresh clone: install, "database is empty" message, load in 62 s, same query results.

## Still to do (me)
- [ ] Write the TODO sections of the README in my own words
- [ ] Record the video: add a paper (e.g. `1503.02531`), check query A or B, show the verdict + summary
- [ ] Portfolio entry, Google form
