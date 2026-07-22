#!/usr/bin/env python3
"""One-command pipeline: raw exports -> cleaned persons + metrics in data/processed/.

Usage: .venv/bin/python pipeline/run.py
Every decision it makes is printed AND appended to data/processed/pipeline_log.txt.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_metrics  # noqa: E402
import clean  # noqa: E402
import ingest  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

LOG_LINES = []


def log(msg):
    print(msg)
    LOG_LINES.append(str(msg))


def main():
    log("== ingest ==")
    notion = ingest.load_notion(log)
    portal = ingest.load_portal(log)

    log("== clean ==")
    rows = clean.clean_notion(notion, log)
    rows = clean.dedupe_notion(rows, log)
    persons = clean.resolve(rows, portal, log)

    log("== metrics ==")
    metrics = build_metrics.build(persons, portal, log)

    (OUT / "persons.json").write_text(json.dumps(persons, indent=1))
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=1))
    (OUT / "pipeline_log.txt").write_text("\n".join(LOG_LINES) + "\n")
    log(f"== wrote {OUT / 'persons.json'} ({len(persons)} persons), metrics.json, pipeline_log.txt ==")


if __name__ == "__main__":
    main()
