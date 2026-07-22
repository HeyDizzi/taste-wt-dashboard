#!/usr/bin/env python3
"""Ingest raw exports per mapping.yml. Loud about anything unmapped; drops nothing silently."""
import csv
import json
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
MAPPING = yaml.safe_load((ROOT / "pipeline" / "mapping.yml").read_text())


def load_notion(log):
    cfg = MAPPING["notion"]
    rows = list(csv.DictReader(open(ROOT / cfg["file"], encoding="utf-8-sig")))
    base = list(csv.DictReader(open(ROOT / cfg["subset_check_against"], encoding="utf-8-sig")))

    colmap, drop = cfg["columns"], set(cfg["drop"])
    raw_cols = set(rows[0].keys())
    unmapped = raw_cols - set(colmap) - drop
    if unmapped:
        log(f"!! UNMAPPED NOTION COLUMNS (ignored until mapped): {sorted(unmapped)}")
    missing = set(colmap) - raw_cols
    if missing:
        log(f"!! MAPPED COLUMNS ABSENT FROM FILE: {sorted(missing)}")
    for d in drop:
        n = sum(1 for r in rows if r.get(d, "").strip())
        log(f"dropped column {d!r}: {n}/{len(rows)} rows had a value")

    # subset check: base export must not contain rows the _all export lacks
    key = lambda r: (r.get("What’s your email?", "").strip().lower(), r.get("Submission time", "").strip())  # noqa: E731
    extra = {key(r) for r in base} - {key(r) for r in rows}
    log(f"subset check: base rows not in _all = {len(extra)}"
        + (" !! BASE IS NOT A SUBSET — investigate" if extra else " (ok, _all is authoritative)"))

    records = [{canon: r.get(src, "").strip() for src, canon in colmap.items()} for r in rows]
    log(f"notion ingest: {len(records)} records, {len(colmap)} mapped columns")
    return records


def load_heyreach(log):
    """HeyReach outreach data — optional: pipeline runs without it (stages stay not-instrumented)."""
    hr = RAW / "heyreach"
    if not (hr / "campaign_leads.json").exists():
        log("heyreach: no data — outreached/responded stay not instrumented")
        return None
    leads = json.loads((hr / "campaign_leads.json").read_text())
    campaigns = json.loads((hr / "campaigns.json").read_text())
    flat = [dict(l, campaign_id=cid) for cid, ls in leads.items() for l in ls]
    log(f"heyreach ingest: {len(campaigns)} campaigns, {len(flat)} leads")
    return {"campaigns": campaigns, "leads": flat}


def load_portal(log):
    p = {
        "experts_index": json.loads((RAW / "experts_index.json").read_text())["data"],
        "experts_full": json.loads((RAW / "experts_full.json").read_text()),
        "deals": json.loads((RAW / "deals_full.json").read_text()),
        "board": json.loads((RAW / "pipeline_board.json").read_text()),
        "projects": json.loads((RAW / "projects.json").read_text()),
        "positions": json.loads((RAW / "positions.json").read_text()),
        "manifest": json.loads((RAW / "fetch_manifest.json").read_text()),
    }
    log(f"portal ingest: {len(p['experts_index'])} directory experts, {len(p['experts_full'])} full profiles, "
        f"{len(p['deals'])} deals, {len(p['projects'])} projects, {len(p['positions'])} positions")
    return p
