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

## Step 2 — Navigable raw-data explorer (`scripts/build_explorer.py`)

- Generates `data/raw/funnel.explorer.html`: a single self-contained file embedding the full
  raw pull with tabbed, searchable, hash-linked navigation (pipeline board, experts + full
  profile drill-in, deals, projects/positions, supply requests, fetch manifest).
- The file embeds real personal data (names, emails, rates, comm logs) → it lives in
  `data/raw/` and matches two independent gitignore rules (`data/raw/`, `*.explorer.html`).
- This is a *raw data browsing* aid, deliberately chart-free; the analytical dashboard with
  cleaned/modeled data is a separate later step.
