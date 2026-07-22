#!/usr/bin/env python3
"""Normalize, dedupe (flag — never silently merge), and resolve entities across systems.

Output: one `persons` list — the master spine. Every drop/merge/flag is counted and logged.
"""
import datetime
import re

from ingest import MAPPING

VOCAB = MAPPING["vocab"]

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}
DATE_RE = re.compile(r"(\w+) (\d{1,2}), (\d{4})(?: (\d{1,2}):(\d{2}) (AM|PM))?")


def parse_ts(s):
    """Notion long form ('June 30, 2026 4:27 PM' / 'May 19, 2026') or ISO. None if unparseable."""
    s = (s or "").strip()
    if not s:
        return None
    m = DATE_RE.match(s)
    if m:
        mon, day, yr, hh, mm, ap = m.groups()
        if mon not in MONTHS:
            return None
        h = int(hh) % 12 + (12 if ap == "PM" else 0) if hh else 0
        return datetime.datetime(int(yr), MONTHS[mon], int(day), h, int(mm or 0)).isoformat()
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None).isoformat()
    except ValueError:
        return None


def band(value, table):
    v = (value or "").strip()
    if not v:
        return None, None
    if v in table:
        return tuple(table[v])
    # multi-select ("2-6, 6-10") → widest span
    parts = [p.strip() for p in v.split(",") if p.strip() in table]
    if parts:
        los = [table[p][0] for p in parts]
        his = [table[p][1] for p in parts]
        return (None if any(x is None for x in los) else min(los),
                None if any(x is None for x in his) else max(his))
    return None, None


SCORE_TAGS = {"Engineer", "Offboarded", "Social"}


def parse_score(raw):
    """'3 - Average…' labeled scale, multi-select joins, plus non-score tags.
    Returns (max numeric score or None, sorted tag list)."""
    parts = [p.strip() for p in (raw or "").split(",") if p.strip()]
    nums = [int(p[0]) for p in parts if p[:1].isdigit()]
    tags = sorted({p for p in parts if p in SCORE_TAGS})
    return (max(nums) if nums else None), tags


def norm_spec(raw):
    v = (raw or "").split("(")[0].strip()
    return VOCAB["specialization"].get(v) if v else None


def norm_channel(raw):
    parts = [p.strip() for p in (raw or "").split(",") if p.strip()]
    mapped = [VOCAB["channel"].get(p) for p in parts]
    mapped = [m for m in mapped if m]
    return (mapped[0] if mapped else None), parts


def clean_notion(records, log):
    out, bad_ts = [], 0
    country_map = VOCAB.get("country", {})
    for r in records:
        score, score_tags = parse_score(r["portfolio_score"])
        ts = parse_ts(r["submission_ts"])
        if r["submission_ts"] and not ts:
            bad_ts += 1
        rate_lo, rate_hi = band(r["rate_band"], VOCAB["rate_band"])
        hrs_lo, hrs_hi = band(r["hours_band"], VOCAB["hours_band"])
        yrs_lo, yrs_hi = band(r["years_band"], VOCAB["years_band"])
        channel, channel_all = norm_channel(r["channel_raw"])
        out.append({
            "email": r["email"].lower(),
            "first_name": r["first_name"], "last_name": r["last_name"],
            "name": f'{r["first_name"]} {r["last_name"]}'.strip(),
            "phone": re.sub(r"\D", "", r["phone"] or ""),
            "linkedin_url": r["linkedin_url"].rstrip("/").lower(),
            "portfolio_url": r["portfolio_url"], "github_url": r["github_url"],
            "has_resume": bool(r["resume"]),
            "channel": channel, "channel_all": channel_all,
            "referrer": r["referrer_team"] or r["referrer_other"] or None,
            "status_raw": r["status_raw"],
            "member_flag": r["member_flag"] or None,
            "portfolio_review": VOCAB["portfolio_review"].get(r["portfolio_review_raw"]),
            "portfolio_score": score, "score_tags": score_tags,
            "country": country_map.get(r["country_raw"], r["country_raw"]) or None,
            "specialization": norm_spec(r["specialization_raw"]),
            "rate_min": rate_lo, "rate_max": rate_hi,
            "hours_min": hrs_lo, "hours_max": hrs_hi,
            "years_min": yrs_lo, "years_max": yrs_hi,
            "ai_comfort": int(r["ai_comfort"]) if r["ai_comfort"] else None,
            "tools": [t.strip() for t in (r["tools_raw"] or "").split(",") if t.strip()],
            "ratings": {k.removeprefix("rating_"): float(r[k]) for k in
                        ("rating_three_d", "rating_brand", "rating_digital_ui", "rating_frontend",
                         "rating_illustration", "rating_motion", "rating_office") if r[k]},
            "submission_ts": ts,
            "initial_email_sent": r["initial_email_sent"] or None,
            "last_contact": parse_ts(r["last_contact"]),
            "latest_comm": r["latest_comm"] or None,
        })
    log(f"normalize: {len(out)} rows, unparseable timestamps: {bad_ts}")
    return out


def dedupe_notion(rows, log):
    """Email is identity. Same-email rows collapse (keep latest ts, union non-null fields).
    Same-name/different-email pairs are FLAGGED, not merged."""
    by_email = {}
    no_email = []
    for r in rows:
        (by_email.setdefault(r["email"], []) if r["email"] else no_email).append(r)  # noqa: expression-statement pattern
    merged, dup_groups = [], 0
    for email, grp in by_email.items():
        if len(grp) == 1:
            merged.append(grp[0])
            continue
        dup_groups += 1
        grp.sort(key=lambda r: r["submission_ts"] or "")
        keep = dict(grp[-1])                       # latest submission wins
        for other in grp[:-1]:
            for k, v in other.items():
                if not keep.get(k) and v:
                    keep[k] = v                    # union non-null fields
        keep["dup_of_rows"] = len(grp)
        merged.append(keep)
    log(f"dedupe: {len(rows)} rows -> {len(merged)} unique emails "
        f"({dup_groups} same-email groups collapsed, rule: latest submission + union of non-null fields) "
        f"+ {len(no_email)} rows with NO email kept as singletons")
    merged.extend(no_email)

    # flag (not merge) same-name different-email candidates
    by_name = {}
    for r in merged:
        if r["name"]:
            by_name.setdefault(r["name"].lower(), []).append(r)
    flagged = 0
    for name, grp in by_name.items():
        if len(grp) > 1:
            flagged += len(grp)
            for r in grp:
                r["possible_dup_name"] = name
    log(f"dedupe: {flagged} rows flagged as possible same-person (same first+last, different email) — NOT merged")
    return merged


def resolve(notion, portal, log):
    """One person per human across systems. Key: email; portal profile attached where matched."""
    full = portal["experts_full"]
    directory_ids = {e["id"] for e in portal["experts_index"]}
    deals_by_expert = {}
    for d in portal["deals"].values():
        deals_by_expert.setdefault(d["expert_id"], []).append(d)

    portal_by_email = {}
    for eid, prof in full.items():
        em = ((prof.get("expert") or {}).get("email") or "").strip().lower()
        if em:
            portal_by_email.setdefault(em, eid)

    persons, matched = [], set()
    for r in notion:
        eid = portal_by_email.get(r["email"]) if r["email"] else None
        if eid:
            matched.add(eid)
        persons.append(make_person(r, eid, full, deals_by_expert, directory_ids))
    portal_only = [eid for eid in full if eid not in matched]
    for eid in portal_only:
        persons.append(make_person(None, eid, full, deals_by_expert, directory_ids))

    log(f"resolve: {len(persons)} persons = {len(notion)} notion "
        f"({len(matched)} matched to portal by email) + {len(portal_only)} portal-only")
    log(f"resolve: of portal-only, {sum(1 for e in portal_only if e not in directory_ids)} "
        f"are board-only experts (absent from directory)")
    return persons


def make_person(notion_row, expert_id, full, deals_by_expert, directory_ids):
    p = {"sources": [], "expert_id": expert_id}
    if notion_row:
        p.update(notion_row)
        p["sources"].append("notion")
    if expert_id:
        prof = full[expert_id]
        e = prof.get("expert") or {}
        p["sources"].append("portal")
        p.setdefault("email", (e.get("email") or "").lower())
        p.setdefault("name", f'{e.get("first_name") or ""} {e.get("last_name") or ""}'.strip())
        p["portal"] = {
            "community_stage": e.get("community_stage"),
            "country": e.get("country"),
            "source": e.get("source"),
            "portfolio_review": VOCAB["portfolio_review"].get(str(e.get("portfolio_review") or "").title()),
            "portfolio_score": e.get("portfolio_score"),
            "primary_specialization": e.get("primary_specialization"),
            "availability_status": prof.get("availability_status"),
            "lifetime_hours": (prof.get("rollups") or {}).get("lifetime_hours") or 0,
            "in_directory": expert_id in directory_ids,
            "deals": [{
                "id": d["id"], "project_id": d["project_id"], "stage": d["stage"],
                "rate": d["rate"], "stage_entered_at": d.get("stage_entered_at"),
                "created_at": d.get("created_at"),
            } for d in deals_by_expert.get(expert_id, [])],
        }
        # cross-system disagreement flags (recorded, not resolved)
        if notion_row:
            np, pp = p.get("portfolio_review"), p["portal"]["portfolio_review"]
            if np and pp and np != pp:
                p["conflict_portfolio_review"] = {"notion": np, "portal": pp}
    p.setdefault("channel", (p.get("portal") or {}).get("source"))
    return p
