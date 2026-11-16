"""PLAN001-PLAN004 rules, grounded in the OCI API Gateway usage-plan docs."""

from __future__ import annotations

from dataclasses import dataclass

from .model import Export


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str  # HIGH | MEDIUM | LOW
    plan: str
    detail: str


def rule_unlimited_entitlement(export: Export) -> list:
    """PLAN001 HIGH: entitlement with no rate limit AND no quota -> unlimited usage."""
    out = []
    for plan in export.usage_plans:
        for e in plan.entitlements:
            if not e.has_rate_limit() and not e.has_quota():
                out.append(
                    Finding(
                        rule="PLAN001",
                        severity="HIGH",
                        plan=plan.display_name or plan.ocid,
                        detail=(
                            f"entitlement '{e.name}' sets neither a rate limit nor a quota; "
                            f"an unlimited rate/quota applies to its {len(e.target_deployments)} target deployment(s)"
                        ),
                    )
                )
    return out


def rule_soft_quota(export: Export) -> list:
    """PLAN002 MEDIUM: quota exists but breaches are allowed (never rejected)."""
    out = []
    for plan in export.usage_plans:
        for e in plan.entitlements:
            if e.has_quota() and e.operation_on_breach == "ALLOW":
                out.append(
                    Finding(
                        rule="PLAN002",
                        severity="MEDIUM",
                        plan=plan.display_name or plan.ocid,
                        detail=(
                            f"entitlement '{e.name}' quota {e.quota_value}/{e.quota_unit} has "
                            f"operation_on_breach=ALLOW; breaches are never rejected (no HTTP-429)"
                        ),
                    )
                )
    return out


def rule_duplicate_target(export: Export) -> list:
    """PLAN003 MEDIUM: same deployment in two entitlements within one plan (not allowed)."""
    out = []
    for plan in export.usage_plans:
        seen: dict = {}
        for e in plan.entitlements:
            for dep in e.target_deployments:
                if dep in seen:
                    out.append(
                        Finding(
                            rule="PLAN003",
                            severity="MEDIUM",
                            plan=plan.display_name or plan.ocid,
                            detail=(
                                f"deployment {dep} is targeted by both entitlements "
                                f"'{seen[dep]}' and '{e.name}' in the same usage plan; OCI rejects this"
                            ),
                        )
                    )
                else:
                    seen[dep] = e.name
    return out


def rule_no_subscribers(export: Export) -> list:
    """PLAN004 LOW: usage plan with zero subscribers."""
    out = []
    for plan in export.usage_plans:
        if export.plan_subscriber_counts.get(plan.ocid, 0) == 0:
            out.append(
                Finding(
                    rule="PLAN004",
                    severity="LOW",
                    plan=plan.display_name or plan.ocid,
                    detail="no subscribers are attached; nothing can consume this plan yet",
                )
            )
    return out


ALL_RULES = (
    rule_unlimited_entitlement,
    rule_soft_quota,
    rule_duplicate_target,
    rule_no_subscribers,
)

_SEVERITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def run_all(export: Export) -> list:
    findings = []
    for rule in ALL_RULES:
        findings.extend(rule(export))
    findings.sort(key=lambda f: (_SEVERITY_RANK[f.severity], f.rule, f.plan))
    return findings


def exit_code(findings: list) -> int:
    if any(f.severity == "HIGH" for f in findings):
        return 2
    if findings:
        return 1
    return 0
