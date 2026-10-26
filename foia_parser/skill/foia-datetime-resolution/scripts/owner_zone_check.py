#!/usr/bin/env python3
"""Find the zone of REV and GARRY pages from messages that have an explicit-offset copy.

For a PO entry on a REV or GARRY page (its zone is assumed), look for a copy
elsewhere whose stamp carries an explicit offset, with the same date (+-1 day)
and near-identical text (difflib ratio >= 0.6 on normalised body text). Then
   implied offset = printed PO time - explicit-offset instant (as UTC)
and the zone is the offset that matches. Writes owner_zone_check.csv.
"""
import csv
import difflib
import json
import os
import re
from datetime import datetime, timedelta

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "page_based")
ANALYSIS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analysis")
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun",
                                      "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def load(name):
    d = json.load(open(os.path.join(HERE, name), encoding="utf-8"))
    return d["entries"] if isinstance(d, dict) and "entries" in d else d


def norm_body(e):
    lines = [l for l in (e.get("content") or "").split("\n")
             if l.strip() and not re.match(r"^\s*(>?\s*)(From|To|Cc|Bcc|Subject|Sent|Date|Attachments|Importance)\s*:", l, re.I)
             and not re.match(r"^-{3,}$", l.strip())]
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", " ".join(lines).lower())).strip()[:300]


def printed(stamp):
    """(datetime, has_offset_hours) for a stamp with a printed time, else None."""
    s = stamp or ""
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})\D+?(\d{1,2}):(\d{2})\s*([ap]\.?m\.?)?", s, re.I)
    if m:
        d, mo, y, h, mi, ap = m.groups()
        mon = MONTHS.get(mo[:3].lower())
    else:
        m = re.search(r"([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})\D+?(\d{1,2}):(\d{2})\s*([ap]\.?m\.?)?", s, re.I)
        if not m:
            return None
        mo, d, y, h, mi, ap = m.groups()
        mon = MONTHS.get(mo[:3].lower())
    if not mon:
        return None
    h, mi = int(h), int(mi)
    if ap and ap.lower().startswith("p") and h < 12:
        h += 12
    if ap and ap.lower().startswith("a") and h == 12:
        h = 0
    return datetime(int(y), mon, int(d), h, mi)


def offset_of(stamp):
    m = re.search(r"(?:UTC|GMT)?\s*([+-])(\d{2}):?(\d{2})\b", stamp or "")
    if not m or not (re.search(r"UTC|GMT|\+0000|[+-]\d{4}", stamp or "")):
        return None
    sign = 1 if m.group(1) == "+" else -1
    return sign * (int(m.group(2)) + int(m.group(3)) / 60)


def main():
    po = load("po-emails.json")
    ff = load("farrar-fauci.json")
    owners = {}
    for e in po:
        z = e.get("zone_assumed") or ""
        if "REV mailbox" in z:
            owners[id(e)] = "REV"
        elif "Robert Garry's own" in z:
            owners[id(e)] = "GARRY"
    explicit = []
    for e in po + ff:
        if e.get("stamp_status") == "offset" or "explicit" in (e.get("zone_assumed") or ""):
            off = offset_of(e.get("stamp"))
            p = printed(e.get("stamp"))
            if off is not None and p is not None:
                explicit.append((e, p - timedelta(hours=off), norm_body(e)))
    rows = []
    for e in po:
        if id(e) not in owners:
            continue
        p = printed(e.get("stamp"))
        body = norm_body(e)
        if p is None or len(body) < 60:
            rows.append([owners[id(e)], e.get("idx"), e.get("date"), e.get("sender"), e.get("stamp"),
                         "", "", "", "no printed time or text"])
            continue
        best = None
        for x, x_utc, xb in explicit:
            if x is e or abs((x_utc.date() - p.date()).days) > 1:
                continue
            r = difflib.SequenceMatcher(None, body[:300], xb[:300]).ratio()
            if r >= 0.6 and (best is None or r > best[0]):
                best = (r, x, x_utc)
        if best is None:
            rows.append([owners[id(e)], e.get("idx"), e.get("date"), e.get("sender"), e.get("stamp"),
                         "", "", "", "no explicit-offset copy found"])
            continue
        r, x, x_utc = best
        implied = round((p - x_utc).total_seconds() / 3600, 2)
        rows.append([owners[id(e)], e.get("idx"), e.get("date"), e.get("sender"), e.get("stamp"),
                     x.get("stamp"), "%.2f" % r, implied,
                     "copy in %s (idx %s)" % (x.get("source", "farrar-fauci" if x in ff else "po-emails"), x.get("idx"))])
    out = os.path.join(ANALYSIS, "owner_zone_check.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["owner", "po_idx", "date", "sender", "po_stamp", "copy_stamp", "similarity",
                    "implied_offset_hours", "note"])
        w.writerows(rows)
    found = [r for r in rows if r[7] != ""]
    print("owner pages checked:", len(rows), "| with an explicit copy:", len(found))
    for r in found:
        print(" ", r[0], r[1], r[2], r[3], "| printed:", r[4], "| copy:", r[5], "| sim", r[6], "| implied UTC%+.2f" % float(r[7]))


if __name__ == "__main__":
    main()
