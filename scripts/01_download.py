"""Download the ヒグマ出没マップ of Kamisunagawa Town (R6, R7, R8) from the BODIK open data catalogue.

Each fiscal year is its own catalogue entry with one CSV. Saves each entry's metadata (package_show)
and CSV as served, with sha256 and the Last-Modified, in data/raw/<version>/MANIFEST.json. Stops when
an entry does not say cc-by-40-intl or has not exactly one CSV. The version is the UTC date of the run.

    uv run python scripts/01_download.py [--version 2026-10-26]
"""

import argparse
import datetime as dt
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

import kami as k

ROOT = Path(__file__).parents[1]
UA = "kamisunagawa-higuma-sighting/0.1 (+https://github.com/yuiseki/kamisunagawa-higuma-sighting)"


def get(url: str) -> tuple[bytes, dict]:
    with urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120
    ) as r:
        return r.read(), {h.lower(): v for h, v in r.headers.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=dt.datetime.now(dt.UTC).strftime("%Y-%m-%d"))
    args = ap.parse_args()
    raw = ROOT / "data" / "raw" / args.version
    raw.mkdir(parents=True, exist_ok=True)
    files, entries = {}, {}
    for key, (pid, fy, _, _) in k.SOURCES.items():
        time.sleep(1)
        body, _ = get(k.api_package(pid))
        pkg = json.loads(body)["result"]
        if pkg["license_id"] != k.LICENSE_ID:
            raise SystemExit(f"{pid}: license_id is {pkg['license_id']!r}: stopping")
        csvs = [r for r in pkg["resources"] if r["format"] == "CSV"]
        if len(csvs) != 1:
            raise SystemExit(f"{pid}: expected one CSV, found {len(csvs)}")
        r = csvs[0]
        (raw / f"{key}_package.json").write_bytes(body)
        time.sleep(1)
        data, h = get(r["url"])
        name = f"{key}_{r['url'].rsplit('/', 1)[1]}"
        (raw / name).write_bytes(data)
        files[f"{key}_package.json"] = {
            "url": k.api_package(pid),
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
        }
        files[name] = {"url": r["url"], "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                       "last_modified": h.get("last-modified")}  # fmt: skip
        entries[key] = {
            "package": pid, "page": k.page(pid), "title": pkg["title"], "fiscal_year": fy,
            "metadata_modified": pkg["metadata_modified"], "organization": pkg["organization"]["title"],
            "csv": name, "resource_name": r["name"], "resource_last_modified": r["last_modified"],
        }  # fmt: skip
        print(key, pkg["title"], len(data))
    manifest = {
        "retrieved": args.version,
        "license_id": k.LICENSE_ID,
        "entries": entries,
        "files": files,
    }
    (raw / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
