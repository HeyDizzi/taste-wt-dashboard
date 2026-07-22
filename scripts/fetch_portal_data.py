#!/usr/bin/env python3
"""Pull every available record from the taste-portal MCP server into data/raw/.

Reads TASTE_PORTAL_KEY / TASTE_PORTAL_URL from .env (never committed).
Output files land in data/raw/ (gitignored). Rerunnable: overwrites in place.
"""
import concurrent.futures as cf
import json
import pathlib
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

env = {}
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
URL = env["TASTE_PORTAL_URL"]
KEY = env["TASTE_PORTAL_KEY"]

_id = 0


def call_tool(name, arguments=None, retries=3):
    """One MCP tools/call round-trip; returns the parsed JSON payload of the tool result."""
    global _id
    _id += 1
    body = json.dumps({
        "jsonrpc": "2.0", "id": _id, "method": "tools/call",
        "params": {"name": name, "arguments": arguments or {}},
    }).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {KEY}",
    })
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode()
            for line in raw.splitlines():
                if line.startswith("data: "):
                    msg = json.loads(line[6:])
                    if "error" in msg:
                        raise RuntimeError(f"{name}: RPC error {msg['error']}")
                    result = msg["result"]
                    if result.get("isError"):
                        raise RuntimeError(f"{name}: tool error {result['content']}")
                    # List-returning tools arrive as one content block PER item.
                    items = [json.loads(c["text"]) for c in result["content"]]
                    return items[0] if len(items) == 1 else items
            raise RuntimeError(f"{name}: no data frame in response")
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def save(name, obj):
    path = RAW / name
    path.write_text(json.dumps(obj, indent=1))
    print(f"  wrote {path.relative_to(ROOT)} ({path.stat().st_size:,} bytes)")


def fan_out(label, fn, ids, workers=8):
    """Run fn(id) concurrently; returns ({id: result}, {id: error})."""
    out, errs = {}, {}
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(fn, i): i for i in ids}
        done = 0
        for fut in cf.as_completed(futures):
            i = futures[fut]
            try:
                out[i] = fut.result()
            except Exception as e:  # noqa: BLE001 — record and continue
                errs[i] = str(e)
            done += 1
            if done % 100 == 0 or done == len(ids):
                print(f"  {label}: {done}/{len(ids)} ({len(errs)} errors)")
    return out, errs


def main():
    manifest = {"fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "source": URL, "counts": {}, "errors": {}}

    print("== singleton lists ==")
    # These three tools return a LIST; a one-item result parses as a bare dict, so coerce.
    as_list = lambda x: x if isinstance(x, list) else [x]  # noqa: E731
    projects = as_list(call_tool("list_projects"))
    positions = as_list(call_tool("list_positions"))
    supply = as_list(call_tool("list_supply_requests"))
    board = call_tool("get_pipeline")
    save("projects.json", projects)
    save("positions.json", positions)
    save("supply_requests.json", supply)
    save("pipeline_board.json", board)

    print("== experts directory (paginated) ==")
    experts_index, page = [], 1
    while True:
        chunk = call_tool("search_experts", {"page": page, "page_size": 100})
        experts_index.extend(chunk["data"])
        if page * chunk["page_size"] >= chunk["total"]:
            break
        page += 1
    save("experts_index.json", {"data": experts_index, "total": len(experts_index)})

    deal_ids = [d["id"] for c in board["columns"] for d in c["deals"]]
    board_expert_ids = {d["expert_id"] for c in board["columns"] for d in c["deals"] if d.get("expert_id")}
    expert_ids = sorted({e["id"] for e in experts_index} | board_expert_ids)

    print(f"== expert detail x{len(expert_ids)} ==")
    experts_full, expert_errs = fan_out("experts", lambda i: call_tool("get_expert", {"expert_id": i}), expert_ids)
    save("experts_full.json", experts_full)

    print(f"== deal detail x{len(deal_ids)} ==")
    deals_full, deal_errs = fan_out("deals", lambda i: call_tool("get_deal", {"deal_id": i}), deal_ids)
    save("deals_full.json", deals_full)

    # Test submissions only where the full deal shows a test in flight/done.
    tested = [i for i, d in deals_full.items()
              if d and (d.get("test_status") or d.get("test_submitted_at") or d.get("test_score") is not None)]
    print(f"== test submissions x{len(tested)} ==")
    subs, sub_errs = fan_out("submissions", lambda i: call_tool("get_test_submission", {"deal_id": i}), tested)
    save("test_submissions.json", subs)

    manifest["counts"] = {
        "projects": len(projects) if isinstance(projects, list) else projects.get("total"),
        "positions": len(positions) if isinstance(positions, list) else positions.get("total"),
        "supply_requests": len(supply) if isinstance(supply, list) else supply.get("total"),
        "pipeline_deals_on_board": board["total"],
        "experts_index": len(experts_index),
        "experts_full": len(experts_full),
        "deals_full": len(deals_full),
        "test_submissions": len(subs),
    }
    manifest["errors"] = {"experts": expert_errs, "deals": deal_errs, "test_submissions": sub_errs}
    save("fetch_manifest.json", manifest)
    print("done.")


if __name__ == "__main__":
    sys.exit(main())
