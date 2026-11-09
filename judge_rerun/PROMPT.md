# Blind re-run of Pilot C: judge instructions

Each judge (Claude Opus 5.5 run 1, Claude Opus 5.5 run 2, Claude Sonnet 5.5, Claude Haiku 5.5) ran as a separate, freshly started agent with no shared context. It received the same 11 batch files (`blind_input/`, random case IDs, shuffled order) in its own folder. The answer key and every file containing labels were encrypted with a passphrase that no judge could see for the whole duration of the runs, and were restored afterwards (checksums verified). No helper scripts were found in the judges' folders after the runs.

The instructions each judge received:

> You are the "LLM-as-a-judge" method in a research experiment on REST API specification drift. Work ONLY inside your folder. Do not list, open or search any other folder or file on this machine.
>
> INPUT: 11 files batch_01.json ... batch_11.json, 104 cases in total. Each case has "id" (a neutral identifier), "spec_ops" (the specification, the source of truth: one entry per operation with method, path, documented success status, whether auth is required, and the top-level fields the success response must contain) and "source" (the Flask implementation code).
>
> FOR EACH CASE decide which operations drift from the specification: a spec operation whose route is missing in the code; a wrong success status code; a missing or renamed response field; authentication required in the spec but not enforced (auth is enforced only by the @auth_required decorator), or the reverse; any route in the code that is NOT in the specification (report it with the method and path as written in the code). Path parameter names may differ ({id} vs <id>); that is not drift. List ONLY operations that drift. If a case has no drift, the list is empty. Judge each case independently from the spec and code shown.
>
> RULES: Do not write or run any script or program that compares spec and code; the point is your own reading and judgement. You may use tools only to read the batch files and to append your answers. Read one batch file at a time.
>
> OUTPUT: after judging each batch, append one JSON line per case to results.jsonl: {"id": "<case id>", "pred": [["POST", "/path"], ...], "raw": "<one short sentence of reasoning>"}.
