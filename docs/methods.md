# Methods and provenance

The initial comparison reuses 80 previously scored statements. The independent comparison uses a separate 80 statements from 20 trials. The [data dictionary](data_dictionary.md) lists the cohorts and joins. The [model configuration](../config/models/model_config.json) records quantization, templates and local runtime information. The [weight digests](../config/models/pins.json) identify both model builds. Some historical cached calls have no per-call runtime patch version. The recorded seconds are request times.

| Check | Files |
|---|---|
| Initial label-free statements and reference relations | [Model inputs](../data/processed/initial/confirmation.jsonl) and [reference keys](../data/processed/historical/key.jsonl) |
| Independent inputs and source pointers | [Model inputs](../data/processed/independent/inputs.jsonl) and [reference keys](../data/processed/independent/key.jsonl) |
| Data construction | [Historical constructor](../code/scripts/construction/rebuild.py), [reference counts and checksums](../config/construction_outputs.json), [independent constructor](../code/scripts/independent/construct.py) and [source inventory](notes/reproduction_scope.md) |
| Model service versions | [Evidence by model and method](../config/runtime/version_coverage.json) separates per-call versions, batch snapshots and unknown versions. |
| Procedures and failure attribution | [Original method](../code/src/method.py), [scoring](../code/src/score.py) and [independent scoring](../code/src/independent/holdout_score.py) |
| Boundaries and revisions | [Public scope](../code/results/public_scope.jsonl), [label ledger](../code/results/label_ledger.jsonl), [historical version notes](archive/historical/version_notes.md) |

The full replay reconstructs the 698 screening decisions from registry records and exclusion identifiers. The independent constructor uses that screen, the relevant registry snapshot and archived publication links. It selects 20 trials and produces 40 pairs (80 statements). The public passage analysis retains all 150 sampled statements and identifies the 26 point-shaped statements as a post hoc subgroup.

The [historical technical notes](archive/guide/technical_notes.md) preserve the original method descriptions and limitations. Paths in these notes, in frozen manifests and in raw replies use the original experiment layout. The [path map](../config/file_manifest.tsv) gives their current locations. The root command reconstructs those paths in a temporary directory, runs the frozen scripts and writes the verified outputs back to `code/results/` and `docs/evaluation_index.tsv`. The files under `data/` are read-only inputs to replay.
