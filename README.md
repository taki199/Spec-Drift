# Spec-drift detection — Research Project I pilot data

Data and scoring code for the pilots in the Research Project I report *Automated Spec-Drift Detection in Multi-Agent Development Pipelines* (Houcine Taki, Vytautas Magnus University, 2026).

## Contents

| Path | What it is |
| --- | --- |
| `answer_key/cases.json` | Pilot B dataset: 104 Flask implementations built from 18 APIs.guru OpenAPI specifications (18 controls, 86 with one injected drift). Each case holds the specification operations (`spec_ops`), the source code, the ground truth (`gt`), the drift type (`kind`), and the stored predictions of the rule-based (`rule`) and test-based (`test`) detectors. |
| `answer_key/judge.py` | LLM-as-a-judge script (Anthropic API) and the scorer. `--report` computes precision, recall, F1, run-to-run agreement, combinations and per-type recall from saved results without any API calls. |
| `judge/INSTRUCTIONS.md` | Instructions given to the LLM judges in Pilot C. |
| `judge/blind_cases.json` | The judges' input: the same 104 cases without labels or detector outputs. |
| `judge/judge_results.jsonl` | Pilot C verdicts: Claude Sonnet 5.5 (run 1) and Claude Opus 5.5 (runs 2 and 3), 104 cases each. |
| `scoring_report.txt` | Output of the scorer on these results. |
| `judge_rerun/` | Blind re-run of Pilot C (9 November 2026): `blind_input/` (the 104 cases with random IDs, shuffled, in 11 batches), `PROMPT.md` (the judge instructions), `judge_results_blind.jsonl` (verdicts mapped back to the original IDs; `anon_id` keeps the ID the judge saw), `id_mapping.json`, `scoring_report_blind.txt`. |

## Reproduce the Pilot B and C scores

```
cd answer_key
python judge.py --report --results ../judge/judge_results.jsonl
```

This prints the figures reported in Section 6 of the report (rules F1 0.994, tests F1 0.883, rules OR tests 1.00, LLM judges 1.00) and matches `scoring_report.txt`. The unit of detection is one operation: 1,098 specification operations plus 18 undocumented ones, 1,116 in total.

## Known limitations

- **Case identifiers in the first Pilot C runs revealed the drift type.** IDs such as `…__missing_operation` were visible in `judge/blind_cases.json`. The experiment was repeated blind (`judge_rerun/`): random IDs, shuffled order, the answer key encrypted while four isolated judges worked (Claude Opus 5.5 twice, Sonnet 5.5 and Haiku 5.5 once). All four again scored precision, recall and F1 of 1.00 with 0 of 18 controls flagged, so the leak did not drive the result; the cases are simply too easy.

Reproduce the blind scores:

```
cd answer_key
python judge.py --report --results ../judge_rerun/judge_results_blind.jsonl
```
- The code that generated the implementations and ran the rule-based and test-based detectors is not included yet; their outputs are stored in `cases.json`. [Add `build_and_eval.py` here if available.]
- Pilot A (the 9-variant toy API, `pilot.py`, `results.json`) and the Schemathesis cross-check are not included yet. [Add if available.]
- The implementations are template-generated with one clean drift each, so all scores are an upper bound.

## Licence

Specifications come from the APIs.guru OpenAPI Directory (CC0). [Choose a licence for the code, e.g. MIT.]
