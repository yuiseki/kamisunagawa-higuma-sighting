"""Check the Parquet against the three CSVs as served, with pyarrow's CSV reader (all columns as strings).

Every row of every file: each text column equals the CSV's (empty is null), the date, the coordinates
and the point equal the CSV's, `row` and `fiscal_year` are right. Also: the row totals equal the
CSVs', the sha256 of each CSV equals the manifest's, and the rows are the CSVs in order.

    uv run python scripts/03_verify.py
"""

import datetime as dt
import hashlib
import importlib
import json
import sys
from pathlib import Path

import kami as k
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
from shapely import from_wkb

ROOT = Path(__file__).parents[1]


def main() -> int:
    exp = importlib.import_module("02_export_parquet")
    run = sorted((ROOT / "data" / "raw").glob("*/MANIFEST.json"))[-1].parent
    manifest = json.loads((run / "MANIFEST.json").read_text())
    d = pq.read_table(ROOT / "data" / "parquet" / "sighting.parquet").to_pydict()
    pos = 0
    for key, (_, fy, enc, header) in k.SOURCES.items():
        e = manifest["entries"][key]
        path = run / e["csv"]
        assert (
            hashlib.sha256(path.read_bytes()).hexdigest() == manifest["files"][e["csv"]]["sha256"]
        )
        src = pacsv.read_csv(
            path,
            read_options=pacsv.ReadOptions(encoding=enc if enc != "utf-8" else "utf8"),
            parse_options=pacsv.ParseOptions(newlines_in_values=True),
            convert_options=pacsv.ConvertOptions(
                column_types={c: "string" for c in header}, strings_can_be_null=False
            ),
        ).to_pydict()
        n = len(src[header[0]])
        for i in range(n):
            j = pos + i
            assert (
                d["fiscal_year"][j] == fy
                and d["source_file"][j] == e["csv"]
                and d["row"][j] == i + 1
            ), j
            for c, col in exp.NAMES.items():
                want = (src[c][i] or None) if c in src else None
                assert d[col][j] == want, (key, i, c)
            assert d["date"][j] == dt.datetime.strptime(src["出没年月日"][i], "%Y/%m/%d").date(), j
            assert d["latitude"][j] == float(src["緯度"][i]) and d["longitude"][j] == float(
                src["経度"][i]
            ), j
            g = from_wkb(d["geometry"][j])
            assert (g.x, g.y) == (d["longitude"][j], d["latitude"][j]), j
        pos += n
        print(f"{key}: {n} rows equal the CSV")
    assert pos == len(d["row"]), (pos, len(d["row"]))
    print(f"OK: {pos} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
