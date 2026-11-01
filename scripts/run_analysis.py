"""Run every governed metric and write reports/findings.json (used by the app and the README)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ric.metrics import METRICS  # noqa: E402
from ric.sql_guard import validate  # noqa: E402
from ric.warehouse import query  # noqa: E402


def main() -> int:
    findings = {}
    for m in METRICS:
        df = query(validate(m.sql))
        findings[m.key] = {"title": m.title, "summary": m.summarize(df),
                           "rows": json.loads(df.head(30).to_json(orient="records", date_format="iso"))}
        print(f"- {m.title}: {findings[m.key]['summary']}")
    out = ROOT / "reports" / "findings.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(findings, indent=2))
    print(f"\nWrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
