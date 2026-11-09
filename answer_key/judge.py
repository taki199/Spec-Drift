"""LLM-as-a-judge for spec drift (Research Project I kit).
Usage:
  pip install anthropic
  export ANTHROPIC_API_KEY=...            # your key, stays on your computer
  python judge.py --runs 3                # all 104 cases x 3 runs (resumable)
  python judge.py --runs 1 --limit 10     # quick try
  python judge.py --report                # metrics from saved results (no API calls)
  python judge.py --mock --runs 2         # test the pipeline without any API (uses the rule detector as fake judge)
Model: set ANTHROPIC_MODEL (default below). Results are appended to judge_results.jsonl."""
import argparse, json, os, re, sys, statistics, time

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
OUT = "judge_results.jsonl"
PROMPT = """You are checking whether a REST API implementation still matches its specification.

SPECIFICATION (source of truth). Each line is one operation: HTTP method, path, documented success status, whether authentication is required, and the top-level fields the success response must contain:
{spec}

IMPLEMENTATION (Flask source code):
```python
{src}
```

For EVERY operation in the specification, decide whether the implementation drifts from it (missing route, wrong success status, missing or renamed response field, authentication required in the spec but not enforced or the reverse). Also list any route the implementation exposes that is NOT in the specification. Path parameter names may differ (e.g. {{id}} vs <id>); that is not drift. Authentication in the implementation is enforced only by the @auth_required decorator.

Answer with JSON only, no other text:
{{"drift": [{{"method": "GET", "path": "/x/{{id}}", "reason": "short reason"}}]}}
List ONLY operations that drift (including undocumented extra routes, with their method and path as in the code). Use an empty list if there is no drift."""

def norm(p): return re.sub(r"[{<][^}>]*[}>]", "*", p)

def spec_text(ops):
    return "\n".join(f"- {o['method']} {o['path']} -> {o['status']}, auth={'yes' if o['auth'] else 'no'}, fields={o['response_fields']}" for o in ops)

def parse(txt):
    m = re.search(r"\{.*\}", txt, re.S)
    try: d = json.loads(m.group(0))["drift"]
    except Exception: return None
    return sorted({(x["method"].upper(), norm(x["path"])) for x in d if "method" in x and "path" in x})

def call(client, case):
    r = client.messages.create(model=MODEL, max_tokens=1500, temperature=0.7,
        messages=[{"role": "user", "content": PROMPT.format(spec=spec_text(case["spec_ops"]), src=case["source"])}])
    return r.content[0].text

def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0; r = tp / (tp + fn) if tp + fn else 0.0
    return round(p, 3), round(r, 3), round(2 * p * r / (p + r), 3) if p + r else 0.0

def clean_pred(p):
    if p is None: return None
    out = set()
    for x in p:
        if isinstance(x, dict): m, pa = x.get("method", ""), x.get("path", "")
        else: m, pa = x[0], x[1]
        out.add((str(m).upper(), norm(str(pa))))
    return sorted(out)

def report(cases):
    rows = [json.loads(l) for l in open(OUT)] if os.path.exists(OUT) else []
    for r in rows: r["pred"] = clean_pred(r["pred"])
    for m in sorted({r.get("model", "?") for r in rows}):
        print("=" * 70); report_one(cases, [r for r in rows if r.get("model", "?") == m], m)

def report_one(cases, rows, MODEL):
    by_case = {c["id"]: c for c in cases}
    runs = sorted({r["run"] for r in rows})
    if not rows: print("no results yet"); return
    def universe(c): return {(o["method"], norm(o["path"])) for o in c["spec_ops"]} | {tuple(x) for x in c["gt"]}
    def score(pred_fn):
        tp = fp = fn = tn = 0
        for c in cases:
            gt = {tuple(x) for x in c["gt"]}
            fl = pred_fn(c)
            if fl is None: continue
            for u in universe(c):
                a, b = u in fl, u in gt
                if a and b: tp += 1
                elif a: fp += 1
                elif b: fn += 1
                else: tn += 1
        return tp, fp, fn, tn
    results = {}
    per_run = []
    for run in runs:
        d = {r["id"]: r["pred"] for r in rows if r["run"] == run and r["pred"] is not None}
        tp, fp, fn, tn = score(lambda c: set(map(tuple, d[c["id"]])) if c["id"] in d else None)
        per_run.append(prf(tp, fp, fn)); 
    print(f"model: {MODEL}   runs: {len(runs)}   cases judged per run: {[len({r['id'] for r in rows if r['run']==x}) for x in runs]}")
    for i, (p, r, f) in enumerate(per_run): print(f"  run {runs[i]}: precision {p}  recall {r}  F1 {f}")
    if len(per_run) > 1:
        for name, k in (("precision", 0), ("recall", 1), ("F1", 2)):
            v = [x[k] for x in per_run]; print(f"  {name}: mean {statistics.mean(v):.3f}  std {statistics.pstdev(v):.3f}")
    # run-to-run disagreement
    dis = 0; tot = 0
    for cid in by_case:
        ps = [json.dumps(r["pred"]) for r in rows if r["id"] == cid and r["pred"] is not None]
        if len(ps) > 1: tot += 1; dis += len(set(ps)) > 1
    if tot: print(f"  cases where runs disagree: {dis}/{tot}")
    # first run as the LLM, plus combinations
    r0 = runs[0]; d0 = {r["id"]: set(map(tuple, r["pred"])) for r in rows if r["run"] == r0 and r["pred"] is not None}
    combos = {
      "LLM alone": lambda c: d0.get(c["id"]),
      "rules alone": lambda c: set(map(tuple, c["rule"])),
      "tests alone": lambda c: set(map(tuple, c["test"])),
      "rules OR tests": lambda c: set(map(tuple, c["rule"])) | set(map(tuple, c["test"])),
      "LLM OR rules OR tests": lambda c: (d0.get(c["id"]) or set()) | set(map(tuple, c["rule"])) | set(map(tuple, c["test"])) if c["id"] in d0 else None,
      "majority of LLM, rules, tests": lambda c: (lambda s: {u for u in universe(c) if sum(u in x for x in s) >= 2})([d0[c['id']], set(map(tuple, c['rule'])), set(map(tuple, c['test']))]) if c["id"] in d0 else None,
      "(rules OR tests) AND LLM": lambda c: ((set(map(tuple, c["rule"])) | set(map(tuple, c["test"]))) & d0[c["id"]]) if c["id"] in d0 else None,
    }
    print(f"\nCombinations (using run {r0} of the LLM):")
    for n, fn_ in combos.items():
        tp, fp, fn, tn = score(fn_); p, r, f = prf(tp, fp, fn)
        print(f"  {n:32s} TP {tp:4d} FP {fp:4d} FN {fn:4d}  precision {p}  recall {r}  F1 {f}")
    # LLM per drift type
    print("\nLLM recall per drift type (run %s):" % r0)
    kinds = sorted({c["kind"] for c in cases if c["gt"]})
    for k in kinds:
        hit = tot = 0
        for c in cases:
            if c["kind"] == k and c["id"] in d0:
                gt = {tuple(x) for x in c["gt"]}; tot += len(gt); hit += len(gt & d0[c["id"]])
        print(f"  {k:26s} {hit}/{tot}")
    fpc = [(c["id"], sorted(d0[c["id"]])) for c in cases if c["kind"] == "control" and c["id"] in d0 and d0[c["id"]]]
    print(f"\nControls wrongly flagged by the LLM (run {r0}): {len(fpc)} of {sum(1 for c in cases if c['kind']=='control' and c['id'] in d0)}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--report", action="store_true"); ap.add_argument("--results", default=None); ap.add_argument("--mock", action="store_true")
    a = ap.parse_args()
    global OUT
    if a.results: OUT = a.results
    cases = json.load(open("cases.json"))
    if a.report: return report(cases)
    if a.limit:  # keep a balanced sample: controls plus drifted
        cases = cases[:a.limit]
    done = set()
    if os.path.exists(OUT):
        for l in open(OUT): r = json.loads(l); done.add((r["id"], r["run"]))
    client = None
    if not a.mock:
        import anthropic; client = anthropic.Anthropic()
    with open(OUT, "a") as f:
        for run in range(1, a.runs + 1):
            for i, c in enumerate(cases):
                if (c["id"], run) in done: continue
                if a.mock: pred = c["rule"]; raw = "mock"
                else:
                    for attempt in range(4):
                        try: raw = call(client, c); break
                        except Exception as e:
                            print("retry", attempt, e, file=sys.stderr); time.sleep(5 * (attempt + 1)); raw = None
                    pred = parse(raw) if raw else None
                f.write(json.dumps(dict(id=c["id"], run=run, pred=pred, raw=raw, model=MODEL)) + "\n"); f.flush()
                if i % 10 == 0: print(f"run {run}: {i+1}/{len(cases)}", flush=True)
    report(json.load(open("cases.json"))[:a.limit] if a.limit else json.load(open("cases.json")))

if __name__ == "__main__":
    main()
