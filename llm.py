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


def available():
    return bool(os.getenv("OPENAI_API_KEY"))


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
    from openai import OpenAI

    listing = "\n\n".join(
        f"[{i}] ({p['year']}, {p['primary_category']}) {p['document'][:1500]}" for i, p in enumerate(papers, 1)
    )
    resp = OpenAI().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": PROMPT.format(idea=idea, papers=listing)},
        ],
    )
    text = resp.choices[0].message.content.strip()
    invalid = sorted(n for n in cited_numbers(text) if not 1 <= n <= len(papers))
    return text, invalid
