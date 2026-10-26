"""Write data/README.md (the dataset card), data/LICENSE and data/provenance.yaml.

uv run python scripts/04_card.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).parents[1]
REPO = "kamisunagawa-higuma-sighting"

CARD = """---
license: cc-by-4.0
license_name: cc-by-4.0
license_link: https://creativecommons.org/licenses/by/4.0/legalcode.ja
language:
- ja
tags:
- japan
- hokkaido
- bear
- brown-bear
- wildlife
- geospatial
size_categories:
- n<1K
pretty_name: Brown bear (ヒグマ) sightings of Kamisunagawa Town, Hokkaido
---

# {repo}

The brown bear (ヒグマ, written 羆 in the records) sighting maps of Kamisunagawa Town (上砂川町,
Sorachi District, Hokkaido), published by the town in the BODIK open data catalogue, one entry per
fiscal year: {rows:,} records from {first} to {last} (R6 to R8). As GeoParquet. A very small
municipality's data; the file is the whole of it.

## Source

Three catalogue entries, each with one CSV, licence `{license_id}` (Creative Commons Attribution 4.0
International), update frequency 「随時」 (from time to time):

{entry_rows}

The CSVs are kept as served under `raw/{run}/` (R6 is Shift_JIS, the others UTF-8) with their sha256
in `MANIFEST.json`, with the catalogue's `*_package.json`. Fetched {fetched}. The town updates the
current year's entry as records come in: this repository holds the state of {fetched}.

## Files

| Path | Content |
|---|---|
| `parquet/sighting.parquet` | all {rows:,} records of the three entries |
| `parquet/columns.json` | the counts |
| `raw/{run}/` | the three CSVs and the three `package.json` as served |

## Columns

| Column | Source column | Content |
|---|---|---|
| `fiscal_year` | | 2024, 2025, 2026: the fiscal year of the entry (R6, R7, R8) |
| `source_file`, `row` | | the CSV and the position in it, from 1 |
| `source_id` | `_id` | R8 only |
| `municipality_code` | 全国地方公共団体コード | as written: `14257` in R6 and R7, `014257` in R8 |
| `date`, `time_text` | 出没年月日, 時刻 | date; time as text `H:MM` |
| `prefecture`, `municipality` | 出没場所_都道府県, _市区町村 | |
| `place` | 出没場所 | R7 and R8: the place as a sentence (a landmark or an address) |
| `address_text`, `town`, `lot` | 出没場所_連結表記, _町字, _番地以下 | R6 only |
| `latitude`, `longitude` | 緯度, 経度 | numbers |
| `situation`, `remarks` | 状況, 特記事項 | free text; null when empty |
| `geometry` | | the point as WKB (longitude, latitude), WGS84 assumed |

## What was changed

- The three CSVs have different columns (R6 splits the place into address parts, R7 and R8 give one
  `place`, R8 adds `_id`); they are put in one table with the columns above, null where a file has
  none. The values are as in the source (the Parquet was checked against each CSV with a second CSV
  reader, every row and column). Nothing was removed, merged or corrected.
- The source states no datum; WGS84 is assumed. All points fall near Kamisunagawa (checked).

## Counts

| Fiscal year | Records | From | To |
|---|---|---|---|
{count_rows}

## Known issues

- Very small: {rows:,} records. Each fiscal year is its own entry and is updated during the year; R8 is
  incomplete (the state of {r8_state}).
- The records are the town's reports (sightings, tracks, droppings); one animal can be reported more
  than once, and the counts are not a census.

## Licence

The catalogue states Creative Commons Attribution 4.0 International (`cc-by-40-intl`) for each entry.
This dataset is offered under CC BY 4.0 and the credit is to Kamisunagawa Town:

> 出典：上砂川町「ヒグマ出没マップ」（{pages}）を加工して作成
"""


def main() -> int:
    run = sorted((ROOT / "data" / "raw").glob("*/MANIFEST.json"))[-1].parent
    m = json.loads((run / "MANIFEST.json").read_text())
    cols = json.loads((ROOT / "data/parquet/columns.json").read_text())
    assert cols["run"] == run.name
    d = pq.read_table(ROOT / "data/parquet/sighting.parquet").drop(["geometry"]).to_pydict()
    rows = cols["rows"]
    entry_rows = "\n".join(
        f"- R{e['fiscal_year'] - 2018}: <{e['page']}> 「{e['title']}」, resource 「{e['resource_name']}」, "
        f"entry last modified {e['metadata_modified'][:10]}, file `{e['csv'].split('_', 1)[1]}`"
        for e in m["entries"].values()
    )
    fy = Counter(d["fiscal_year"])
    count_rows = "\n".join(
        f"| R{y - 2018} ({y}) | {fy[y]:,} | {min(x for x, f in zip(d['date'], d['fiscal_year'], strict=True) if f == y)} "
        f"| {max(x for x, f in zip(d['date'], d['fiscal_year'], strict=True) if f == y)} |"
        for y in sorted(fy)
    )
    card = CARD.format(
        repo=REPO, rows=rows, license_id=m["license_id"], run=run.name, fetched=run.name,
        first=min(d["date"]), last=max(d["date"]), entry_rows=entry_rows, count_rows=count_rows,
        r8_state=m["entries"]["r8"]["resource_name"].split("（")[-1].rstrip("）"),
        pages=", ".join(e["page"] for e in m["entries"].values()),
    )  # fmt: skip
    data = ROOT / "data"
    (data / "README.md").write_text(card, encoding="utf-8")
    (data / "LICENSE").write_text(
        "CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/legalcode)\n\n"
        "The records are from 上砂川町 ヒグマ出没マップ (R6 to R8), published in the BODIK open data catalogue\n"
        "under Creative Commons Attribution 4.0 International, processed as described in README.md.\n"
        f"Credit: 出典：上砂川町「ヒグマ出没マップ」（{', '.join(e['page'] for e in m['entries'].values())}）を加工して作成\n",
        encoding="utf-8",
    )
    (data / "provenance.yaml").write_text(
        f"source: 上砂川町 ヒグマ出没マップ R6 to R8 (BODIK)\nlicense: {m['license_id']}\nrun: {run.name}\n"
        f"retrieved: {run.name}\nrows: {rows}\n"
        + "".join(
            f"{k_}_csv_sha256: {m['files'][e['csv']]['sha256']}\n" for k_, e in m["entries"].items()
        ),
        encoding="utf-8",
    )
    print("wrote data/README.md, LICENSE, provenance.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
