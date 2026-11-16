"""python -m plan_checker.cli EXPORT"""

from __future__ import annotations

import argparse
import sys

from .model import ExportError, load_export
from .rules import exit_code, run_all


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="apigw-usage-plan-check",
        description="Audit an offline export of OCI API Gateway usage plans for hygiene issues.",
    )
    p.add_argument("export", help="path to the JSON export")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        export = load_export(args.export)
    except ExportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    findings = run_all(export)
    ent = sum(len(p.entitlements) for p in export.usage_plans)
    print(
        f"Usage plan audit - {len(export.usage_plans)} plan(s), {ent} entitlement(s), "
        f"{sum(export.plan_subscriber_counts.values())} subscriber attachment(s), {len(findings)} finding(s)"
    )
    for f in findings:
        print(f"[{f.severity:6s}] {f.rule} plan={f.plan}")
        print(f"         {f.detail}")
    code = exit_code(findings)
    print({0: "RESULT: clean", 1: "RESULT: warnings only", 2: "RESULT: HIGH findings present"}[code])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
