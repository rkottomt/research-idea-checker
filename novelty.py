"""Novelty score: how close is the nearest paper, compared with what 'close' normally means here?

Raw cosine distances mean little on their own, so we calibrate once against this collection:
use a sample of paper titles as short queries (ideas are short too) and record each title's
distance to the nearest *other* paper. An idea's nearest distance is then ranked against that
distribution: closer than most papers' own nearest neighbour means the area is well covered.

Thresholds below come from real measurements in explore.py (see prompt_log.md, Step 5).
"""
import json
import os
import random

from db import STORE_PATH, USER_IDEA

CALIBRATION_PATH = os.path.join(STORE_PATH, "calibration.json")
SAMPLE_SIZE = 300
OFF_TOPIC = 0.65       # nonsense queries land at 0.68-0.84; weakest real query seen was 0.63
SIMILAR_IDEA = 0.55    # paraphrased ideas ~0.46, unrelated ideas > 0.9
NEAR_DUPLICATE = 0.06  # edited copy of a paper 0.007; closest two different papers 0.069


def calibrate(collection):
    got = collection.get(where={"source": {"$ne": USER_IDEA}}, include=["metadatas"])
    pairs = list(zip(got["ids"], (m["title"] for m in got["metadatas"])))
    random.seed(0)
    sample = random.sample(pairs, min(SAMPLE_SIZE, len(pairs)))
    res = collection.query(query_texts=[t for _, t in sample], n_results=2,
                           where={"source": {"$ne": USER_IDEA}}, include=["distances"])
    nearest = []
    for (pid, _), ids, dists in zip(sample, res["ids"], res["distances"]):
        others = [d for i, d in zip(ids, dists) if i != pid]
        if others:
            nearest.append(others[0])
    calib = {"nearest_neighbour_distances": sorted(nearest), "collection_size": len(pairs)}
    with open(CALIBRATION_PATH, "w") as f:
        json.dump(calib, f)
    return calib


def load_calibration(collection):
    if os.path.exists(CALIBRATION_PATH):
        with open(CALIBRATION_PATH) as f:
            return json.load(f)
    print("Calibrating novelty scores against this collection (one-time)...")
    return calibrate(collection)


def assess(distance, calib):
    """Turn the distance to the closest paper into a verdict."""
    nn = calib["nearest_neighbour_distances"]
    closer_than = sum(d >= distance for d in nn) / len(nn)
    pct = f"{closer_than:.0%}"
    if distance >= OFF_TOPIC:
        return {"label": "OUT OF SCOPE", "in_scope": False, "closer_than": closer_than,
                "detail": f"The closest paper is {distance:.2f} away, about as far as unrelated text gets. "
                          "This collection doesn't cover the topic, so novelty can't be judged here."}
    if closer_than >= 0.75:
        label, msg = "VERY CLOSE MATCH", "Read [1] before going further: it may already be your idea."
    elif closer_than >= 0.40:
        label, msg = "CROWDED", "Closely related work exists; you'd need a clear angle to stand out."
    elif closer_than >= 0.10:
        label, msg = "RELATED WORK EXISTS", "Neighbouring work exists, but nothing is a direct match."
    else:
        label, msg = "LOOKS OPEN (in this collection)", "Nothing here is close. Only ~2k papers are loaded, so search wider."
    return {"label": label, "in_scope": True, "closer_than": closer_than,
            "detail": f"Your closest match is nearer than {pct} of papers' own nearest neighbours here. {msg}"}
