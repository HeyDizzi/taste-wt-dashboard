# Primary funnel friction

## Method, not speculation

1. Build one person-level spine across both systems (2,478 Notion applications ∪ 975 portal
   profiles; 768 join by email). Dedupe with flagged — never silent — merges.
2. Assign each person their furthest canonical stage (mapping: `00-data-mapping.md`).
3. Rank transitions by **absolute people lost**, not worst percentage — a 90% drop on 20
   people is noise; a 40% drop on 800 is the business problem.
4. Price each leak: people lost × cost-per-vetted-designer (editable input; $150 default assumption
   until FP&A confirms).

## What the cleaned spine shows (pipeline run 2026-07-22; 2,541 persons)

| Transition | Cleaned numbers | Read |
|---|---|---|
| outreached → responded | 9,445 → 2,815 (30% reply) | largest in absolute heads (−6,630), but a ~30% LinkedIn reply rate is at/above channel norms — this is the cost of doing outreach, not a broken step |
| responded → applied | 2,815 repliers → 681 applied (24%) | doc remembered ~37%; join undercount explains part of the gap |
| applied → portfolio passed | 2,541 → 1,797 (71%) | screening is not the problem |
| passed → accepted | 1,797 → 1,441 (80%) | nor is acceptance |
| **accepted → any project contact** | **1,441 → 611: −830 people (58% never contacted)** | **the leak that matters: these people cost real vetting spend, and losing them is not channel-normal** |
| project contact → staffed | 611 → 134 (22%) | second leak: of 855 deals, 198 sit at `invited`/pending indefinitely, 235 rejected |
| staffed → billable | not measurable — `lifetime_hours` = 0 for every profile | instrumentation gap, not a funnel finding |

(An earlier portal-only cut said 364/553 = 66%; the cross-system spine supersedes it — the
leak is bigger than either system shows alone.)

Working hypothesis to interrogate, not assert: the funnel's constraint is not recruiting
volume or screening quality — it is **matching throughput after acceptance**. Availability
statuses agree: 399 profiles are `active_not_on_project`, 137 `idle`, only 3 `active_full`.

## Business impact framing

At $150/vetted designer, 1,307 vetted-never-staffed (830 never offered + 477 offered but
never converted) ≈ **$196k of sunk vetting spend** producing zero supply — before counting
acquisition spend above them in the funnel. Editable cost input in the dashboard; number
updates when FP&A gives the real cost.
