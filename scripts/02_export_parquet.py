"""Write GeoParquet of the ヒグマ出没マップ of Kamisunagawa Town (R6, R7, R8 in one table).

One row per record. fiscal_year (2024, 2025, 2026: the fiscal year of the catalogue entry, R6 to R8),
source_file, row (position in that CSV), source_id (the `_id` of R8), municipality_code (as the source
writes it: `14257`, `014257`), date, time_text, prefecture, municipality, place (R7 and R8: 出没場所),
address_text, town, lot (R6 only: 出没場所_連結表記, _町字, _番地以下), latitude, longitude, situation
(状況), remarks (特記事項), geometry (WKB Point, WGS84 assumed). Empty fields are null.

    uv run python scripts/02_export_parquet.py [--version 2026-10-26]
"""

import argparse
import json
import sys
from pathlib import Path

import kami as k
import pyarrow as pa
import pyarrow.parquet as pq
from shapely.geometry import Point

ROOT = Path(__file__).parents[1]
NAMES = {  # CSV column -> Parquet column
    "_id": "source_id", "全国地方公共団体コード": "municipality_code", "時刻": "time_text",
    "出没場所_都道府県": "prefecture", "出没場所_市区町村": "municipality", "出没場所": "place",
    "出没場所_連結表記": "address_text", "出没場所_町字": "town", "出没場所_番地以下": "lot",
    "状況": "situation", "特記事項": "remarks",
}  # fmt: skip
SCHEMA = pa.schema(
    [
        ("fiscal_year", pa.int16()), ("source_file", pa.string()), ("row", pa.int32()),
        ("source_id", pa.string()), ("municipality_code", pa.string()), ("date", pa.date32()),
        ("time_text", pa.string()), ("prefecture", pa.string()), ("municipality", pa.string()),
        ("place", pa.string()), ("address_text", pa.string()), ("town", pa.string()),
        ("lot", pa.string()), ("latitude", pa.float64()), ("longitude", pa.float64()),
        ("situation", pa.string()), ("remarks", pa.string()), ("geometry", pa.binary()),
    ]
)  # fmt: skip


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=None)
    args = ap.parse_args()
    runs = sorted((ROOT / "data" / "raw").glob("*/MANIFEST.json"))
    raw = runs[-1].parent if args.version is None else ROOT / "data" / "raw" / args.version
    manifest = json.loads((raw / "MANIFEST.json").read_text())
    rows, counts = [], {}
    for key, (_, fy, enc, header) in k.SOURCES.items():
        e = manifest["entries"][key]
        src = k.parse_csv((raw / e["csv"]).read_bytes(), enc, header)
        counts[key] = len(src)
        for i, r in enumerate(src, 1):
            row = {"fiscal_year": fy, "source_file": e["csv"], "row": i}
            for c, col in NAMES.items():
                row[col] = (r[c] or None) if c in r else None
            row.update(date=r["_date"], latitude=r["_lat"], longitude=r["_lon"],
                       geometry=Point(r["_lon"], r["_lat"]).wkb)  # fmt: skip
            rows.append(row)
    geo = {"version": "1.1.0", "primary_column": "geometry",
           "columns": {"geometry": {"encoding": "WKB", "geometry_types": ["Point"]}}}  # fmt: skip
    t = pa.Table.from_pylist(rows, schema=SCHEMA).replace_schema_metadata(
        {b"geo": json.dumps(geo).encode()}
    )
    out = ROOT / "data" / "parquet"
    out.mkdir(parents=True, exist_ok=True)
    pq.write_table(t, out / "sighting.parquet", compression="zstd")
    (out / "columns.json").write_text(
        json.dumps({"run": raw.name, "rows": len(rows), "counts": counts}, indent=2) + "\n"
    )
    print(len(rows), counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
