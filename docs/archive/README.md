# Code and data for *When Numbers Agree but Relations Do Not*

This supplement accompanies the experiments on numerical claims in clinical trial results. Start with the table below to inspect a finding, or use the command to rebuild the results. Paths are relative to the extracted archive.

## Reproduce Tables 2 and 3

Extract the whole ZIP into one folder. Open a terminal in the folder containing this README and run the following with Python 3.10 or later. The replay uses the Python standard library and the archived model replies. It runs offline on a CPU.

```sh
python reproduce.py
```

A successful run ends with `Verified both cohorts and regenerated the paper tables and individual predictions.` The script writes 25 files to `results/` and checks their hashes against `expected.json`. The included results are available for immediate inspection. To check a clean rebuild, extract a fresh copy, move its `results/` directory aside and run the same command. Optional new inference and the provenance of the source snapshots are described in the [technical notes](guide/technical_notes.md).

## Rebuild the independent cohort

From the same folder, run the following to check cohort construction against the frozen inputs.

```sh
python cohort_source/rebuild.py
```

The script starts with 698 archived screening decisions, reconstructs the pool of 78 candidates, and selects the independent trials using the frozen constructor. It checks the 20 selected registry snapshots, 40 statement pairs, 80 inputs and reference labels, exclusions, and publication links. It runs offline in a temporary directory. Running it after `reproduce.py` also checks the publication links against the regenerated source audit.

To regenerate the 320-row lookup index after scoring, run `python guide/build_index.py`.

## Find a result in the paper

| Paper result | Data or output to open | Code or supporting evidence |
|---|---|---|
| Table 2, initial 80 statements | [All methods and metrics](results/metrics.csv) and [1,440 item–method predictions](results/predictions.csv) | `score.py`, `tables.py`. The table includes the separately rendered independent rows. |
| Table 2, independent 80 statements | [Metrics](results/independent_metrics.json) and [640 item–method predictions](results/independent_predictions.csv) | `independent/holdout_score.py`, `independent/render_holdout.py`. The fourth method in the CSV is the secondary ambiguity-priority replay. |
| Table 3, first failure in each procedure | [First stages and row IDs for each statement and model](results/audit.jsonl), [stage totals](results/failure.json) and [typeset table](results/stages.tex) | `score.py`, `tables.py`. `audit_counts.py` reports overlapping reference-based field errors separately in `results/paper_counts.json`. |
| Section 7.2, conditions and validation order | [160 paired judgments with and without condition values](results/condition_ablation.jsonl) and [validation-order summary](results/validation_order_summary.json) | `condition_ablation.py`, `validation_order.py`. `results/validation_order_items.jsonl` records all 360 selector replies. |
| Section 7, examples from the two cohorts | [Initial examples](results/cases.json) and [independent row diagnoses](results/independent_rows.jsonl) | Search the [evaluation index](guide/evaluation_index.tsv) by statement ID or trial ID to locate the actual Direct and Select replies. |
| Section 7.3, public scope and label sensitivity | [150 public statements](historical/public.jsonl), [26 point-shaped claims](results/public_scope.jsonl), [label ledger](results/label_ledger.jsonl) and [sensitivity results](results/sensitivity.json) | `boundaries.py`. `historical/frozen_diagnostics.md` records the separate claim and passage failure counts. |
| Table 1, cohort provenance and source checks | [Original registry source audit](historical/source_audit_172_pairs.jsonl) and [independent source audit](results/independent_source_audit.json) | `independent/verify_sources.py`, `historical/source_evidence/`, `independent/registry/`. |

The [data dictionary](guide/data_dictionary.md) describes the cohorts, labels, scoring units and model identifiers. The [evaluation index](guide/evaluation_index.tsv) has one row per statement and model in the two Table 2 cohorts. It is a lookup aid for reviewing completed predictions. Only the label-free inputs enter the selector. [Technical notes](guide/technical_notes.md) document the models, prompts, frozen code, source terms and known limitations.
