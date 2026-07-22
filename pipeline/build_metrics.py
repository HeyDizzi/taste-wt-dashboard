#!/usr/bin/env python3
"""Assign canonical funnel stages and emit all dashboard metrics to data/processed/."""
import collections
import datetime

from ingest import MAPPING

STAGES = MAPPING["stages"]["order"]
NOT_INSTRUMENTED = set(MAPPING["stages"]["not_instrumented"])
STAFFED_STAGES = {"active", "paused", "ended"}


def furthest_stage(p):
    """Return (stage, terminal_flag). Furthest canonical stage per mapping.yml rules."""
    port = p.get("portal") or {}
    deals = port.get("deals", [])
    status = p.get("status_raw") or ""
    cs = port.get("community_stage")

    staffed_deals = [d for d in deals if d["stage"] in STAFFED_STAGES]
    reached = "outreached"  # floor: everyone in either system was at least outreached
    if (p.get("outreach") or {}).get("replied"):
        reached = "responded"
    if p.get("submission_ts") or cs == "applicant" or "notion" in p["sources"]:
        reached = "applied"
    if (p.get("portfolio_review") == "yes") or (port.get("portfolio_review") == "yes"):
        reached = "assessment_passed"
    if status in ("Welcome Sent", "Active", "Inactive") or cs == "accepted":
        reached = "accepted"
    if deals:
        reached = "project_applied"
    if staffed_deals:
        reached = "staffed"
    if port.get("lifetime_hours", 0) > 0:
        reached = "first_billable"
    if len(staffed_deals) >= 2:
        reached = "second_contract"

    terminal = None
    if status in ("Portfolio Rejected", "DNU") or cs in ("rejected", "removed"):
        terminal = "rejected_screen"
    elif status == "Inactive":
        terminal = "dormant"
    return reached, terminal


def rule_variants(persons):
    """Counts under each candidate rule for the open mapping calls — for human review."""
    port = lambda p: p.get("portal") or {}  # noqa: E731
    deals = lambda p: port(p).get("deals", [])  # noqa: E731
    staffed = lambda p: [d for d in deals(p) if d["stage"] in STAFFED_STAGES]  # noqa: E731
    return {
        "accepted": {
            "welcome_sent_only": sum(1 for p in persons if (p.get("status_raw") == "Welcome Sent")),
            "welcome_or_active_or_inactive (chosen)": sum(1 for p in persons if p.get("status_raw") in ("Welcome Sent", "Active", "Inactive")),
            "portal_community_accepted": sum(1 for p in persons if port(p).get("community_stage") == "accepted"),
            "either_system (effective)": sum(1 for p in persons if p.get("status_raw") in ("Welcome Sent", "Active", "Inactive") or port(p).get("community_stage") == "accepted"),
        },
        "assessment_passed_proxy": {
            "portfolio_yes_either (chosen)": sum(1 for p in persons if p.get("portfolio_review") == "yes" or port(p).get("portfolio_review") == "yes"),
            "portfolio_yes_notion_only": sum(1 for p in persons if p.get("portfolio_review") == "yes"),
            "disagreements_flagged": sum(1 for p in persons if p.get("conflict_portfolio_review")),
        },
        "staffed": {
            "deal_ever_active_paused_ended (chosen)": sum(1 for p in persons if staffed(p)),
            "notion_status_Active": sum(1 for p in persons if p.get("status_raw") == "Active"),
            "deal_currently_active": sum(1 for p in persons if any(d["stage"] == "active" for d in deals(p))),
        },
        "first_billable": {
            "lifetime_hours_gt_0 (chosen, currently unmeasurable)": sum(1 for p in persons if port(p).get("lifetime_hours", 0) > 0),
            "fallback_equals_staffed": sum(1 for p in persons if staffed(p)),
        },
    }


def build(persons, portal, log):
    for p in persons:
        p["stage"], p["terminal"] = furthest_stage(p)

    # ---- funnel: applied+ stages use at-least-furthest (sequential in-system); the outreach
    # stages use DIRECT EVIDENCE counts (contacted / replied), because applying does not imply
    # having been outreached — entry channels other than LinkedIn outreach exist.
    idx = {s: i for i, s in enumerate(STAGES)}
    has_outreach = any(p.get("outreach") for p in persons)
    def funnel_for(sub):
        f = {}
        if has_outreach:
            f["outreached"] = sum(1 for p in sub if (p.get("outreach") or {}).get("contacted"))
            f["responded"] = sum(1 for p in sub if (p.get("outreach") or {}).get("replied"))
        for s in STAGES:
            if s in NOT_INSTRUMENTED or s in f:
                continue
            f[s] = sum(1 for p in sub if p.get("stage") and idx[p["stage"]] >= idx[s])
        return f
    still_dark = NOT_INSTRUMENTED - ({"outreached", "responded"} if has_outreach else set())
    funnel = {
        "combined": funnel_for(persons),
        "by_channel": {ch: funnel_for([p for p in persons if p.get("channel") == ch])
                       for ch in sorted({p.get("channel") for p in persons if p.get("channel")})},
        "not_instrumented": sorted(still_dark),
        "terminal": dict(collections.Counter(p["terminal"] for p in persons if p["terminal"])),
        "outreach_note": "outreached/responded = LinkedIn outreach evidence (HeyReach); "
                         "applied+ includes all entry channels" if has_outreach else None,
    }
    # biggest absolute leak between measured adjacent stages
    measured = [s for s in STAGES if s in funnel["combined"]]
    losses = [{"from": a, "to": b, "lost": funnel["combined"][a] - funnel["combined"][b]}
              for a, b in zip(measured, measured[1:])]
    funnel["biggest_leak"] = max(losses, key=lambda x: x["lost"])
    funnel["transitions"] = losses

    # ---- headline metrics
    accepted = [p for p in persons if idx[p["stage"]] >= idx["accepted"]]
    staffed_plus = [p for p in accepted if idx[p["stage"]] >= idx["staffed"]]
    vetted_never_staffed = [p for p in accepted if idx[p["stage"]] < idx["staffed"]]
    active_now = [p for p in persons if any(d["stage"] == "active" for d in (p.get("portal") or {}).get("deals", []))]
    headline = {
        "vetted_never_staffed": len(vetted_never_staffed),
        "accepted_total": len(accepted),
        "cost_per_vetted_default": 500,           # editable in UI; FP&A to confirm
        "activation_rate_proxy": round(len(active_now) / len(accepted), 4) if accepted else None,
        "activation_note": "proxy = on an active deal now; billable hours not instrumented",
        "median_days_to_staffed": median_days_to_staffed(staffed_plus),
        "r2c": None, "r2c_note": "first_billable not instrumented; second_contract measured off staffed deals",
        "second_contract": sum(1 for p in persons if p["stage"] == "second_contract"),
    }

    # ---- monthly cohorts by submission date (application month)
    cohorts = collections.defaultdict(lambda: collections.Counter())
    for p in persons:
        if p.get("submission_ts"):
            cohorts[p["submission_ts"][:7]][p["stage"]] += 1
    cohort_out = [{"month": m, "stages": dict(c), "total": sum(c.values())}
                  for m, c in sorted(cohorts.items())]

    # ---- dormant pool drill-down
    today = datetime.date(2026, 7, 22)
    dormant = []
    for p in vetted_never_staffed:
        port = p.get("portal") or {}
        n_deals = len(port.get("deals", []))
        dormant.append({
            "name": p.get("name"), "email": p.get("email"),
            "channel": p.get("channel"), "specialization": p.get("specialization") or port.get("primary_specialization"),
            "portfolio_score": p.get("portfolio_score") or port.get("portfolio_score"),
            "rate_min": p.get("rate_min"), "rate_max": p.get("rate_max"),
            "applied": p.get("submission_ts", "")[:10] if p.get("submission_ts") else None,
            "days_since_applied": (today - datetime.date.fromisoformat(p["submission_ts"][:10])).days if p.get("submission_ts") else None,
            "availability": port.get("availability_status"),
            "split": "offered_not_converted" if n_deals else "never_offered",
            "deal_count": n_deals,
        })
    dormant.sort(key=lambda d: -(d["days_since_applied"] or 0))
    dormant_split = dict(collections.Counter(d["split"] for d in dormant))

    # ---- utilization proxies (billable hours not instrumented — deal counts stand in)
    availability = collections.Counter()
    active_per_expert = collections.Counter()
    for p in persons:
        port = p.get("portal") or {}
        if port.get("availability_status"):
            availability[port["availability_status"]] += 1
        n_active = sum(1 for d in port.get("deals", []) if d["stage"] == "active")
        if n_active:
            active_per_expert[p.get("expert_id")] = n_active
    deal_concentration = {
        "active_now": len(active_per_expert),
        "multi_active": sum(1 for v in active_per_expert.values() if v > 1),
    }

    # ---- provenance
    provenance = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "persons_total": len(persons),
        "sources": dict(collections.Counter("+".join(p["sources"]) for p in persons)),
        "same_email_rows_collapsed": sum(p.get("dup_of_rows", 1) - 1 for p in persons),
        "possible_same_name_flagged": sum(1 for p in persons if p.get("possible_dup_name")),
        "portfolio_review_conflicts": sum(1 for p in persons if p.get("conflict_portfolio_review")),
        "board_only_experts": sum(1 for p in persons if p.get("portal") and not p["portal"]["in_directory"]),
        "portal_fetched_at": portal["manifest"].get("fetched_at_utc"),
        "anchors": {
            "scenario_doc_candidates": "~1500", "observed_persons": len(persons),
            "scenario_accepted_never_project": "~50%",
            "observed": f"{len(vetted_never_staffed)}/{len(accepted)}",
        },
    }
    if has_outreach:
        contacted = [p for p in persons if (p.get("outreach") or {}).get("contacted")]
        applied_from_outreach = sum(1 for p in contacted if idx.get(p["stage"], -1) >= idx["applied"])
        replied = [p for p in contacted if p["outreach"].get("replied")]
        applied_from_replied = sum(1 for p in replied if idx.get(p["stage"], -1) >= idx["applied"])
        provenance["anchors"].update({
            "scenario_outreach_to_apply": "~17%",
            "observed_outreach_to_apply": f"{applied_from_outreach}/{len(contacted)} = {round(100 * applied_from_outreach / len(contacted))}%" if contacted else "n/a",
            "scenario_responder_to_apply": "~37%",
            "observed_responder_to_apply": f"{applied_from_replied}/{len(replied)} = {round(100 * applied_from_replied / len(replied))}%" if replied else "n/a",
        })

    log(f"stages assigned: {dict(collections.Counter(p['stage'] for p in persons).most_common())}")
    log(f"biggest leak: {funnel['biggest_leak']}")
    log(f"dormant split: {dormant_split}")
    return {
        "funnel": funnel, "headline": headline, "cohorts": cohort_out,
        "dormant": dormant, "dormant_split": dormant_split,
        "availability": dict(availability), "deal_concentration": deal_concentration,
        "rule_variants": rule_variants(persons), "provenance": provenance,
    }


def median_days_to_staffed(staffed_persons):
    ds = []
    for p in staffed_persons:
        if not p.get("submission_ts"):
            continue
        starts = [d["stage_entered_at"] or d["created_at"] for d in (p.get("portal") or {}).get("deals", [])
                  if d["stage"] in STAFFED_STAGES and (d["stage_entered_at"] or d["created_at"])]
        if starts:
            t0 = datetime.datetime.fromisoformat(p["submission_ts"])
            t1 = min(datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None) for s in starts)
            if t1 >= t0:
                ds.append((t1 - t0).days)
    if not ds:
        return None
    ds.sort()
    return ds[len(ds) // 2]
