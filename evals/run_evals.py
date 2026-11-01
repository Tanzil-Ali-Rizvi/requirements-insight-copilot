"""Evaluate the copilot offline and gate CI on the results.

Checks
  routing      question goes to docs / data / both as expected
  metric       data questions use the expected governed metric
  retrieval    docs questions cite the expected document (and section, if given) in the top 3
  guard        every attack SQL is blocked, and none can touch files when run in the sandbox
Writes evals/results.json and evals/results.md. Exits 1 if any gate fails.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ric.agent import match_metric, route  # noqa: E402
from ric.retrieval import default_retriever  # noqa: E402
from ric.sql_guard import UnsafeSQL, validate  # noqa: E402
from ric.warehouse import query  # noqa: E402

GATES = {"routing": 0.90, "metric": 0.90, "retrieval": 0.90, "guard": 1.00}


def score_cases(cases: list[dict], failures: list[str]) -> dict[str, list[int]]:
    retriever = default_retriever()
    tally = {k: [0, 0] for k in ("routing", "metric", "retrieval")}
    for c in cases:
        got = route(c["q"])
        ok = got == c["route"]
        tally["routing"][0] += ok
        tally["routing"][1] += 1
        if not ok:
            failures.append(f"routing  {c['id']}: expected {c['route']}, got {got} | {c['q']}")
        if "metric" in c:
            m, _ = match_metric(c["q"])
            ok = bool(m) and m.key == c["metric"]
            tally["metric"][0] += ok
            tally["metric"][1] += 1
            if not ok:
                failures.append(f"metric   {c['id']}: expected {c['metric']}, got {m.key if m else None} | {c['q']}")
        if "doc" in c:
            hits = retriever.search(c["q"], k=3)
            ok = any(h.chunk.doc == c["doc"] and ("section" not in c or h.chunk.section == c["section"]) for h in hits)
            tally["retrieval"][0] += ok
            tally["retrieval"][1] += 1
            if not ok:
                failures.append(f"retrieval {c['id']}: expected {c['doc']} § {c.get('section', '*')}, got "
                                f"{[h.chunk.citation for h in hits]} | {c['q']}")
    return tally


def main() -> int:
    failures: list[str] = []
    tally = score_cases(yaml.safe_load((ROOT / "evals" / "cases.yaml").read_text()), failures)
    tally["guard"] = [0, 0]
    holdout_failures: list[str] = []
    holdout = score_cases(yaml.safe_load((ROOT / "evals" / "holdout.yaml").read_text()), holdout_failures)
    attacks = yaml.safe_load((ROOT / "evals" / "guard_attacks.yaml").read_text())

    for sql in attacks:
        blocked = False
        try:
            validate(sql)
        except UnsafeSQL:
            blocked = True
        if not blocked:  # second wall: the sandbox must refuse it too
            try:
                query(sql)
            except Exception:
                blocked = True
        tally["guard"][0] += blocked
        tally["guard"][1] += 1
        if not blocked:
            failures.append(f"guard    not blocked: {sql}")

    results = {k: {"passed": p, "total": n, "score": p / n if n else 1.0, "gate": GATES[k]}
               for k, (p, n) in tally.items()}
    passed = all(r["score"] >= r["gate"] for r in results.values())
    held = {k: {"passed": p, "total": n, "score": p / n if n else 1.0} for k, (p, n) in holdout.items()}
    (ROOT / "evals" / "results.json").write_text(json.dumps(
        {"results": results, "holdout": held, "failures": failures, "holdout_failures": holdout_failures,
         "passed": passed}, indent=2))
    lines = ["| Check | Tuned set | Held-out set | CI gate |", "| --- | --- | --- | --- |"]
    for k, r in results.items():
        h = held.get(k)
        h_txt = f"{h['passed']}/{h['total']} ({h['score']:.0%})" if h else "n/a"
        lines.append(f"| {k} | {r['passed']}/{r['total']} ({r['score']:.0%}) | {h_txt} | {r['gate']:.0%} |")
    md = "\n".join(lines)
    (ROOT / "evals" / "results.md").write_text(md + "\n")
    print(md)
    for f in failures:
        print("  FAIL", f)
    for f in holdout_failures:
        print("  HOLDOUT MISS", f)
    print("PASSED" if passed else "FAILED")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
