# Data dictionary

## Cohorts and files

| Cohort | Units | Inputs | Reference and freeze records |
|---|---|---|---|
| Fixed development round | 20 statements from 20 trials, one selector reply per statement per model | `data/dev.jsonl` | `data/dev_key.jsonl`, `freeze.json` |
| Initial Table 2 cohort | 80 statements, 40 pairs, 20 trials. The selection comparison on these previously scored statements was post hoc. | `data/confirmation.jsonl` | `historical/key.jsonl`, `historical/main_freeze.json`, `freeze.json` |
| Independent Table 2 cohort | 80 statements, 40 pairs, 20 previously unscored trials. Each model ran Direct and Select once per statement. | `independent/inputs.jsonl` | `independent/key.jsonl`, `independent/freeze.json`, `independent/screen.json` |
| Public Results passages | All 150 sampled NLI4CT-P statements. The 26 point-shaped statements form a post hoc subgroup. | `historical/public.jsonl` | Supplied `gold` label and `source_url` on each row, `historical/public_types.jsonl` |
| Original registry construction | 172 pairs, 344 statements across the original development and retrospective partitions | `historical/source_audit_172_pairs.jsonl` contains amended statements, evidence and source pointers | `historical/source_checks.jsonl`, `results/label_ledger.jsonl` |

## Joining files

JSONL contains one JSON object per line. CSV and TSV files have headers. Use `id` for a statement within a cohort. Use `cohort`, `model` and `id` for joins across the review index, and add `method` for a prediction. `trial` is the registry ID and the unit of paired resampling. `pair` groups the original statement and its numerical variant. The initial predictions store `qwen2.5_7b` and `llama3.1_8b` in `model`. The independent predictions store `qwen2.5:7b` and `llama3.1:8b`. The index retains each cohort's spelling.

In a key file, `target` is the registry row described by the statement. `donor` supplies the alternative value used to construct its paired mismatch. `json_pointer` locates the measurement in the corresponding registry study. On the independent set the full study JSON is available in `independent/registry/`. Historical inputs, raw target/donor fields, source checks and source pointers are supplied at the paths above. Source and dataset terms continue to apply. For independent cohort construction, `cohort_source/screen.jsonl` contains one archived decision per screened study, including exclusions. `cohort_source/studies.json` contains the full registry snapshots for the 78 candidates and identification and publication-reference metadata where available for the remaining 620 studies. The earlier trial and publication lists supply the exclusions used before selection. `python cohort_source/rebuild.py` rebuilds the independent cohort starting with these screening decisions.

## Predictions and costs

| Field | Meaning |
|---|---|
| `gold` | Reference label from the constructed pair or the public dataset. |
| `prediction` | Method verdict. `consistent` and `mismatch` are definite. `unclear` is an abstention. |
| `direct` | The Direct verdict on the same statement and model. The fallback uses this value when its verifier abstains. |
| `returned_ids`, `compatible_ids` | Row IDs returned by the selector and reference-compatible rows for offline scoring. The first parsed row has ID 1. In model replies 0 denotes no match and −1 denotes ambiguity. |
| `answered`, `correct`, `wrong` | Counts of definite answers, correct verdicts and wrong definite answers. Full-sample accuracy includes abstentions in its denominator. |
| `fixed`, `lost`, `net` | Changes in correctness relative to Direct on the same items. For standalone methods, a change from correct to abstention counts as a loss in full-sample accuracy. |
| `calls`, `tokens`, `seconds` | Accounted model calls, input plus output tokens, and summed logged request seconds. Cached calls span different runtime versions and loads. |

## Tracing the examples

Filter `guide/evaluation_index.tsv` to `independent`, then search `NCT03490760` for the Qwen denominator example or `NCT05070247` for the Llama wrong-row pair. The `select_reply` and `direct_reply` columns point to the individual receipts, including the exact request and response. In `results/independent_rows.jsonl`, join by model and statement ID to compare the returned and compatible row IDs with the final verdict. In the initial cohort the corresponding file is `results/audit.jsonl`.
