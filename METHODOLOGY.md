# METHODOLOGY

Running log of every data-handling step, written as the work happens. Counts are stated
before/after each operation; disagreements between sources are recorded, not silently resolved.

## Step 0 — Data source discovery (2026-07-22 ~10:35)

- Expected source per brief: manual CSV exports from Dave. Actual source available: the
  **taste-portal MCP server** (`https://api-portal.tastelabs.com/mcp/`, server v1.28.1),
  a live API over the recruiting portal — projects, experts directory, positions, pipeline
  board (deals), supply requests, test submissions.
- Auth: per-user portal API key (Bearer `tpk_…`), stored in `.env` (gitignored). The first
  configured key was rejected (HTTP 401); replaced with a working key supplied by Hudson.
- Data protection set up **before any data was fetched**: `.gitignore` committed first, covering
  `data/raw/`, `.env`, and any generated file embedding real data (`*.explorer.html`).
  Verified with `git check-ignore` prior to the first fetch.

## Step 1 — Full raw pull (2026-07-22 ~10:40, `scripts/fetch_portal_data.py`)

One rerunnable script pulls everything the key can see into `data/raw/` as JSON:

| File | Contents | Count |
|---|---|---|
| `projects.json` | `list_projects` | 8 |
| `positions.json` | `list_positions` | 12 |
| `supply_requests.json` | `list_supply_requests` (open only — server only exposes open ones) | 4 |
| `pipeline_board.json` | `get_pipeline`, all projects | 855 deals across 7 stages |
| `experts_index.json` | `search_experts`, paginated ×100 | 838 experts |
| `experts_full.json` | `get_expert` per id (union of directory ids + board `expert_id`s) | 975, 0 fetch errors |
| `deals_full.json` | `get_deal` per board deal id | 855, 0 fetch errors |
| `test_submissions.json` | `get_test_submission` where the deal shows test evidence | 0 (see below) |
| `fetch_manifest.json` | timestamp, per-file counts, and **every per-id fetch error** | — |

Board stage counts as fetched: invited 198, in_review 53, accepted 208, rejected 235,
active 55, paused 62, ended 44 (= 855).

Decisions / observations logged at fetch time:

- **Board stages ≠ brief stages.** The live board has 7 stages (`invited, in_review, accepted,
  rejected, active, paused, ended`), not the brief's 10 canonical funnel stages. Mapping the
  server's deal-stage vocabulary onto the canonical funnel is a downstream modeling decision,
  recorded when made — not forced at ingest.
- **Board deal rows are slim** (no test/compliance fields, `test_status` null on all 855);
  the per-deal `get_deal` record is the authoritative deal row. Both are kept.
- **Expert id universe**: fetched full profiles for the union of directory ids and any
  `expert_id` referenced on the board, so pipeline candidates missing from the directory
  (or vice versa) surface as a reconciliation finding rather than silently dropping.
- Sanity anchor from the scenario doc: ~1,500 candidates expected. The board shows **855
  deals**; the directory shows **838 experts**. A deal is (expert × project), so neither
  number is directly "candidates" — reconciliation TBD after dedupe. Recorded, not resolved.

Bugs caught and fixed during the pull (both would have silently shrunk the data):

- **Multi-content-block parse bug (mine):** the MCP server returns list-tool results as one
  content block *per item*; the first fetch took only block[0], truncating
  projects/positions/supply to 1 row each. Fixed in `fetch_portal_data.py`; those three
  files refetched (8 / 12 / 4 rows). Experts/pipeline/deals were unaffected (dict payloads).
- **Deal schema names differ from tool docs:** full deal rows use `bg_check_status` /
  `payment_setup_status` (not `background_check_status`/`payment_status`), and there is **no
  `test_status` field** — only `test_score` / `test_submitted_at` / `test_notes` /
  `retest_count`.

Findings recorded at fetch time (leads for the analysis, not conclusions):

- **137 pipeline experts are missing from the experts directory** (975 profile ids = 838
  directory + 137 board-only). Full profiles were fetched for all of them anyway.
- **Test data is not instrumented in this portal**: all 855 deals have null
  `test_score`/`test_submitted_at`, and a stratified sample of 56 `get_test_submission`
  calls (8 per stage, seeded random) returned empty submissions (no definition, no answers).
  Assessment-stage data must come from another source or be flagged "not instrumented".
- Board deal rows all show `test_status: null` and `invite_status: pending` dominates —
  the board's own summary fields look sparsely populated vs. the full deal records.

## Step 1b — Notion export registered (2026-07-22 ~12:55)

- Two manual CSV exports of the Notion "Main Application Database" arrived in the repo root
  (Hudson is a guest in the workspace — API/MCP routes unavailable; export obtained another
  way). **Moved into `data/raw/` immediately** (`notion_main_app_db.csv`,
  `notion_main_app_db_all.csv`) — they were untracked but unprotected at the root.
- Both files: 2,478 data rows. `_all` variant has 36 columns (superset: adds per-dimension
  ratings, tools, years experience, AI comfort, `Latest comm`); base has 23. `_all` is the
  pipeline input pending a subset check.
- Profile at registration: `General Status` = Welcome Sent 823, Portfolio Rejected 548,
  Outreach 452, Not started 370, Active 277, Inactive 7, DNU 1. Emails present 2,444
  (2,375 distinct, 69 dups); **names 2,477 present but only 1,227 distinct — a 50% collision
  rate vs 3% for emails. Anomaly flagged for diagnosis before any dedupe rule is chosen.**
- Cross-system overlap by normalized email: 768/838 portal directory experts appear in the
  Notion export; 843/975 of all fetched profiles.
- Portal-side stats computed for deliverable drafts (from raw, pre-cleaning): accepted in
  directory 553, of which **364 have no deal ever**; 52 experts on an active deal;
  `lifetime_hours` = 0 for all 975 profiles; deal `rate` null on all 855 deals.

## Step 3 — Cleaning pipeline (2026-07-22 ~13:2x, `pipeline/run.py`)

One command: `.venv/bin/python pipeline/run.py` → `data/processed/{persons,metrics}.json`
+ `pipeline_log.txt` (the machine-written version of this section). Key numbers:

- **Ingest**: 2,478 Notion rows, 34 mapped columns; base CSV verified as row-subset of `_all`
  (0 extras) so `_all` is sole input. Dropped columns logged with fill counts; two initially
  "dropped" columns were rescued on inspection:
  - `Property` (2,216 filled) is **country**, misnamed in Notion → mapped.
  - `Recruiting Portfolio Score` is a labeled 1–5 scale with non-score tags
    (`Engineer` 64, `Offboarded` 25, `Social`) and multi-select joins → parsed to
    max-numeric + tag list.
- **Name-collision anomaly resolved**: the "full name" column is the Notion page *title*,
  defaulting to "New submission" localized (`new submission` ×946, `novo envio` ×185,
  `nueva respuesta` ×109, `nouvelle soumission` ×9). Real names = First + Last columns.
  Field renamed `page_title`, excluded from identity.
- **Dedupe** (rule: email = identity; latest submission wins, union of non-null fields):
  2,478 → 2,375 unique emails (64 groups collapsed) + 34 no-email singletons.
  22 rows flagged same-name/different-email (e.g. `isabella@…` vs `isabellaa@…` typo pair) —
  flagged, NOT merged.
- **Entity resolution**: 2,541 persons = 2,409 Notion-side (843 matched to portal by email)
  + 132 portal-only (62 of them board-only, absent from the directory).
- **Semantic finding**: `Outreach`/`Not started` status rows are ~100% filled with
  application answers → everyone in the export APPLIED; "Outreach" records acquisition mode,
  not funnel position. Therefore the observable funnel starts at `applied`; true outreach
  volume (and the doc's ~17% outreach→apply anchor) is not measurable from trial data.
- **Stage assignment** (rules in `mapping.yml`; alternatives + counts in
  `metrics.rule_variants`): furthest-stage distribution — accepted 830, applied 744,
  project_applied 477, assessment_passed 356, staffed 108, second_contract 26.
- **Biggest absolute leak: accepted → project_applied, 830 people lost**
  (1,441 reached at-least-accepted; 611 at-least-project_applied).
- **Dormant pool**: 1,307 vetted-never-staffed = 830 never offered a deal + 477 offered but
  never converted — the demand-starvation vs. friction split is now measurable.
- Reconciliation vs. scenario doc: ~1,500 candidates claimed; observed 2,541 persons
  (recorded, not resolved — the doc may predate recent recruiting waves).

## Step 4 — Dashboard (2026-07-22 ~13:2x, `app/`)

- Static app (no build step) renders `data/processed/metrics.json` only — zero data logic in
  the browser. `make dev` → http://127.0.0.1:8471/app/, keys 1–5 switch views. Deviation from
  the brief's Vite+React plan recorded: cut for scope, the pipeline is the deliverable's core.
- Chart colors follow the validated reference palette (ordinal blue ramps re-validated for
  this app: 5-step light + dark both pass; a 6-step light ramp FAILED adjacent-ΔL, so the
  cohort stack folds `second_contract` into `staffed+`). Red is reserved for leak/dormant.
- Display rule: `outreached` marked not-instrumented after finding that every exported row
  already applied — showing 2,541 "outreached" would have implied outreach volume we don't have.
- Deliverable docs updated from portal-only to cleaned-spine numbers: leak = accepted →
  project contact (−830); dormant pool 1,307 = 830 never-offered + 477 offered-not-converted;
  VAR proxy 52/1,441 = 3.6%.

## Step 2 — Navigable raw-data explorer (`scripts/build_explorer.py`)

- Generates `data/raw/funnel.explorer.html`: a single self-contained file embedding the full
  raw pull with tabbed, searchable, hash-linked navigation (pipeline board, experts + full
  profile drill-in, deals, projects/positions, supply requests, fetch manifest).
- The file embeds real personal data (names, emails, rates, comm logs) → it lives in
  `data/raw/` and matches two independent gitignore rules (`data/raw/`, `*.explorer.html`).
- This is a *raw data browsing* aid, deliberately chart-free; the analytical dashboard with
  cleaned/modeled data is a separate later step.
