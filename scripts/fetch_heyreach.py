#!/usr/bin/env python3
"""Pull HeyReach (LinkedIn outreach) data into data/raw/heyreach/ (gitignored).

Purpose: light up the funnel's two dead stages — `outreached` (campaign leads contacted)
and `responded` (conversations/replies) — and join them to the person spine via
linkedin_url / email.

Reads HEYREACH_API_KEY from .env. Base: https://api.heyreach.io/api/public, auth X-API-KEY.
HeyReach's API is known to 404 on some documented endpoints; every endpoint outcome
(ok / 404 / error) is recorded in heyreach_manifest.json rather than hidden.
"""
import json
import pathlib
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw" / "heyreach"
OUT.mkdir(parents=True, exist_ok=True)

BASE = "https://api.heyreach.io/api/public"
PAGE = 100

env = {}
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
KEY = env.get("HEYREACH_API_KEY", "")

manifest = {"fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "base": BASE, "endpoints": {}, "counts": {}}


def call(path, body=None, method="POST", retries=3):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body or {}).encode() if method == "POST" else None,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json", "X-API-KEY": KEY},
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                txt = resp.read().decode()
                manifest["endpoints"][path] = "ok"
                return json.loads(txt) if txt.strip() else {}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                manifest["endpoints"][path] = "404 (endpoint not available on this plan/version)"
                return None
            if e.code == 429:               # rate limit — HeyReach allows ~300 req/min
                time.sleep(5 * (attempt + 1))
                continue
            if attempt == retries - 1:
                manifest["endpoints"][path] = f"HTTP {e.code}: {e.read().decode()[:200]}"
                return None
            time.sleep(2 ** attempt)
        except Exception as e:  # noqa: BLE001
            if attempt == retries - 1:
                manifest["endpoints"][path] = f"error: {e}"
                return None
            time.sleep(2 ** attempt)


def paged(path, body_extra=None, items_key="items"):
    """HeyReach paginates POST bodies with offset/limit; responses carry totalCount."""
    out, offset = [], 0
    while True:
        body = {"offset": offset, "limit": PAGE, **(body_extra or {})}
        resp = call(path, body)
        if resp is None:
            return None if offset == 0 else out
        chunk = resp.get(items_key) if isinstance(resp, dict) else resp
        if chunk is None and isinstance(resp, dict):          # some endpoints use other keys
            for k in ("campaigns", "leads", "conversations", "lists", "data"):
                if isinstance(resp.get(k), list):
                    chunk = resp[k]
                    break
        if not chunk:
            return out
        out.extend(chunk)
        total = resp.get("totalCount") if isinstance(resp, dict) else None
        offset += PAGE
        if total is not None and offset >= total:
            return out
        if total is None and len(chunk) < PAGE:
            return out


def save(name, obj):
    p = OUT / name
    p.write_text(json.dumps(obj, indent=1))
    print(f"  wrote {p.relative_to(ROOT)} ({p.stat().st_size:,} bytes)")


def main():
    if not KEY:
        raise SystemExit("HEYREACH_API_KEY missing from .env — add it and rerun.")

    print("== auth check ==")
    ok = call("/auth/CheckApiKey", method="GET")
    print(f"  CheckApiKey: {manifest['endpoints'].get('/auth/CheckApiKey')}"
          + (f" -> {ok}" if ok not in (None, {}) else ""))
    if manifest["endpoints"].get("/auth/CheckApiKey") != "ok":
        save("heyreach_manifest.json", manifest)
        raise SystemExit("API key rejected — manifest written; get a valid key from HeyReach Settings → API.")

    print("== campaigns ==")
    campaigns = paged("/campaign/GetAll") or []
    save("campaigns.json", campaigns)

    print("== lead lists ==")
    lists_ = paged("/list/GetAll") or []
    save("lists.json", lists_)

    print(f"== leads per campaign x{len(campaigns)} ==")
    leads = {}
    for c in campaigns:
        cid = c.get("id")
        got = paged("/campaign/GetLeadsFromCampaign", {"campaignId": cid})
        if got is None:                                   # endpoint 404s → try lead lists route
            break
        leads[str(cid)] = got
        print(f"  campaign {cid}: {len(got)} leads")
    save("campaign_leads.json", leads)

    print("== overall stats ==")
    stats = call("/stats/GetOverallStats", {"accountIds": [], "campaignIds": [c.get("id") for c in campaigns],
                                            "startDate": "2025-01-01T00:00:00Z",
                                            "endDate": manifest["fetched_at_utc"]})
    save("stats.json", stats or {})

    print("== conversations (inbox) ==")
    convos = paged("/inbox/GetConversationsV2", {"filters": {}}) or []
    save("conversations.json", convos)

    manifest["counts"] = {"campaigns": len(campaigns), "lists": len(lists_),
                          "campaigns_with_leads": len(leads),
                          "leads_total": sum(len(v) for v in leads.values()),
                          "conversations": len(convos)}
    save("heyreach_manifest.json", manifest)
    print("done — see heyreach_manifest.json for endpoint outcomes.")


if __name__ == "__main__":
    main()
