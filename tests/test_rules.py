import unittest

from plan_checker.model import Entitlement, Export, UsagePlan
from plan_checker.rules import (
    exit_code,
    rule_duplicate_target,
    rule_no_subscribers,
    rule_soft_quota,
    rule_unlimited_entitlement,
    run_all,
)

D1, D2 = "ocid1.apideployment.oc1..d1", "ocid1.apideployment.oc1..d2"


def ent(name="e", rps=10, quota=(100, "MONTH", "REJECT"), targets=(D1,)):
    qv, qu, br = (None, None, None) if quota is None else quota
    return Entitlement(name=name, rate_limit_rps=rps, quota_value=qv,
                       quota_unit=qu, operation_on_breach=br, target_deployments=tuple(targets))


def plan(ocid="ocid1.apigatewayusageplan.oc1..p", name="plan", ents=()):
    return UsagePlan(ocid=ocid, display_name=name, entitlements=tuple(ents))


def exp(plans, subs=()):
    counts = {p.ocid: 0 for p in plans}
    for s in subs:
        for pid in s:
            if pid in counts:
                counts[pid] += 1
    return Export(deployments=frozenset({D1, D2}), usage_plans=tuple(plans),
                  plan_subscriber_counts=counts)


class TestPlan001Unlimited(unittest.TestCase):
    def test_fires_without_limits(self):
        e = exp([plan(ents=[ent(rps=None, quota=None)])], subs=[["ocid1.apigatewayusageplan.oc1..p"]])
        out = rule_unlimited_entitlement(e)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].severity, "HIGH")

    def test_rate_limit_alone_suffices(self):
        e = exp([plan(ents=[ent(quota=None)])])
        self.assertEqual(rule_unlimited_entitlement(e), [])

    def test_quota_alone_suffices(self):
        e = exp([plan(ents=[ent(rps=None)])])
        self.assertEqual(rule_unlimited_entitlement(e), [])


class TestPlan002SoftQuota(unittest.TestCase):
    def test_fires_on_allow(self):
        e = exp([plan(ents=[ent(quota=(100, "DAY", "ALLOW"))])])
        out = rule_soft_quota(e)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].severity, "MEDIUM")

    def test_reject_quiet(self):
        e = exp([plan(ents=[ent(quota=(100, "DAY", "REJECT"))])])
        self.assertEqual(rule_soft_quota(e), [])

    def test_no_quota_quiet(self):
        e = exp([plan(ents=[ent(quota=None)])])
        self.assertEqual(rule_soft_quota(e), [])


class TestPlan003DuplicateTarget(unittest.TestCase):
    def test_fires_on_dup_within_plan(self):
        e = exp([plan(ents=[ent(name="a", targets=(D1,)), ent(name="b", targets=(D1, D2))])])
        out = rule_duplicate_target(e)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].severity, "MEDIUM")

    def test_same_target_across_plans_ok(self):
        p1 = plan(ocid="ocid1.apigatewayusageplan.oc1..p1", ents=[ent(name="a", targets=(D1,))])
        p2 = plan(ocid="ocid1.apigatewayusageplan.oc1..p2", ents=[ent(name="b", targets=(D1,))])
        e = exp([p1, p2])
        self.assertEqual(rule_duplicate_target(e), [])

    def test_no_dup_quiet(self):
        e = exp([plan(ents=[ent(name="a", targets=(D1,)), ent(name="b", targets=(D2,))])])
        self.assertEqual(rule_duplicate_target(e), [])


class TestPlan004NoSubscribers(unittest.TestCase):
    def test_fires_with_zero_subscribers(self):
        e = exp([plan(ents=[ent()])])
        self.assertEqual(len(rule_no_subscribers(e)), 1)

    def test_quiet_with_subscriber(self):
        e = exp([plan(ents=[ent()])], subs=[["ocid1.apigatewayusageplan.oc1..p"]])
        self.assertEqual(rule_no_subscribers(e), [])


class TestAggregation(unittest.TestCase):
    def test_exit_code_2_on_high(self):
        e = exp([plan(ents=[ent(rps=None, quota=None)])], subs=[["ocid1.apigatewayusageplan.oc1..p"]])
        self.assertEqual(exit_code(run_all(e)), 2)

    def test_exit_code_1_on_medium_only(self):
        e = exp([plan(ents=[ent(quota=(100, "DAY", "ALLOW"))])], subs=[["ocid1.apigatewayusageplan.oc1..p"]])
        self.assertEqual(exit_code(run_all(e)), 1)

    def test_exit_code_0_when_clean(self):
        e = exp([plan(ents=[ent()])], subs=[["ocid1.apigatewayusageplan.oc1..p"]])
        self.assertEqual(exit_code(run_all(e)), 0)


if __name__ == "__main__":
    unittest.main()
