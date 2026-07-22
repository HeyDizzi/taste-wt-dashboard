# North Star metric

## The metric

**Vetted Activation Rate (VAR): % of accepted experts with billable activity in the trailing
30 days.**

Today's proxy (billable hours not instrumented): % of accepted experts on an `active` deal =
52 / 1,441 = **3.6%** (cleaned cross-system spine; the portal-only cut said 9.4% — the
denominator was hiding 888 accepted people who exist only in Notion).

## Why it beats the alternatives

| Alternative | Why it loses |
|---|---|
| Network size (accepted count) | Counts inventory, not output. Taste's own data: 1,441 accepted, 91% never staffed — size grew while vitality didn't. |
| Applications / pipeline volume | Measures top-of-funnel spend efficiency, already healthy; more volume worsens the actual constraint (matching). |
| Total billable hours / GMV | Hides concentration — 3 experts at `active_full` can carry the number while the bench rots. VAR counts *people*, so over-utilization can't mask idle supply. |
| Utilization % of active experts | Denominator excludes the dormant pool — the exact population the business is paying for and wasting. |
| NPS / expert satisfaction | Lagging, unmeasurable weekly, and downstream of VAR anyway: idle experts churn. |

## Why it's the vitality metric for a two-sided marketplace

- It is the only number both sides move: demand growth raises it, supply over-recruiting
  lowers it. It punishes exactly the two observed failure modes (idle bench, reactive staffing).
- It decomposes cleanly for diagnosis: VAR = (accepted → offered) × (offered → active) ×
  (active → billable) — each factor owned by a different fix.
- Numerator switches from "active deal" to "billable hours > 0 in 30d" the day hours data
  exists; definition survives the instrumentation upgrade.
