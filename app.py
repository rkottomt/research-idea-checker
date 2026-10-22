"""Research Idea Checker: has someone already done this?

Usage:  python app.py
"""
import os
import re
import textwrap
from collections import Counter

import llm
import novelty
from db import ROOT, USER_IDEA, USER_PAPER, get_collection, now, paper_record
from fetch_arxiv import fetch_by_id, parse_arxiv_id

TOP_K = 5
PAPERS_ONLY = {"source": {"$ne": USER_IDEA}}
REPORTS_DIR = os.path.join(ROOT, "reports")
WIDTH = 92


def wrap(text, indent="    "):
    return "\n".join(textwrap.fill(line, WIDTH, initial_indent=indent, subsequent_indent=indent) if line else ""
                     for line in text.splitlines())


def ask(prompt):
    try:
        return input(prompt).strip()
    except EOFError:
        return "q"


def search(collection, text, k, where):
    res = collection.query(query_texts=[text], n_results=k, where=where,
                           include=["documents", "metadatas", "distances"])
    return [{"id": i, "document": doc, "distance": dist, **meta}
            for i, doc, meta, dist in zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0])]


def parse_filters(text):
    """'cs.AR 2022' -> exact metadata filter on category and minimum year (vectors do the fuzzy part)."""
    clauses = [PAPERS_ONLY]
    for token in text.split():
        if re.fullmatch(r"[a-z]+\.[A-Z]{2}", token):
            clauses.append({"primary_category": token})
        elif re.fullmatch(r"(19|20)\d\d", token):
            clauses.append({"year": {"$gte": int(token)}})
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def show_papers(papers):
    for n, p in enumerate(papers, 1):
        tag = "  (added by you)" if p["source"] == USER_PAPER else ""
        print(f"  [{n}] {p['distance']:.3f}  {p['title']}{tag}")
        print(f"            {p['primary_category']}, {p['year']}  {p['url']}")


def breakdown(papers):
    cats = Counter(p["primary_category"] for p in papers)
    years = sorted(p["year"] for p in papers)
    cat_str = ", ".join(f"{c} ({n})" for c, n in cats.most_common())
    return f"Where the related work lives: {cat_str}; published {years[0]}-{years[-1]}"


# ---------------------------------------------------------------- 1. check an idea

def check_idea(collection, calib, idea=None):
    idea = idea or ask("\nDescribe your idea in a sentence or two:\n> ")
    if not idea or idea == "q":
        return
    filters = ask("Filter by category and/or earliest year (e.g. 'cs.AR 2022'), or Enter for all: ")
    where = parse_filters(filters)

    papers = search(collection, idea, TOP_K, where)
    if not papers:
        print("No papers match those filters.")
        return
    result = novelty.assess(papers[0]["distance"], calib)

    print(f"\nNovelty: {result['label']}")
    print(wrap(result["detail"]))
    if filters:
        print("    (judged only against papers matching your filters)")
    print("\nClosest prior work (cosine distance, lower = closer):")
    show_papers(papers)
    print("\n" + wrap(breakdown(papers), indent="  "))

    similar_ideas = [i for i in search(collection, idea, 3, {"source": USER_IDEA})
                     if i["distance"] < novelty.SIMILAR_IDEA]
    for past in similar_ideas:
        print(f"\n  You had a similar idea on {past['added_at'][:10]}: \"{past['document']}\"")

    writeup = None
    if result["in_scope"] and llm.available():
        print(f"\nAsking {llm.MODEL} for a related-work summary (it may only cite [1]-[{len(papers)}])...")
        try:
            writeup, invalid = llm.related_work(idea, papers)
            print("\n" + wrap(writeup, indent="  "))
            if invalid:
                print(f"\n  Warning: the summary cites {invalid}, which were not retrieved. Treat it with care.")
        except Exception as e:
            print(f"  LLM step failed ({e}); the ranked papers above are still valid.")
    elif not result["in_scope"]:
        print("\n  Skipping the related-work summary: nothing retrieved is close enough to summarise.")
    else:
        print("\n  (Set OPENAI_API_KEY in .env to also get a related-work summary.)")

    if ask("\nSave this idea to your notebook? [y/N] ").lower() == "y":
        collection.add(ids=[f"idea-{now()}"], documents=[idea], metadatas=[{
            "title": idea[:80], "source": USER_IDEA, "added_at": now(), "verdict": result["label"],
            "closest_paper": papers[0]["title"], "primary_category": "idea", "year": int(now()[:4]), "url": "",
        }])
        print("  Saved. Future checks will remind you of it.")
    if ask("Export this report as Markdown? [y/N] ").lower() == "y":
        print(f"  Wrote {export_report(idea, result, papers, writeup)}")


def export_report(idea, result, papers, writeup):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", idea.lower()).strip("-")[:50]
    path = os.path.join(REPORTS_DIR, f"{slug}.md")
    lines = [f"# Idea check: {idea}", "", f"_Checked {now()[:10]}_", "",
             f"**Novelty:** {result['label']}. {result['detail']}", "", "## Closest prior work", ""]
    lines += [f"{n}. [{p['title']}]({p['url']}) ({p['primary_category']}, {p['year']}), distance {p['distance']:.3f}"
              for n, p in enumerate(papers, 1)]
    if writeup:
        lines += ["", "## Related-work summary (AI-generated from the papers above)", "", writeup]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return os.path.relpath(path, ROOT)


# ---------------------------------------------------------------- 2. add a paper

def read_multiline(prompt):
    print(prompt)
    lines = []
    while True:
        line = ask("")
        if not line or line == "q":
            return " ".join(lines)
        lines.append(line)


def add_paper(collection):
    ref = ask("\nPaste an arXiv ID or URL (or press Enter to type a paper in by hand): ")
    if ref == "q":
        return
    if ref:
        arxiv_id = parse_arxiv_id(ref)
        if not arxiv_id:
            print("  That doesn't look like an arXiv ID.")
            return
        if collection.get(ids=[arxiv_id], include=[])["ids"]:
            print(f"  {arxiv_id} is already in the collection.")
            return
        print(f"  Fetching {arxiv_id} from arXiv...")
        paper = fetch_by_id(arxiv_id)
        if not paper:
            print("  arXiv has no paper with that ID.")
            return
    else:
        title = ask("Title: ")
        abstract = read_multiline("Abstract (paste it, then press Enter on an empty line):")
        if not title or not abstract:
            print("  Need both a title and an abstract.")
            return
        paper = {"id": f"user-{now()}", "title": title, "abstract": abstract, "authors": [],
                 "primary_category": ask("Category, e.g. cs.AR (Enter to skip): ") or "unknown"}

    pid, doc, meta = paper_record(paper, USER_PAPER)
    nearest = search(collection, doc, 1, PAPERS_ONLY)
    if nearest and nearest[0]["distance"] < novelty.NEAR_DUPLICATE:
        print(f"  This looks like a near-duplicate of: {nearest[0]['title']} ({nearest[0]['distance']:.3f})")
        if ask("  Add it anyway? [y/N] ").lower() != "y":
            return
    collection.add(ids=[pid], documents=[doc], metadatas=[meta])
    print(f"  Added \"{meta['title']}\". It's searchable now ({collection.count()} items).")
    print("  Papers most like it:")
    show_papers([p for p in search(collection, doc, 4, PAPERS_ONLY) if p["id"] != pid][:3])


# ---------------------------------------------------------------- 3. saved ideas

def saved_ideas(collection, calib):
    got = collection.get(where={"source": USER_IDEA}, include=["documents", "metadatas"])
    ideas = sorted(zip(got["documents"], got["metadatas"]), key=lambda x: x[1]["added_at"])
    if not ideas:
        print("\n  No saved ideas yet. Check an idea and answer 'y' to save it.")
        return
    print()
    for n, (doc, meta) in enumerate(ideas, 1):
        print(f"  {n}. [{meta['added_at'][:10]}] {doc}")
        print(f"       was: {meta['verdict']}; closest: {meta['closest_paper'][:70]}")
    choice = ask("\nEnter a number to re-check it against the current collection, or Enter to go back: ")
    if choice.isdigit() and 1 <= int(choice) <= len(ideas):
        check_idea(collection, calib, idea=ideas[int(choice) - 1][0])


# ---------------------------------------------------------------- 4. stats

def stats(collection):
    metas = collection.get(include=["metadatas"])["metadatas"]
    sources = Counter(m["source"] for m in metas)
    cats = Counter(m["primary_category"] for m in metas if m["source"] != USER_IDEA)
    years = Counter(m["year"] for m in metas if m["source"] != USER_IDEA)
    print(f"\n  {len(metas)} items: " + ", ".join(f"{n} {s}" for s, n in sources.most_common()))
    print("  top categories: " + ", ".join(f"{c} {n}" for c, n in cats.most_common(6)))
    print("  by year: " + ", ".join(f"{y}: {years[y]}" for y in sorted(years)))


# ---------------------------------------------------------------- menu

def main():
    collection = get_collection()
    if collection.count() == 0:
        print("The database is empty. Run `python fetch_arxiv.py` and then `python load.py` first.")
        return
    calib = novelty.load_calibration(collection)
    actions = {"1": lambda: check_idea(collection, calib), "2": lambda: add_paper(collection),
               "3": lambda: saved_ideas(collection, calib), "4": lambda: stats(collection)}
    while True:
        print(f"\n--- Research Idea Checker ({collection.count()} items) ---")
        print("1. Check an idea\n2. Add a paper\n3. My saved ideas\n4. Stats\n5. Quit")
        choice = ask("Choose an option: ")
        if choice in ("5", "q"):
            break
        if choice in actions:
            actions[choice]()


if __name__ == "__main__":
    main()
