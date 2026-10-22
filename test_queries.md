# Scratch: "no shared words" test queries

Corpus: 1,944 arXiv abstracts from cs.AR (hardware, incl. FPGA work), cs.CV, cs.LG.
"Shared words" = content words (stopwords removed) that appear in both the query and the paper's title + abstract.
"Keyword rank" = where that paper lands if you rank all 1,944 papers by how many query words they contain.
Measured with `explore.py` style checks on 2026-10-22.

## Chosen

**A. "an AI that keeps adding to what it knows without wiping out earlier lessons"**
| rank | distance | paper | shared words | keyword rank |
|---|---|---|---|---|
| 1 | 0.399 | Self-Activating Neural Ensembles for Continual Reinforcement Learning (2022, cs.LG) | none | 1597 / 1944 |
| 2 | 0.427 | How Do Human Users Teach a Continual Learning Robot in Repeated Interactions? (2023, cs.RO) | none | 1629 / 1944 |

The papers say "continual learning" and "catastrophic forgetting"; the query says neither.

**B. "reprogrammable silicon that runs deep nets faster"**
| rank | distance | paper | shared words | keyword rank |
|---|---|---|---|---|
| 1 | 0.347 | Field-Programmable Gate Array Architecture for Deep Learning: Survey & Future Directions (2024, cs.AR) | "deep" | 501 / 1944 |
| 3 | 0.373 | BARVINN: Arbitrary Precision DNN Accelerator Controlled by a RISC-V CPU (2022, cs.AR, runs on an FPGA) | none | 753 / 1944 |

The papers say "FPGA", "field-programmable", "accelerator"; the query says "reprogrammable silicon". The only overlap, "deep", appears in hundreds of papers.

## Tried and dropped
- "a chip you can reprogram after it's built to make AI models run faster": top hit RHNAS (hardware/NN co-design), FPGA survey only #4.
- "helping a camera see clearly at night": top hit shares "night"; no low-light enhancement papers in the corpus.
- "figuring out how far away things are from a single photo": no depth-estimation papers came back.
- "teaching a robot by letting it watch people do the task": top hit shares "teach" and "robot".
- "doing the math where the data is stored...": returned number-format papers, not processing-in-memory.
- "shrinking a big neural network so it runs on a phone": good results (On-Device Training Under 256KB Memory, 0.497) but shares "neural".

## Distances for reference
- Nonsense queries (lasagna, knitting, taxes, puppies): 0.68-0.84
- Technical descriptions of existing work: 0.27-0.44
- Title -> nearest other paper (calibration, n=300): p25 0.381, p50 0.456, p75 0.518, p95 0.596
