# oci-ootb-apigw-usage-plan-check

**Category: built-in OCI services project (OOTB).** The custom portfolio project in this pair
is `oci-reserved-ip-inventory`.

## Which built-in OCI services this wires

- **OCI API Gateway Usage Plans** (`oci_apigateway_usage_plan`): entitlements with optional
  rate limits (requests per second) and quotas (requests per Minute/Hour/Day/Week/Month with a
  Calendar reset policy and REJECT/ALLOW on breach), targeting one or more API deployments.
- **OCI API Gateway Subscribers** (`oci_apigateway_subscriber`): API consumers (clients with
  reporting tokens) subscribed to one or more usage plans.
- **OCI API Gateway Deployments** (`oci_apigateway_deployment`): the API deployments the
  entitlements target. A deployment must be made *eligible* for usage-plan inclusion first
  (a deployment-level operation); the Terraform here does not model eligibility.

## Custom code vs native config

- **Native config**: `terraform/` declares a gateway, one deployment, one usage plan with a
  properly shaped entitlement, and one subscriber, using only built-in provider resources.
  **Template only - NOT plan/apply validated** (no live tenancy).
- **Custom code**: `plan_checker/` audits an offline JSON export of usage plans, entitlements
  and subscribers against four hygiene rules the service does not enforce for you.

## The rules

| Rule | Severity | Fires when |
| ---- | -------- | ---------- |
| PLAN001 | HIGH | An entitlement sets neither a rate limit nor a quota. Per OCI docs, an unlimited rate limit/quota then applies to its target deployments (clients still need a subscription + token, but nothing caps their volume). |
| PLAN002 | MEDIUM | An entitlement's quota has `operation_on_breach: ALLOW` - the quota is recorded but breaches are never rejected (no HTTP-429); it is reporting, not protection. |
| PLAN003 | MEDIUM | The same API deployment is targeted by two entitlements **within one usage plan** - OCI explicitly does not allow this, so the plan would be rejected at apply time. |
| PLAN004 | LOW | A usage plan has zero subscribers - nothing can consume it yet (subscribers are the only way clients attach to a plan). |

Exit code: `2` on any HIGH, `1` on MEDIUM/LOW only, `0` when clean.

## Run it

```bash
python -m plan_checker.cli samples/plans_messy.json   # exits 2, all 4 rules fire
python -m plan_checker.cli samples/plans_clean.json   # exits 0
python -m unittest discover -s tests -v               # 18 tests, stdlib only
```

## Honest limits

- **Offline audit**: the JSON export is synthetic; nothing calls the OCI API Gateway service.
- Rule semantics are grounded in the official docs
  (<https://docs.oracle.com/en-us/iaas/Content/APIGateway/Tasks/apigatewaydefiningusageplans_topic-Creating-a-usage-plan.htm>)
  as of Nov 2026: unlimited-when-unset, REJECT/ALLOW-on-breach, no duplicate deployment within
  one plan, subscribers-attach-to-plans.
- Deployment *eligibility* for usage plans is a service-side prerequisite not modeled here.
- Client tokens are for usage-plan reporting, not authentication; this project never handles
  real tokens.
- Terraform template is illustrative and has **not** been plan/apply validated.

## Project status

Built as a daily OOTB project. 18 unit tests, green locally and in CI. Free tier only; no
live cloud calls, no spend.
