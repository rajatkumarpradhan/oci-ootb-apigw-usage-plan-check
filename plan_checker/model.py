"""Data model + export loading for the usage-plan audit."""

from __future__ import annotations

import json
from dataclasses import dataclass


class ExportError(ValueError):
    """Raised when an export file is malformed."""


QUOTA_UNITS = {"MINUTE", "HOUR", "DAY", "WEEK", "MONTH"}


@dataclass(frozen=True)
class Entitlement:
    name: str
    rate_limit_rps: int | None
    quota_value: int | None
    quota_unit: str | None
    operation_on_breach: str | None  # REJECT | ALLOW
    target_deployments: tuple

    def has_rate_limit(self) -> bool:
        return self.rate_limit_rps is not None

    def has_quota(self) -> bool:
        return self.quota_value is not None


@dataclass(frozen=True)
class UsagePlan:
    ocid: str
    display_name: str
    entitlements: tuple


@dataclass(frozen=True)
class Export:
    deployments: frozenset
    usage_plans: tuple
    plan_subscriber_counts: dict  # plan ocid -> number of subscribers


def _parse_entitlement(raw: dict, where: str) -> Entitlement:
    if "name" not in raw:
        raise ExportError(f"{where}: missing required field 'name'")
    rl = raw.get("rate_limit")
    rps = None
    if rl is not None:
        if not isinstance(rl, dict) or "value" not in rl:
            raise ExportError(f"{where}.rate_limit: must be an object with 'value'")
        unit = rl.get("unit", "SECOND")
        if unit != "SECOND":
            raise ExportError(f"{where}.rate_limit: unit must be SECOND, got {unit!r}")
        rps = int(rl["value"])
    q = raw.get("quota")
    qv = q_unit = breach = None
    if q is not None:
        for req in ("value", "unit", "operation_on_breach"):
            if req not in q:
                raise ExportError(f"{where}.quota: missing required field {req!r}")
        if q["unit"] not in QUOTA_UNITS:
            raise ExportError(f"{where}.quota: unit must be one of {sorted(QUOTA_UNITS)}, got {q['unit']!r}")
        if q["operation_on_breach"] not in ("REJECT", "ALLOW"):
            raise ExportError(f"{where}.quota: operation_on_breach must be REJECT or ALLOW")
        qv, q_unit, breach = int(q["value"]), q["unit"], q["operation_on_breach"]
    targets = raw.get("target_deployments", [])
    if not isinstance(targets, list):
        raise ExportError(f"{where}: 'target_deployments' must be a list")
    return Entitlement(
        name=raw["name"],
        rate_limit_rps=rps,
        quota_value=qv,
        quota_unit=q_unit,
        operation_on_breach=breach,
        target_deployments=tuple(targets),
    )


def load_export(path: str) -> Export:
    with open(path, "r", encoding="utf-8") as fh:
        try:
            raw = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ExportError(f"{path}: not valid JSON: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("usage_plans"), list):
        raise ExportError(f"{path}: top level must be an object with a 'usage_plans' list")
    plans = []
    for i, p in enumerate(raw["usage_plans"]):
        where = f"usage_plans[{i}]"
        if "ocid" not in p:
            raise ExportError(f"{where}: missing required field 'ocid'")
        entitlements = tuple(
            _parse_entitlement(e, f"{where}.entitlements[{j}]")
            for j, e in enumerate(p.get("entitlements", []))
        )
        plans.append(UsagePlan(ocid=p["ocid"], display_name=p.get("display_name", ""), entitlements=entitlements))
    counts = {p.ocid: 0 for p in plans}
    for s in raw.get("subscribers", []):
        for pid in s.get("usage_plan_ids", []):
            if pid in counts:
                counts[pid] += 1
    return Export(
        deployments=frozenset(raw.get("deployments", [])),
        usage_plans=tuple(plans),
        plan_subscriber_counts=counts,
    )
