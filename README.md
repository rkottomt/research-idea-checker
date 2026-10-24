# Research Idea Checker

**Has someone already done this?** Describe a research idea in plain English. The app finds the closest existing arXiv papers in hardware, FPGA, computer vision, and machine learning, tells you how crowded that area is, and writes a short related-work summary that only cites the papers it actually found.

CMU 15-114 HW6. Python CLI + ChromaDB. Prompt log: [`prompt_log.md`](prompt_log.md).

---

## What it does and why I chose it

The user describes a research idea first and then the app finds all research papers that are similar to the idea and writes a short summary on how crowded the space is. 

## What's stored in the database

The database holds 1,944 arXiv papers from hardware architecture (cs.AR), computer vision (cs.CV) and machine learning (cs.LG), from 2019–2025, plus 200 extra papers that mention FPGAs. Each paper is one item, made of its title and abstract, and isn't split up because each abstract already covers one idea. Each one stores its title, authors, category, year, URL and source, and the same collection also holds the papers you add and the ideas you save while using the app.

## How to add items and how to search

To add a paper, choose 2. Add a paper and paste its arXiv ID or URL, or press Enter to type in a title and abstract yourself; it becomes searchable right away. To search, choose 1. Check an idea, describe your idea in plain English, and optionally filter by category or earliest year (for example cs.AR 2022). The app then shows a novelty verdict, the 5 closest papers and a related-work summary, and lets you save the idea so later checks can remind you of it. The result only shows up if an OpenAI key is set up.

## Two queries a keyword search would miss

Query A: "an AI that keeps adding to what it knows without wiping out earlier lessons" returns Self-Activating Neural Ensembles for Continual Reinforcement Learning (distance 0.399) and How Do Human Users Teach a Continual Learning Robot (0.427). Keyword search would miss both: neither shares a single content word with the query, because they say "continual learning" and "catastrophic forgetting" instead. Keyword search ranks them about 1,600th of 1,944.

Query B: "reprogrammable silicon that runs deep nets faster" returns Field-Programmable Gate Array Architecture for Deep Learning: Survey & Future Directions (0.347) first, and BARVINN, an FPGA accelerator, third (0.373). Keyword search would miss these too. The papers say "FPGA", "field-programmable" and "accelerator" instead of "reprogrammable silicon", so the survey shares only the generic word "deep" and ranks 501st, and BARVINN shares no words and ranks 753rd.

## How I used AI

AI helped with idea generation and seeing what ideas would appeal greatly to my interests. Then it developed the technical implementation after I described the system design. I picked the project and my areas of interest and asked the eval questions. Claude Code brainstormed ideas, designed the code, and ran the tests and the evaluation. OpenAi gpt-5-5.4mini runs inside the app for the query rewrite and the related work summary. 

---

## AI-generated documentation

_Everything below this line was written by Claude Code (Claude Opus 5.5) and checked against the running code._

### Quick start

Requires Python 3.9+ (tested on 3.9.6, macOS).

```bash
git clone https://github.com/rkottomt/research-idea-checker.git
cd research-idea-checker
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

python fetch_arxiv.py   # downloads ~1,944 abstracts to data/papers.jsonl (~3 MB, a few minutes)
python load.py          # embeds them into chroma_store/ (~1 minute) and calibrates the novelty score
python app.py           # the app
```

Optional: `cp .env.example .env` and put an OpenAI key in it to turn on the research-terms rewrite and the related-work summary. Without a key, everything else works: search, novelty verdict, adding papers, saved ideas.

### Getting and loading the data

The raw data is not committed (`data/` and `chroma_store/` are in `.gitignore`).

- **`fetch_arxiv.py`** calls the free [arXiv API](https://info.arxiv.org/help/api/index.html). No key is needed. For each of `cs.AR`, `cs.CV`, `cs.LG` it takes the 45 most recent submissions in each half-year from 2019 to 2025 (42 requests). arXiv has no FPGA category, so it also runs one relevance query, `abs:FPGA AND (cat:cs.AR OR cat:cs.CV OR cat:cs.LG)`, for 200 papers. Duplicates (cross-listed papers) are dropped, leaving **1,944 papers**. Requests are spaced 3 seconds apart, as the arXiv API terms ask. arXiv keeps changing, so a fresh download may differ by a few papers.
- **`load.py`** embeds the papers in batches of 100 (about 30 papers/s on a laptop CPU). `--limit 50` does a timing run. It skips IDs that are already stored, so it's safe to re-run. At the end it calibrates the novelty score (see below).

### Vector database, embedding model, and first-run downloads

| | |
|---|---|
| Vector DB | [ChromaDB](https://docs.trychroma.com/) 1.5.9, `PersistentClient` writing to `./chroma_store/` |
| Distance | cosine, set explicitly: `configuration={"hnsw": {"space": "cosine"}}`. Chroma's default for this model is L2. |
| Embedding model | Chroma's built-in default, `all-MiniLM-L6-v2` (ONNX, runs locally on CPU, 384 dimensions) |
| First run | Chroma downloads the model once (79 MB) to `~/.cache/chroma/onnx_models/` |
| LLM (optional) | OpenAI `gpt-5.4-mini` by default; override with `OPENAI_MODEL` in `.env` |

### Data and metadata

- **One item = one paper.** The embedded document is `"<title>. <abstract>"`. Abstracts are already about one idea each, so papers are not split.
- **Truncation:** the model reads at most 256 tokens. Measured with the model's own tokenizer, 56% of documents are longer (median 268 tokens, max 516), so those lose their last sentence or two, usually experimental results. The title, problem, and method are always read, and those carry the "what is this paper about" signal. I kept one item per paper rather than splitting, because splitting would let one paper fill several of the top-5 slots.
- **Metadata per paper:** `title`, `authors` (first 5), `primary_category`, `year` (int, so it can be filtered with `$gte`), `url`, `source`, `added_at`.
- **`source`** is `arxiv` (loaded corpus), `user_paper` (added in the app), or `user_idea` (a saved idea). Papers and ideas share one collection. Searches for prior work filter with `{"source": {"$ne": "user_idea"}}`, and the "you had a similar idea" check filters with `{"source": "user_idea"}`.

### Using the app

```
--- Research Idea Checker (1944 items) ---
1. Check an idea
2. Add a paper
3. My saved ideas
4. Stats
5. Quit
```

**1. Check an idea.** You type an idea and can add an optional filter such as `cs.AR 2022`, meaning category cs.AR, year ≥ 2022. The filter is an exact metadata match; the meaning matching is done by the vectors. The app then:
1. If an OpenAI key is set, asks the LLM to restate the idea in research terms, and searches with **both** your words and the restatement. Each paper keeps its best distance. Papers that only the restatement found are labelled `(found via research terms)`.
2. Prints a **novelty verdict** (below), the 5 closest papers with distances and links, and which categories and years the related work comes from.
3. Reminds you if a **saved idea** of yours is similar (cosine distance < 0.55).
4. If a key is set and the idea is in scope, has the LLM write **RELATED WORK / CLOSEST MATCH / GAPS** from the retrieved abstracts only. The app parses every `[n]` citation and warns if the model cites a number it was never given.
5. Offers to save the idea, and to export the report to `reports/<idea>.md` (gitignored), ready to paste into a proposal.

**2. Add a paper.** Paste an arXiv ID or URL (`2301.00290`, `arXiv:2301.00290v1`, `https://arxiv.org/pdf/...`). The app fetches it from arXiv and adds it. You can also type in a title and abstract, for example your own draft. It refuses an ID that's already stored, warns if the new text is a near-duplicate (distance < 0.06), and then shows the new paper's 3 nearest neighbours. The paper is searchable immediately.

**3. My saved ideas.** Lists saved ideas with the verdict they got at the time. Pick one to re-check it against the current collection, which may have grown since.

**4. Stats.** Counts by source, category, and year.

### How the novelty score works

Raw distances mean little on their own, so the app calibrates once per load. It takes 300 random paper **titles** and uses each as a short query (ideas are short too), recording the distance to the nearest *other* paper. This gives a picture of how close a typical paper's closest neighbour is in this collection (measured: p25 0.381, median 0.456, p75 0.518, p95 0.596). Your idea's closest distance is then ranked against that distribution:

| Verdict | Rule | Example (measured) |
|---|---|---|
| VERY CLOSE MATCH | closer than ≥ 75% of papers' nearest neighbours | "4-bit quantization of a CNN on an FPGA for real-time object detection" → 0.284 |
| CROWDED | 40–75% | "vision transformer for semantic segmentation" → 0.405 |
| RELATED WORK EXISTS | 10–40% | "shrinking a big neural network so it runs on a phone" (no LLM) → 0.497 |
| LOOKS OPEN (in this collection) | < 10% | "SQL query optimization in databases" → 0.620 |
| OUT OF SCOPE | distance ≥ 0.65 | "blockchain consensus protocols" → 0.720, "lasagna recipe" → 0.790 |

The thresholds come from real measurements (see `explore.py`, `test_queries.md`, and Step 5 of the prompt log). Nonsense queries landed at 0.68–0.84, and the weakest genuine query was at 0.63.

### Known limitations

- **Novelty is relative to ~2,000 papers.** "LOOKS OPEN" means open *in this collection*, not in all of science, and the app says so.
- **Plain English scores as more novel than jargon.** The embedding model doesn't connect everyday words to research terms well. "transferring what a big network knows into a much smaller one" scored LOOKS OPEN with plain vector search, because every distillation paper says "knowledge distillation" and "teacher/student." The research-terms rewrite fixes this case (VERY CLOSE MATCH, 5/5 distillation papers), but only when a key is set.
- **Abstract openings dominate.** Hinton et al.'s *Distilling the Knowledge in a Neural Network* starts by talking about ensembles, so it ranks lower for distillation queries than its title suggests.
- Exact facts (dates, numbers, "not X") belong in metadata filters, not the query.

### Files

| File | Purpose |
|---|---|
| `app.py` | CLI menu: check idea, add paper, saved ideas, stats |
| `db.py` | Chroma client/collection setup, document + metadata format |
| `fetch_arxiv.py` | Download the corpus; also used by the app to fetch one paper by ID |
| `load.py` | Batch-embed the corpus and calibrate |
| `novelty.py` | Calibration and verdicts; all thresholds live here |
| `llm.py` | Optional OpenAI calls: research-terms rewrite and related-work summary |
| `explore.py` | Step 5 exploration: truncation stats, raw results, keyword baseline, distances |
| `smoke_test.py` | Step 3: 12 hand-written items, proves persistence |
| `test_queries.md` | Scratch file: candidate queries, measured results, dropped queries |

### Credits

- Thank you to arXiv for use of its open access interoperability. Paper metadata comes from the [arXiv API](https://info.arxiv.org/help/api/index.html).
- [ChromaDB](https://github.com/chroma-core/chroma) (Apache 2.0) and the [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) model from Sentence Transformers (Apache 2.0).
- OpenAI API for the optional rewrite and summary.
