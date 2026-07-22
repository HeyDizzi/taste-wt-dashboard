# Information gaps

Ranked by how much they constrain the diagnosis, each with the workaround in use.

| # | Missing | Evidence | Proceeding by |
|---|---|---|---|
| 1 | **Billable hours / payments** | `lifetime_hours` = 0 on all 975 profiles; deal `rate` null on all 855 | VAR proxy = "on an active deal"; dashboard swaps to true billable the day a timesheet/payment export lands |
| 2 | **Assessment data** | portal test fields null everywhere; 56-deal stratified sample of submissions all empty | `Portfolio Approval` used as the vetting proxy; stages 4–5 labeled *not instrumented* on the funnel, as findings |
| 3 | **`responded` stage** | no field in either system | funnel renders the stage as not instrumented; outreach→applied shown as one combined conversion |
| 4 | **Stage-transition history** | only current `stage` + one `stage_entered_at` per deal; no event log | time-in-stage computed for current stage only; cohort view limited to application-date cohorts |
| 5 | **Cost per vetted designer** | not in trial environment | editable input, $500 tagged "assumption" until FP&A number arrives |
| 6 | **Demand-side pipeline** (upcoming projects, revenue per project) | 8 projects visible, no pipeline/revenue fields | activation framed in people and sunk vetting cost, not revenue-at-risk |
| 7 | **Offer history for the dormant pool** | can't distinguish "never offered" from "offered, declined" for the 364 | the activation sprint (04) generates this split as a byproduct within a week |
| 8 | **System-of-record ambiguity** | 137 experts on the pipeline board but absent from the directory; 1,600 Notion applicants absent from portal; 1,250 same-name rows vs only 69 same-email in Notion | dedupe flags, never merges; discrepancy counts reported in the dashboard provenance footer, and the name-collision anomaly diagnosed before any dedupe rule is locked |

Constraint posture: every gap is rendered *visibly* in the dashboard (empty states name the
missing data), so instrumentation debt is presented as a first-class finding, not hidden.
