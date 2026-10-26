"""Shared helpers: the ヒグマ出没マップ of Kamisunagawa Town (BODIK open data catalogue) and how to read the CSVs."""

import csv
import datetime as dt
import io

CKAN = "https://data.bodik.jp"
LICENSE_ID = "cc-by-40-intl"
# one catalogue entry per fiscal year: key -> (package id, fiscal year, CSV encoding, header)
SOURCES = {
    "r6": (
        "014257_r6bear_map", 2024, "cp932",
        ["全国地方公共団体コード", "出没年月日", "時刻", "出没場所_連結表記", "出没場所_都道府県",
         "出没場所_市区町村", "出没場所_町字", "出没場所_番地以下", "緯度", "経度", "状況", "特記事項"],
    ),
    "r7": (
        "014257_r7bear_map", 2025, "utf-8",
        ["全国地方公共団体コード", "出没年月日", "時刻", "出没場所_都道府県", "出没場所_市区町村",
         "出没場所", "緯度", "経度", "状況", "特記事項"],
    ),
    "r8": (
        "014257_r8bear_map", 2026, "utf-8",
        ["_id", "全国地方公共団体コード", "出没年月日", "時刻", "出没場所_都道府県", "出没場所_市区町村",
         "出没場所", "緯度", "経度", "状況", "特記事項"],
    ),
}  # fmt: skip
BBOX = (141.7, 43.3, 142.3, 43.7)  # lon min, lat min, lon max, lat max: around Kamisunagawa


def api_package(pid: str) -> str:
    return f"{CKAN}/api/3/action/package_show?id={pid}"


def page(pid: str) -> str:
    return f"{CKAN}/dataset/{pid}"


def parse_csv(data: bytes, encoding: str, header: list[str]) -> list[dict]:
    """The rows as dicts of the source's columns (strings), with `_date`, `_lat`, `_lon` added."""
    text = data.decode(encoding)
    if text.startswith("﻿"):
        text = text[1:]
    rows = list(csv.DictReader(io.StringIO(text, newline="")))
    if not rows or list(rows[0]) != header:
        raise ValueError(f"unexpected header {list(rows[0]) if rows else None}")
    for i, r in enumerate(rows):
        if None in r or None in r.values():
            raise ValueError(f"row {i}: ragged")
        r["_date"] = dt.datetime.strptime(r["出没年月日"], "%Y/%m/%d").date()
        r["_lat"], r["_lon"] = float(r["緯度"]), float(r["経度"])
        if not (BBOX[0] <= r["_lon"] <= BBOX[2] and BBOX[1] <= r["_lat"] <= BBOX[3]):
            raise ValueError(f"row {i}: point outside Kamisunagawa ({r['_lat']}, {r['_lon']})")
        dt.datetime.strptime(r["時刻"], "%H:%M")
    return rows
