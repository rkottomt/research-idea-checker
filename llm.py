"""Optional LLM step: turn the retrieved papers into a short related-work write-up.

Needs OPENAI_API_KEY in .env (see .env.example). Without it the app skips this step.
"""
import os
import re

from dotenv import load_dotenv

from db import ROOT

load_dotenv(os.path.join(ROOT, ".env"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

SYSTEM = """You help a researcher check whether their idea has already been done.
You get their idea and numbered papers retrieved from a small local collection of arXiv abstracts.
Rules:
- Use only the numbered papers. Cite them as [1], [2], ... Never mention any other paper.
- If a listed paper is not actually related to the idea, leave it out. If none are related, say so plainly.
- Be concrete and brief. Plain text only, no markdown."""

PROMPT = """Idea: {idea}

Retrieved papers:
{papers}

Write three short sections with exactly these labels:
RELATED WORK: 3-5 sentences on how the listed papers approach this idea, with citations.
CLOSEST MATCH: the single closest paper and how the idea differs from it (1-2 sentences).
GAPS: 2-3 lines starting with "- ", each an angle the idea could take that the listed papers do not cover."""


REWRITE_PROMPT = """Restate this research idea in one or two sentences using the standard technical
terms a paper abstract on the topic would use. Do not name specific papers, authors, or results.
Return only the restated idea.

Idea: {idea}"""


def available():
    return bool(os.getenv("OPENAI_API_KEY"))


def _chat(messages):
    from openai import OpenAI

    resp = OpenAI().chat.completions.create(model=MODEL, messages=messages)
    return resp.choices[0].message.content.strip()


def research_terms(idea):
    """Plain-English ideas embed far from jargon-heavy abstracts, so also search with a technical restatement."""
    return _chat([{"role": "user", "content": REWRITE_PROMPT.format(idea=idea)}])


def cited_numbers(text):
    """All numbers cited as [n] or [n, m] in the text."""
    nums = set()
    for group in re.findall(r"\[(\d+(?:\s*,\s*\d+)*)\]", text):
        nums.update(int(n) for n in group.split(","))
    return nums


def related_work(idea, papers):
    """papers: list of dicts with title, year, primary_category, document.

    Returns (text, invalid_citations). invalid_citations lists any [n] that points
    outside the papers we actually gave the model.
    """
    listing = "\n\n".join(
        f"[{i}] ({p['year']}, {p['primary_category']}) {p['document'][:1500]}" for i, p in enumerate(papers, 1)
    )
    text = _chat([
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": PROMPT.format(idea=idea, papers=listing)},
    ])
    invalid = sorted(n for n in cited_numbers(text) if not 1 <= n <= len(papers))
    return text, invalid
