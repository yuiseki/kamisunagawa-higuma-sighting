import datetime as dt

import kami as k
import pytest

H = k.SOURCES["r7"][3]
ROW = "14257,2025/5/6,15:30,北海道,空知郡上砂川町,奥沢パークゴルフ場付近,43.4669533,142.0115521,子羆を目撃,"


def csv_of(*lines, head=H):
    return ("﻿" + ",".join(head) + "\n" + "\n".join(lines) + "\n").encode()


def test_parse_ok():
    r = k.parse_csv(csv_of(ROW), "utf-8", H)[0]
    assert r["_date"] == dt.date(2025, 5, 6) and r["_lat"] == 43.4669533 and r["特記事項"] == ""


def test_cp932_and_bom():
    r = k.parse_csv(csv_of(ROW).decode("utf-8-sig").encode("cp932"), "cp932", H)
    assert r[0]["状況"] == "子羆を目撃"


@pytest.mark.parametrize(
    "bad",
    [
        ROW.replace("2025/5/6", "2025-05-06"),
        ROW.replace("15:30", "3pm"),
        ROW.replace("43.4669533,142.0115521", "142.0115521,43.4669533"),
    ],
)
def test_refuses(bad):
    with pytest.raises(ValueError):
        k.parse_csv(csv_of(bad), "utf-8", H)


def test_refuses_changed_header():
    with pytest.raises(ValueError):
        k.parse_csv(csv_of(ROW), "utf-8", H + ["x"])


def test_three_fiscal_years():
    assert [v[1] for v in k.SOURCES.values()] == [2024, 2025, 2026]
