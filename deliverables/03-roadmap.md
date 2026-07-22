# Initial roadmap

Prioritization logic: **(1) make the leak visible, (2) drain it manually, (3) build the system
that keeps it drained.** Manual before scalable — every automation below is a manual play run
twice first. Impact ranked by people × cost recovered per unit effort.

## Now (days 1–7) — manual interventions

| # | Move | Type | Why first |
|---|---|---|---|
| 1 | Funnel dashboard on cleaned two-source data (this build) | tool | can't manage what's invisible; prices every leak |
| 2 | Concierge matching sprint on the 364 never-staffed accepted experts (see `04-low-lift-activation.md`) | manual | largest leak, zero build required |
| 3 | Clear the 198 pending invites: expire, nudge, or hand-route each | manual | 23% of all deals are stalled at one status |
| 4 | Instrument the two dead stages: log `responded`, wire assessment/test fields (portal fields exist, all null) | fix | unblocks measurement of stages 2/4/5 |

## Next (weeks 2–6) — convert manual plays into system

| # | Build | Replaces |
|---|---|---|
| 5 | Availability-aware match queue: open position → ranked bench shortlist (specialization enum already shared across both systems) | manual matching sprint |
| 6 | Invite lifecycle automation: TTL, reminder, auto-escalation on `invited` deals | manual invite chase |
| 7 | Billable-hours ingestion (timesheet/payment source → portal `lifetime_hours`) | the VAR proxy; enables true North Star |
| 8 | Kill the Notion/portal split: one system of record, or a nightly sync with the 137 board-only + 1,600 Notion-only reconciliation surfaced | manual cross-checking |

## Later (quarter) — scale what worked

| # | Build |
|---|---|
| 9 | Cohort/time views on stage timestamps (`stage_entered_at` exists on deals — start persisting history) |
| 10 | Supply-request loop: auto-generated needed-roles already exist in portal (4 open) — route them to the bench automatically, closing the loop 5 built manually |
| 11 | Demand-side pacing: recruit-to-demand ratio guardrail so acceptance rate tracks project pipeline, not recruiting momentum |

Sequencing rule: nothing in "Next" ships until its manual version in "Now" has run and the
dashboard shows the leak it targets actually moving.
