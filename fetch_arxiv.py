"""Download arXiv abstracts into data/papers.jsonl (one paper per line).

Usage:  python fetch_arxiv.py

Also used by app.py to look up a single paper by its arXiv ID.
The arXiv API asks for at most one request every 3 seconds.
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

API = "https://export.arxiv.org/api/query"
NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
OUT_PATH = os.path.join("data", "papers.jsonl")

CATEGORIES = ["cs.AR", "cs.CV", "cs.LG"]  # hardware architecture, computer vision, machine learning
YEARS = range(2019, 2026)
PER_HALF_YEAR = 45  # papers per category per half-year window
# arXiv has no FPGA category, so pull FPGA papers from these categories explicitly.
EXTRA_QUERIES = [("abs:FPGA AND (cat:cs.AR OR cat:cs.CV OR cat:cs.LG)", 200)]


def _clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _parse_entry(entry):
    raw_id = entry.findtext("a:id", namespaces=NS)
    summary = entry.findtext("a:summary", namespaces=NS)
    if not raw_id or "/abs/" not in raw_id or not summary:
        return None  # error entries have no abstract
    arxiv_id = re.sub(r"v\d+$", "", raw_id.split("/abs/")[1])
    published = entry.findtext("a:published", namespaces=NS)[:10]
    primary = entry.find("arxiv:primary_category", NS)
    return {
        "id": arxiv_id,
        "title": _clean(entry.findtext("a:title", namespaces=NS)),
        "abstract": _clean(summary),
        "authors": [_clean(a.findtext("a:name", namespaces=NS)) for a in entry.findall("a:author", NS)],
        "primary_category": primary.get("term") if primary is not None else "",
        "categories": [c.get("term") for c in entry.findall("a:category", NS)],
        "published": published,
        "year": int(published[:4]),
        "url": f"https://arxiv.org/abs/{arxiv_id}",
    }


def _request(params, retries=3):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "research-idea-checker (CMU 15-114 homework)"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                root = ET.fromstring(resp.read())
            return [p for p in (_parse_entry(e) for e in root.findall("a:entry", NS)) if p]
        except Exception as e:  # network hiccups and arXiv's occasional 503s
            if attempt == retries - 1:
                raise
            print(f"  request failed ({e}); retrying in 5s")
            time.sleep(5)


def search(query, max_results, sort_by="submittedDate"):
    return _request({"search_query": query, "start": 0, "max_results": max_results,
                     "sortBy": sort_by, "sortOrder": "descending"})


def parse_arxiv_id(text):
    """Pull an arXiv ID out of an ID, 'arXiv:...' string, or abs/pdf URL."""
    m = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", text) or re.search(r"([a-z\-]+(?:\.[A-Z]{2})?/\d{7})", text)
    return m.group(1) if m else None


def fetch_by_id(arxiv_id):
    papers = _request({"id_list": arxiv_id, "max_results": 1})
    return papers[0] if papers else None


def build_plan():
    plan = []
    for cat in CATEGORIES:
        for year in YEARS:
            for start, end in [("0101", "0630"), ("0701", "1231")]:
                q = f"cat:{cat} AND submittedDate:[{year}{start}0000 TO {year}{end}2359]"
                plan.append((q, PER_HALF_YEAR, "submittedDate"))
    plan += [(q, n, "relevance") for q, n in EXTRA_QUERIES]
    return plan


def main():
    os.makedirs("data", exist_ok=True)
    papers = {}
    plan = build_plan()
    for i, (query, n, sort_by) in enumerate(plan, 1):
        batch = search(query, n, sort_by)
        new = 0
        for p in batch:
            if p["id"] not in papers:
                papers[p["id"]] = p
                new += 1
        print(f"[{i}/{len(plan)}] {query[:60]:<60} got {len(batch):>3}, new {new:>3}, total {len(papers)}")
        time.sleep(3)  # arXiv API etiquette
    with open(OUT_PATH, "w") as f:
        for p in papers.values():
            f.write(json.dumps(p) + "\n")
    print(f"wrote {len(papers)} papers to {OUT_PATH}")


if __name__ == "__main__":
    main()
