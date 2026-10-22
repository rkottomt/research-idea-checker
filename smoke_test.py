"""Step 3 smoke test: a persistent collection with a dozen hand-written items.

Run it twice. The second run should report the same count without re-adding.
"""
import chromadb

client = chromadb.PersistentClient(path="./chroma_store")  # writes to disk, survives restarts
collection = client.get_or_create_collection(
    name="smoke_test",
    configuration={"hnsw": {"space": "cosine"}},  # default for this embedding model is l2
)

ITEMS = [
    ("cv-1", "cs.CV", "Low-light image enhancement with a lightweight curve estimation network."),
    ("cv-2", "cs.CV", "Monocular depth estimation from a single RGB image using self-supervised training."),
    ("cv-3", "cs.CV", "Real-time object detection for autonomous driving with a single-stage detector."),
    ("cv-4", "cs.CV", "Vision transformers for image classification without convolutions."),
    ("ar-1", "cs.AR", "An FPGA accelerator for convolutional neural network inference with high throughput."),
    ("ar-2", "cs.AR", "A RISC-V vector extension implementation for energy-efficient edge processors."),
    ("ar-3", "cs.AR", "Processing-in-memory architecture that reduces data movement for graph analytics."),
    ("ar-4", "cs.AR", "High-level synthesis flow that maps dataflow programs onto reconfigurable hardware."),
    ("lg-1", "cs.LG", "Post-training quantization of large models to 4-bit weights with minimal accuracy loss."),
    ("lg-2", "cs.LG", "Knowledge distillation transfers a large teacher network into a compact student."),
    ("lg-3", "cs.LG", "Federated learning across mobile devices without sharing raw user data."),
    ("lg-4", "cs.LG", "Reinforcement learning from human feedback for aligning language models."),
]

existing = set(collection.get(ids=[i for i, _, _ in ITEMS])["ids"])
new = [item for item in ITEMS if item[0] not in existing]
if new:
    collection.add(
        ids=[i for i, _, _ in new],
        metadatas=[{"category": c} for _, c, _ in new],
        documents=[d for _, _, d in new],
    )
print(f"added {len(new)} new items; collection now has {collection.count()}")

res = collection.query(query_texts=["making a neural net small enough for a phone"], n_results=3)
for doc, dist in zip(res["documents"][0], res["distances"][0]):
    print(f"  {dist:.3f}  {doc}")
