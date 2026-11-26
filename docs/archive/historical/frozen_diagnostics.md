# Supplementary diagnostics

The statement is the counting unit. Each model saw the same items. These tables describe the frozen evaluations.

## Public passages

The five descriptions refer to the wording of each statement. The coding used the statement text after the earlier aggregate results were known. Invalid claim and invalid source counts overlap. Each statement that passed validation and completeness checks reached the matcher. Neither model found a compatible record on any of these inputs.

| Model | Statement type | N | Invalid claim | Invalid source | Invalid on both | Incomplete after validation | Reached matching | Definite |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen | point-shaped | 26 | 19 | 14 | 8 | 1 | 0 | 0 |
| Qwen | comparison/arithmetic | 50 | 48 | 40 | 38 | 0 | 0 | 0 |
| Qwen | negation | 11 | 11 | 2 | 2 | 0 | 0 | 0 |
| Qwen | mixed assertion | 56 | 52 | 28 | 27 | 2 | 1 | 0 |
| Qwen | other | 7 | 7 | 2 | 2 | 0 | 0 | 0 |
| Qwen | All | 150 | 137 | 86 | 77 | 3 | 1 | 0 |
| Llama | point-shaped | 26 | 22 | 7 | 7 | 0 | 4 | 0 |
| Llama | comparison/arithmetic | 50 | 46 | 14 | 14 | 0 | 4 | 0 |
| Llama | negation | 11 | 11 | 2 | 2 | 0 | 0 | 0 |
| Llama | mixed assertion | 56 | 54 | 21 | 21 | 0 | 2 | 0 |
| Llama | other | 7 | 7 | 6 | 6 | 0 | 0 | 0 |
| Llama | All | 150 | 140 | 50 | 50 | 0 | 10 | 0 |

## Condition values on the 80 confirmation statements

Both rules use the same predicted records, header inheritance and field-presence requirements. Joint checks the condition values. The ablation ignores a populated condition's value. Correct counts include only decisions matching the reference label. FP counts a consistent statement labeled mismatch.

| Model | Pair type | Statements | Joint correct | Joint answered | Joint FP | Ablation correct | Ablation answered | Ablation FP |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen | category | 42 | 6 | 6 | 0 | 0 | 0 | 0 |
| Qwen | group | 28 | 5 | 5 | 0 | 5 | 5 | 0 |
| Qwen | endpoint | 10 | 2 | 2 | 0 | 2 | 2 | 0 |
| Llama | category | 42 | 0 | 0 | 0 | 0 | 0 | 0 |
| Llama | group | 28 | 1 | 1 | 0 | 1 | 2 | 1 |
| Llama | endpoint | 10 | 2 | 2 | 0 | 2 | 2 | 0 |

The scored ablation is reconstructed by `score_release.py` using `score_v2.nocond`. The preliminary `no_conditions` field in the inference log ignores field presence as well. The two versions differ on one Llama confirmation statement. The published comparison uses the scored decisions in `analysis_results/decisions.jsonl`.

## Shared records for the decision-stage comparison

Among the 13 statements that Qwen Joint decided, Record-LLM classified 12 correctly and one incorrectly. Among the three that Llama Joint decided, Record-LLM gave one correct answer, one incorrect answer and one abstention. On the remaining inputs that passed extraction, the respective Record-LLM counts (correct, incorrect, abstained) were (19, 9, 0) and (19, 14, 18).

## Numeric quotation checks

All main tables use the version frozen before confirmation. It excludes bounds written as `>=5` and intervals written as `3 to 5`. In a separate diagnostic it accepted a digit from `5 or more` and either endpoint of `between 3 and 5`. The extension in `numeric_check/` rejects these forms. Seven examples test bounds, signed endpoints and true point values. On the archived model outputs the extended check recovered the same accepted records and errors for all 1,316 claim validations and 300 source validations. The source parser for headed tables reads the value cell directly. The diagnostic concerns these specified expressions.

To reproduce the sensitivity check from the project directory, pass the path to the accompanying replication archive after extracting it.

```text
python supplement/numeric_check/replay_bounds.py PATH_TO_EXTRACTED_REPLICATION_ARCHIVE
```

## Checks for shared publications

The AACT reference snapshot dated 16 November 2026 contained at least one PMID or DOI for nine of the 20 confirmation trials and 75 of the 143 distinct trials in earlier partitions and ancillary probes. The two groups shared no trial ID, PMID or DOI in this check. Trials without a linked publication cannot be compared on that basis.

## A second direct judgment on the confirmation statements

After the confirmation outcomes were known, we applied the existing series B second-pass prompt to all 80 statements with both original model versions. The original inputs and judgments were kept. For each model, the first 80 Direct responses were reused and 80 new second-pass responses were obtained. Fusion and two-pass Direct each cost 160 logical calls. Neither model abstained on the second pass. Compared with two-pass Direct, Fusion gained 11 correct answers and lost seven on Qwen. On Llama it gained one and lost one. Clustered accuracy differences are reported in §7.5. The experiment matches call count. Tokens, elapsed time and the information available inside each second call differ.

`matched_calls/` includes the protocol and its request hash, the inputs, the raw responses, the frozen scoring references, the model digests, and the scripts `run_control.py` and `score.py`. From the project root, `python supplement/matched_calls/score.py` scores the cached responses using NumPy. `python supplement/matched_calls/run_control.py supplement/matched_calls` verifies the request archive without model calls. The scoring reference was never submitted to the model.

## Earlier registry series

### Series A

 From 300 registry candidates in first-posted order, we screened known trial IDs, secondary identifiers and linked PMIDs. A fixed hash order selected 20 trials, including mixed-tumor and pancreatic pseudocyst studies. Two targets per trial yielded 20 group-, three endpoint- and 17 condition-swap pairs. Within each pair, only the claimed point value changed. We froze IDs, code, prompts and fusion before inference. A later AACT citation check (16 November 2026) found no shared PMID, DOI or normalized citation across the partitions checked. Reference coverage was 11/20 development, 21/40 retrospective, 7/20 first-series and 15/30 public trials.

### Scoped denominators and series B

 In a second rendering we separate the outcome arm size from an explicitly listed subgroup size. We map an ordered vector of counts only if its length and the order of measured groups match the registry arm list. For an individual scan result we retain the cohort size but identify the estimate as per participant. This revision changed six development statements and eight in series A. All 226 retrospective inputs were identical across these two renderings.

With the amended renderer fixed, a query capped at 500 studies returned 467 in results-posting order. We screened these in fixed hash order, excluding earlier candidates and matches on trial IDs, secondary identifiers or publication keys. Each selected trial had a registry citation tagged RESULT or DERIVED. Such tags sometimes refer to background material. Twenty trials yielded 40 pairs (21 group, five endpoint and 14 condition). Inputs, prompts, matching and fusion were frozen before inference. Unindexed publications and patient overlap remain possible.

## Source pointers, final wording and support decisions

`evidence_review/source_checks.jsonl` contains one entry for each of the 344 original development and retrospective statements. It gives both source pointers, the enrollment count, the outcome, class and category denominator fields for the target and donor, and the denominators and values actually shown. The retrospective input hashes match the scoring ledger for both models on all 226 statements. The earlier audit ledger's rendered-denominator column preceded the last wording update for four retrospective statements. Use `final_claim_denominator` for the wording given to the methods. The update to the ledger changes no model input or reference label.

In six development statements, the group-specific count written in the category heading qualifies the outcome-arm count. In two VIRAGE statements the sponsor's median response durations of 11.2 and 5.4 months identify the corresponding counts of 19 and 15. In two TRYBECA-1 statements the final wording identifies the 257 participants as the outcome-arm size and explicitly leaves the responder count unspecified. The two TRYBECA-1 pairs in the sensitivity analysis include a pair in which the duration comes from the donor. Equivalence of denominators across these endpoints remains unresolved.

`evidence_review/validated_relations.jsonl` compares every validation-passing extraction on the confirmation set to the source-based relation. The comparison uses the number of relations, normalized field values, decimal point values and the frozen header inheritance rule. `public_types.jsonl` records the 150 fixed wording assignments with claim hashes. The coding was performed after earlier aggregate results were available. `medscore_support.jsonl` crosses both reference labels with the three support outcomes on each reported set. Unsupported includes insufficient evidence.

To reproduce the files, extract the frozen replication package and run `python supplement/evidence_review/check.py REPLICATION_DIRECTORY VIRAGE_SPONSOR_HTML OUTPUT_DIRECTORY` with NumPy installed. The checker verifies the sponsor snapshot against the SHA-256 in `source_evidence/sources.json`. The results can also be inspected directly in the four JSONL files.

## Trial examples and the earlier two-call control

The APACT registry groups several percentiles under a median heading. The wording check names the row labeled 75th percentile. At five-year follow-up, the APACT paper cited in the manuscript reports median overall survival of 41.8 months with nab-paclitaxel plus gemcitabine and 37.7 months with gemcitabine alone. A separate PET endpoint in NCT03914950 has an ambiguous registry unit.

On the 80 series B statements, two-pass Direct used 155,655 tokens for Qwen and 148,657 for Llama. Fusion used 125,598 and 122,449 tokens, respectively. Each used 160 logical calls per model.

## Additional condition test

See `condition_extension/` for the ten items, the two model families, raw field counts, and trial-index sensitivity. The numeric quotation checks described earlier were a post-confirmation diagnostic at the time. They now run in the released verifier. Further inference used the new implementation. The original 80 statements retain their original frozen status.
