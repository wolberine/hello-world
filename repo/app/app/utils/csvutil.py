from __future__ import annotations

import csv
from io import StringIO
from typing import Iterable, Mapping


def rows_to_csv_bytes(rows: Iterable[Mapping[str, object]]) -> bytes:
    rows = list(rows)
    if not rows:
        return b""
    fieldnames = list(rows[0].keys())
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")
