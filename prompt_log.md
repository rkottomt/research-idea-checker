# Prompt Log — HW6: Research Idea Checker

**Tools:** Claude Code (Claude Opus 5.5) for planning, code and debugging; OpenAI `gpt-5.4-mini` in the app for query rewriting and related-work summaries; Chroma's built-in `all-MiniLM-L6-v2` for local embeddings.

## 2026-10-21

**Prompt 1**
> give me ideas that i can do for this project. after i choose a project, create a github repo, track my prompts accurately, keep the prompt log minimal and add commits to github regularly but do not add yourself as a contributor.

**Prompt 2**
> I like the has someone already done this research idea checker, tell me more about the project

## 2026-10-22

**Prompt 3**
> Open the .env file, i have the api key

**Prompt 4**
> I am interested in hardware, fpga, computer vision and machine learning. name the repo research-idea-checker

**Prompt 5**
> Use rkottomt and then go ahead.

**Prompt 6**
> Go ahead with all steps until project is completed.

**Prompt 7**
> open the files u need me to edit and also open the prompt log and i will edit that

**Prompt 8**
> answer briefly whats stored in the database

**Prompt 9**
> answer briefly in 2-3 sentences

**Prompt 10**
> how do i add items and how do i search. also answer briefly in 2-3 sentences

**Prompt 11**
> what are two queries a keyword search would miss

**Prompt 12**
> 56% of abstracts get cut at 256 tokens. Compare three options: (a) split each abstract into overlapping chunks and score a paper by its best chunk, (b) embed title + first and last sentences, (c) switch to a longer-context model like bge-small or nomic-embed. Give me the trade-offs in recall, load time and storage. Don’t implement yet.

**Prompt 13**
> Plain-English queries land farther from papers than jargon queries do. Build a small test set: 10 ideas, each written once casually and once technically. Measure the distance gap. Should the thresholds shift when no rewrite is available, or should the verdict just carry a warning?

**Prompt 14**
> “LOOKS OPEN” only means open within 1,944 papers. Estimate how often a verdict would flip if the corpus were 10x larger. Sample 20 ideas, query the live arXiv API for the top hits, and check whether those papers are in our store.

**Prompt 15**
> search_merged currently takes the min distance across both phrasings. Compare that against reciprocal rank fusion and a weighted average. Which is least likely to let a bad rewrite pull in irrelevant papers?

**Prompt 16**
> What happens when the LLM rewrite drifts from the original idea? Propose a check, like rejecting the rewrite if its embedding is farther than X from the original, and pick X from data.

**Prompt 17**
> Is “heating up” meaningful when we sample a fixed 45 papers per half-year? Since equal sampling hides real growth, suggest a way to report trend honestly.

**Prompt 18**
> Should a user’s saved ideas affect the novelty score, or only trigger the “similar idea before” alert? Lay out the arguments, then I’ll decide.

**Prompt 19**
> Design an evaluation: 30 ideas with known prior papers. Report hit@5 for vector-only, rewrite-only and merged search, so the README can show numbers instead of one anecdote.

## 2026-10-23

**Prompt 20**
> is this deployed on vercel?

## 2026-10-24

**Prompt 21**
> is the repo updated

**Prompt 22**
> [pasted the HW6 submission form] give me the answers for this

**Prompt 23**
> open the read me and tell me how to fix it

**Prompt 24**
> add the project to portfolio, remove wiki higher or lower. https://github.com/rkottomt/rkottomt.github.io

## Corrections made during development
- Token-length check was wrong at first because the tokenizer had its own 128-token cutoff. In fact, 56% of abstracts exceed Chroma's 256-token limit.
- Plain vector search rated knowledge distillation as "LOOKS OPEN". Fixed by also searching with an LLM rewrite of the idea in research terms.
- Rewrote `search_merged` so it tracks the set of phrasings that found each paper.
