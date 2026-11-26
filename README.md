# When Numbers Agree but Relations Do Not

**Supplementary data and code · v2.2**

This study checks whether a number in a clinical trial statement belongs to the group and outcome it describes. We compare direct model judgments with two ways to check the evidence row. The archive contains the records, prompts, original replies and scoring code used in the paper.

## Find the evidence for a result

| Paper | File to open | What to look for |
|---|---|---|
| Table 2, initial trials | [Method comparison](code/results/metrics.csv) | Read `fixed` and `lost` together. Relative to Direct, Joint with fallback gained 2 correct judgments for Qwen and 0 for Llama across 80 statements. |
| Table 2, independent trials | [Method comparison](code/results/independent_metrics.json) | Across a separate 80 statements, selection with fallback changed the correct counts from 52 to 58 for Qwen and from 49 to 72 for Llama. |
| Table 3, failure stages | [Stage counts](code/results/failure.json) | `original_first` and `selection_stage` each count a statement once. `offline_differences` can count a statement more than once. |
| Section 7, example judgments | [Trial and statement index](docs/review/statements.html) | Search a trial ID. Each statement links to its source excerpt and both models’ original replies. |

The [offline review page](docs/review/index.html) displays the tables and the two examples discussed in the paper. The [data dictionary](docs/data_dictionary.md) explains the labels, identifiers and denominators.

The [anonymous paper](docs/papers/paper.pdf) gives the table definitions. The [reproduction notes](docs/notes/reproduction_scope.md) identify which data are reconstructed and which are supplied as frozen inputs.

## Run the analysis

Extract the full ZIP. In a terminal, go to the folder containing this README and run the following command. Python 3.10 or later and a CPU are sufficient. All scoring dependencies are part of the Python standard library. [Environment requirements](code/requirements.txt)

```sh
python --version
python reproduce.py
```

The command verifies the archived inputs and replies, regenerates 25 result files in `code/results/` and writes the 320-row [statement–model index](docs/evaluation_index.tsv). The last line starts with `Verified 25 result files`. To also reconstruct the independent cohort of 20 trials from the archived screening decisions, use this command instead.

```sh
python reproduce.py --cohort
```

For a check starting from the archived registry and public benchmark snapshots, run:

```sh
python reproduce.py --all-data
```

This regenerates the historical partitions and the independent cohort, checks their contents against the frozen references, and uses the regenerated inputs for scoring the original model replies. It needs no network connection or model weights. To inspect the 13 historical JSONL outputs, run `python code/scripts/construction/rebuild.py rebuilt_partitions` from the archive root. Choose a new destination name.

## Where the files live

| Directory | Contents |
|---|---|
| `data/raw/` | Historical registry and publication records, source evidence, and model requests and replies. Replay reads these as inputs. |
| `data/processed/` | Statements presented to the models, answer keys, source-row references, screening decisions and earlier evaluation records. Label-free inputs and answer keys are separate files. |
| `code/src/` | Frozen selection, matching and scoring methods, including the original parsers. |
| `code/scripts/` | Scripts for constructing cohorts, auditing sources and producing tables. The root command runs the relevant scripts together. |
| `code/results/` | Generated tables, metrics, predictions and error analyses. |
| `config/` | Model settings, digests and freeze manifests. The [file manifest](config/file_manifest.tsv) maps historical paths in receipts to their locations in this archive. |
| `docs/` | Data dictionary, revision notes, review pages and material-specific documentation. |

## Data preparation and troubleshooting

The study used pretrained models for inference; offline replay requires no training step. The [runtime inventory](config/runtime/version_coverage.json) distinguishes versions recorded per call from versions documented only by a batch snapshot or missing from the historical record.

The frozen statement inputs are ready to score. Development and initial inputs are in `data/processed/initial/`, independent inputs are in `data/processed/independent/`, and the public input sample is in `data/processed/historical/public.jsonl`. The original prompts and replies are included under `data/raw/model_replies/`. Replaying them works offline. Generating new replies requires a local model runtime and the weight digests listed in [model configuration](config/models/model_config.json).

If Python cannot find `reproduce.py`, run the command from the folder containing `README.md`. If a file differs from its frozen hash, extract a fresh copy of the archive and rerun. To resolve an old path quoted in a raw reply or a historical note, look it up in the first column of `config/file_manifest.tsv`. Original source and public-dataset terms continue to apply.

## Review correspondence

During anonymous review, please send questions through the submission system. Include the table number or statement ID so the authors can identify the relevant evidence.
