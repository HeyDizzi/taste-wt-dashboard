# BUILD BRIEF: Taste Labs Expert Funnel Diagnostic Dashboard

## Who I am and what this is

I'm doing a one-day work trial for a Head of Growth role at Taste Labs, a ~26-person company that supplies AI labs with expert designer judgment ("taste data") for model training. It's a two-sided marketplace: demand side = AI research labs buying projects; supply side = designers recruited into an expert network.

The business problem: acquisition cost per designer keeps rising because the funnel leaks downstream of recruiting. Per the trial scenario doc: ~1,500 candidates in the pipeline, several hundred passed full verification, a significant vetted pool never staffed, information fragmented across platforms, and staffing is reactive — **a few designers are over-utilized while a deep bench sits idle**. The dashboard's job is to make the leaks visible, locate them precisely, and price them.

**This is a one-day build (4–5 working hours). Diagnostic clarity beats feature completeness. When in doubt, cut scope, never polish.**

## Two-part deliverable (both matter — the evaluators value process rigor over output)

1. **Technical interrogation:** a methodology document showing how raw exports became a functional funnel. So: log every step as we go. Keep all scripts. Every cleaning decision (dedupe rules, dropped rows, date parsing, stage mapping, figures that don't reconcile) gets written to a running `METHODOLOGY.md` with counts before/after. Where two exports disagree on the same figure, do not silently resolve — record both numbers, the resolution rule chosen, and why. This document is a first-class deliverable, not a byproduct.
2. **The dashboard/analysis itself**, feeding a 4pm presentation (~12–15 min of content + discussion).

## Architecture

A **proper dashboard application in a git repo**, run locally (`npm run dev` / `make dev`), pushed to GitHub but never deployed publicly. Structure:

```
taste-funnel/
├── README.md              # setup in ≤3 commands, screenshot, what each view answers
├── METHODOLOGY.md         # deliverable #1 — written as we go
├── pipeline/              # Python (pandas): ingest → clean → reconcile → emit JSON
│   ├── ingest.py          # reads data/raw/*.csv, applies column mapping
│   ├── mapping.yml        # editable canonical-field mapping per source file
│   ├── clean.py           # dedupe, date parsing, stage normalization; logs every decision
│   └── build_metrics.py   # computes all funnel/cohort/concentration metrics → app/public/data/*.json
├── data/
│   ├── raw/               # Dave's real exports — GITIGNORED, never committed
│   └── sample/            # synthetic data mirroring expected schemas — committed, powers the repo out of the box
├── app/                   # Vite + React + TypeScript + Tailwind + Recharts
│   └── src/views/         # Funnel, Headline strip, Concentration, Cohorts, DormantPool
└── .gitignore             # data/raw/, .env, node_modules
```

Key decisions and why:

- **Two-layer split (Python pipeline → JSON → React app):** the pipeline IS the technical interrogation — every cleaning step is a readable, rerunnable script, which is exactly what "document your scripts, queries, and data cleaning protocols" asks for. The frontend stays dumb: it renders precomputed JSON, no data logic in the browser.
- **`data/raw/` is gitignored from the first commit.** Real company exports never touch GitHub, even in a private repo — commit the synthetic sample set instead so the repo runs for anyone who clones it. Say this in the README; handling their data carefully is itself a signal.
- **Column mapping lives in `mapping.yml`, not a UI.** When Dave's files arrive mid-day, I edit the yml to map his headers onto canonical fields and rerun the pipeline. Faster to build than dropdown UI, and the yml file becomes part of the methodology documentation.
- **Rerun loop must be one command** (`make refresh` or `python pipeline/run.py && npm run dev`): drop new CSVs in raw/, rerun, dashboard updates. I will get data in waves during the day.
- **Presentation mode:** it presents from localhost on my laptop at ~1280px. Add a keyboard-driven view switcher (1–5 keys jump between views) so driving it live in the 4pm session is smooth.
- Commit early, commit often, with meaningful messages — the git history is part of the process evidence.

## Data reality (important)

- Source: manual exports from Dave (founding recruiter), covering the **two most active projects**: applications, assessments taken, assessments passed, and stage-by-stage counts underneath them. Possibly also a designer-level roster with timestamps, channel/source, and status; possibly a project-side table. Assume some of these won't arrive.
- The company is **mid-migration from a legacy system to a new UI**, so expect: duplicate designers across systems, inconsistent stage names, mixed date formats, nulls, and free-text status fields.
- **Column mapping via `pipeline/mapping.yml`** (see Architecture): the pipeline reads each raw file's headers and maps them to canonical fields per the yml. On first run against a new file, print unmapped columns loudly so nothing is silently dropped. Canonical designer stages, in order:
  1. `outreached`
  2. `responded`
  3. `applied`
  4. `assessment_taken`
  5. `assessment_passed`
  6. `accepted` (joined community/network)
  7. `project_applied`
  8. `staffed`
  9. `first_billable`
  10. `second_contract`
- Not every stage will exist in the data. The funnel must render gracefully with any subset, and visibly label missing stages as "not instrumented" rather than hiding them — missing instrumentation is itself a finding.
- Canonical optional fields per designer row: `designer_id`, `channel/source`, `recruiter`, `project_id`, `status`, plus a timestamp per stage. Parse dates defensively (ISO, US, and spreadsheet serials).
- Dedupe heuristic: if designer-level data comes from two systems, flag probable duplicates (same email or same name + date proximity) rather than silently merging. Show a count of flagged duplicates — data hygiene is being evaluated.

## Views (priority order — build 1 and 2 first, they are the irreducible core)

### 1. The Funnel (main view)
- Horizontal stage-to-stage funnel using **absolute counts** as bar widths, with stage-to-stage conversion % labeled on each transition.
- Toggle: combined / per-project (the two active projects side by side) / per-channel or per-recruiter if those fields exist.
- The single most important design requirement: **the biggest absolute leak should be impossible to miss** — auto-highlight the transition losing the most people (not the worst percentage).
- Known reference numbers for sanity-checking my column mapping (from a conversation ~3 weeks ago, so tolerate drift): ~17% of outreached apply; ~37% of warm responders apply; ~50% of accepted members never apply to a project. If computed values differ wildly, surface a gentle warning so I catch mapping errors, but never force data toward these numbers.

### 2. Headline metrics strip (top of page, five big numbers)
1. **Vetted-never-billed pool**: count of designers at `accepted`+ who never reached `first_billable`
2. **Cost of that pool**: count × cost-per-vetted-designer. Cost is a **user-editable input field** (I'll get the number from FP&A mid-day; default $500 with an "assumption" tag until edited)
3. **Activation rate**: % of accepted reaching first_billable within 30 days (window editable)
4. **Median time-to-first-billable** (if timestamps exist; else "not instrumented")
5. **R2C**: % of first_billable designers reaching second_contract (else "not instrumented")

### 3. Time / cohort view (only if timestamps arrive)
- Monthly cohorts by first-touch date: stacked progression of how far each cohort got.
- Median days-in-stage per transition; flag designers "stuck" > X days (editable, default 14) at any pre-billable stage.
- If a legacy-vs-new-UI flag exists (or can be inferred from date of entry), split conversion by system — **the migration is a natural A/B test** and this comparison may be the most novel finding available.

### 4. Utilization & concentration view
The scenario doc explicitly flags over-utilization of a few designers alongside an idle bench — so the data almost certainly contains a concentration pattern. Surface it:
- Distribution of billable work across vetted designers (histogram or sorted bar): what share of total billable events comes from the top 10% / 20% of designers.
- A single headline stat: "X% of billable work is done by Y designers, while Z vetted designers have done none."
- If timestamps exist: repeat-staffing intervals for the over-utilized cohort (burnout risk indicator) vs. days-idle for the bench.
This view pairs with the dormant drill-down as one story: same-coin sides of a matching failure, not two problems.

### 5. Dormant pool drill-down
- Table of vetted-never-billed designers: days since acceptance, last activity, channel, project applications if any.
- The key split, if project-side data exists: **"never offered a project" vs. "offered but didn't convert"** — this separates demand-starvation from trust/friction churn, which have opposite fixes. If the data can't make this split, label it as the #1 instrumentation gap.

## Design constraints

- One screen per view, tabbed or scroll-snapped; no dashboard sprawl.
- Clean, quiet styling: neutral background, one accent color for highlights, red reserved exclusively for the leak/dead-pool elements. Large numerals for the headline strip. No pie charts, no gradients, no chart junk.
- Every metric label gets a hover tooltip with its exact formula (numerator/denominator) — the audience includes researchers who will ask.
- A small "data provenance" footer: which files loaded, row counts, duplicates flagged, % rows dropped in cleaning, and export date if known ("data as of …").
- Empty states everywhere: any view lacking data must say what data would light it up. Missing instrumentation is a first-class finding of this analysis.

## Sanity-check anchors from the scenario doc

Beyond the conversion reference numbers above: total pipeline should land near **~1,500 candidates**, with **several hundred** past full verification. If cleaned totals differ wildly from these, flag it — either the exports are partial or the mapping is wrong. (If they differ *somewhat*, that's a finding: "the doc says 1,500; the deduped exports say N.")

## Build order

1. CSV loader + column mapper + cleaning report (methodology log starts here)
2. Funnel view with per-project toggle + leak highlight
3. Headline strip with editable cost input
4. Utilization & concentration view
5. Cohort/time view
6. Dormant drill-down
7. Polish pass (tooltips, provenance footer, projector check)

Stop and hand back to me after step 4 if time is short — 1–4 is a complete diagnostic story. The concentration view moved up because the scenario doc telegraphs it; it is likely the freshest finding available.

## Methodology log format (deliverable #1)

Maintain `METHODOLOGY.md` alongside the build with, per step: input files + row counts → operation + rule applied → output counts → open questions. End with a reconciliation table for any figures that don't align across exports. Write it as we go, not retroactively.

## Test data

Before real exports arrive, generate a synthetic CSV: ~800 designers across two projects ("Project A", "Project B"), three channels (cold, referral, inbound), three recruiters, timestamps spanning Feb–Jul 2026, seeded so the funnel roughly reproduces the reference numbers above (17% outreach→apply, ~50% accepted-never-project) with realistic noise, ~5% duplicate rows, mixed date formats, and ~10% missing timestamps. Build against this; the real files replace it via the same loader.
