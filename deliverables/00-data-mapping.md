# Data mapping — canonical schema across Notion + portal

Two sources, one person-level spine. Join key: normalized email (768/838 portal directory
experts match a Notion application row). Encoded in `pipeline/mapping.yml`; this file is the
human-readable spec.

## Person-level field mapping

| Canonical field | Notion CSV (`_all`) column | Portal field (`experts_*`) | Transform / notes |
|---|---|---|---|
| `person_key` | `What's your email?` | `expert.email` | lowercase, trim — the join key across systems |
| `first_name` | `First Name` | `expert.first_name` | trim; fall back to splitting full name |
| `last_name` | `Last Name` | `expert.last_name` | " |
| `full_name` | `What's your full name (first & last)?` | derived | trim, collapse whitespace; fallback matching only |
| `phone` | `What is your WhatsApp phone number?` | `expert.whatsapp_phone` | normalize digits; matching aid only |
| `linkedin_url` | `LinkedIn URL` | `expert.linkedin_url` | normalize scheme/trailing slash — secondary join key |
| `portfolio_url` | `Portfolio or Github URL` | `expert.portfolio_url` | — |
| `github_url` | `URL to your github` | `expert.github_url` | — |
| `resume` | `Resume (PDF only)` | `expert.resume_url` | presence flag only (files not fetched) |
| `country` | — *(not in Notion)* | `expert.country` | portal-only |
| `channel` | `How did you hear about Taste?` | `expert.source` | unify vocab: `Contra/Behance/LinkedIn/…` ↔ `linkedin/referral/website/x/…` |
| `referrer` | `Who on the team referred you?` + `Who referred you? ` (trailing space) | `expert.referred_by` | coalesce both Notion columns; record disagreements |
| `submission_ts` | `Submission time` | — | `"June 30, 2026 4:27 PM"` → ISO; **the `applied` timestamp** |
| `status_raw_notion` | `General Status` | — | verbatim; feeds stage mapping below |
| `member_flag` | `Are you currently a member of the TasteMakers Community?` | — | Yes/No/blank (84% blank — recorded) |
| `community_stage` | — | `expert.community_stage` | portal lifecycle enum, verbatim |
| `portfolio_review` | `Portfolio Approval` | `expert.portfolio_review` | both exist — reconcile, record disagreements |
| `portfolio_score` | `Recruiting Portfolio Score` | `expert.portfolio_score` | " |
| `specialization` | `What is your specialization?` | `expert.primary_specialization` | Notion long label → portal enum (`digital_ui`, `three_d`, `brand`, `motion`, `illustration`, `frontend`, `office`) |
| `rating_<dim>` ×7 | `Rating: 3D…` / `Brand…` / `Digital/UI…` / `Frontend…` / `Illustration…` / `Motion…` / `Office…` | `ratings` per-dim | 1–4 ints; same enum keys as specialization |
| `tools` | `Which tools are you an expert in? …` | `expert.tools` | split comma list; union on merge |
| `years_experience` | `Years of design experience (years)` | `expert.years_experience` | int |
| `ai_comfort` | `How comfortable are you using AI/LLM tools… (1–4)` | — | Notion-only, int |
| `rate_min` / `rate_max` | `What is the range of your typical hourly rate (USD)?` | `expert.rate_min` / `rate_max` | `"$60-$80"` → 60/80; open bands → min only |
| `hours_available` | `How many hours per week are you typically available…` | `expert.hours_min/max` | band → min/max (`"40+"` → 40/null) |
| `initial_email_sent` | `Initial Email Sent` | — | Yes/No |
| `last_contact` | `Last Contact Date` | `last_contact_at` | date-only vs timestamp; only 3 Notion rows populated — recorded |
| `latest_comm` | `Latest comm` | `comm_log` / `messages` | free text; kept for dormant drill-down, not parsed |
| *(dropped, logged)* | `Property`, `Files & media`, `Please Specify "Other"`, `Presentation Type Expertise` | — | near-empty / attachment metadata — drop counts in METHODOLOGY |

Deal-level portal fields (`stage`, `rate`, `start_date`, compliance columns, `stage_entered_at`)
aggregate onto the person during stage assignment; they are not person fields.

## Stage mapping (canonical 10-stage funnel)

| Canonical stage | Notion `General Status` | Portal signal | Confidence |
|---|---|---|---|
| 1 `outreached` | `Outreach`, `Not started` | `community_stage: sourced` | firm |
| 2 `responded` | — | — | **not instrumented** |
| 3 `applied` | any row with `Submission time` (all 2,478) | `community_stage: applicant` | firm |
| 4 `assessment_taken` | — | — | **not instrumented** (portal test fields proven empty) |
| 5 `assessment_passed` | `Portfolio Approval: Yes` *(proxy)* | `portfolio_review: yes` | open call |
| 6 `accepted` | `Welcome Sent` | `community_stage: accepted` | open call |
| 7 `project_applied` | — | has ≥1 deal (board row) | firm |
| 8 `staffed` | `Active`? | deal stage `active`/`paused`/`ended` | open call |
| 9 `first_billable` | — | `lifetime_hours > 0` — **currently 0 for all 975 profiles** → falls back to deal stage `active`+ | open call |
| 10 `second_contract` | — | ≥2 deals reaching `active`+ | firm |
| terminal reject | `Portfolio Rejected`, `DNU` | deal `rejected`; `community_stage: rejected/removed` | firm |
| dormant | `Inactive` | deal `paused` | firm |

Open calls get counts computed under each candidate rule before locking; the chosen rule and
the rejected alternative both go in METHODOLOGY.md.
