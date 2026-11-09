# Task: act as a blind LLM judge for REST API spec drift

You are the "LLM-as-a-judge" method in a research comparison (Master's research project: automated spec-drift detection). Work ONLY inside this `judge/` folder.

IMPORTANT: do NOT open, list or read anything in `../answer_key/` until every judging run is finished. It holds the correct answers; looking at it would invalidate the experiment.

## Input
`blind_cases.json`: a list of 104 cases. Each case has:
- `id`
- `spec_ops`: the specification (source of truth). One entry per operation: method, path, documented success status, whether auth is required, and the top-level fields the success response must contain.
- `source`: the Flask implementation code.

## For each case, decide
Which operations drift from the specification:
- a spec operation whose route is missing in the code,
- a wrong success status code,
- a missing or renamed response field,
- authentication required in the spec but not enforced (auth is enforced only by the `@auth_required` decorator), or the reverse,
- any route in the code that is NOT in the specification (report it with the method and path as written in the code).
Path parameter names may differ (`{id}` vs `<id>`); that is not drift. List ONLY operations that drift. If a case has no drift, the list is empty.
Judge each case independently from the spec and code shown. Do not guess based on case ids or on how many cases have drift.

## Output
Append one JSON line per case to `judge_results.jsonl` (create it if missing):
`{"id": "<case id>", "run": <run number>, "model": "<your exact model name>", "pred": [["POST", "/path"], ...], "raw": "<one short sentence of reasoning>"}`
`pred` is a list of [method, path] pairs (empty list if no drift).

## How to work
- Process the cases in batches of 10 and write each batch's lines to the file before starting the next batch, so nothing is lost.
- One run = all 104 cases once. Run number comes from the user ("run 1", "run 2", ...). Tell the user which model you are and ask for the run number if not given.
- For repeat runs, the user will start a fresh chat so earlier answers do not influence you. Do not read earlier results in `judge_results.jsonl` while judging.
- Do not use any tool to detect drift automatically (no scripts that compare spec and code). The point is your own judgement as an LLM.

## After all runs are done (only then)
Run the scoring from `../answer_key/`:
`python ../answer_key/judge.py --report --results judge_results.jsonl`
(run it from the folder that contains `answer_key/`'s `cases.json`, i.e. `cd ../answer_key` and use `--results ../judge/judge_results.jsonl`.)
Then send the printed report and `judge_results.jsonl` to the user.
