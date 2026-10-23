"""Generate and cache LLM rewrites for the evaluation ideas.

Usage:  python eval/make_rewrites.py

Writes eval/rewrites.json with, for each casual idea:
  good    - the app's real research-terms rewrite (llm.research_terms, same prompt as the app)
  drifted - a deliberately bad rewrite: technical-sounding but shifted to a neighbouring problem,
            to simulate the LLM drifting away from what the user meant
Cached so the evaluation is reproducible without an API key.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import llm  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DRIFT_PROMPT = """Restate this research idea in one or two sentences of standard technical terms,
but shift it to a closely related yet clearly different research problem, the way an over-eager
assistant might misread it. Do not name specific papers. Return only the restated idea.

Idea: {idea}"""


def main():
    with open(os.path.join(HERE, "ideas.json")) as f:
        ideas = json.load(f)
    out = []
    for n, idea in enumerate(ideas, 1):
        good = llm.research_terms(idea["casual"])
        drifted = llm._chat([{"role": "user", "content": DRIFT_PROMPT.format(idea=idea["casual"])}])
        out.append({"target": idea["target"], "good": good, "drifted": drifted})
        print(f"[{n}/{len(ideas)}] {idea['casual'][:60]}")
    with open(os.path.join(HERE, "rewrites.json"), "w") as f:
        json.dump({"model": llm.MODEL, "rewrites": out}, f, indent=1)


if __name__ == "__main__":
    main()
