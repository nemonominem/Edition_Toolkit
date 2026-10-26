#!/usr/bin/env python3
"""Anchor unzoned email entries to an exact copy that carries an explicit offset.

Rule 5 (exact-copy anchor). If an entry's text matches (similarity >= 0.95, same
or adjacent day) a copy whose stamp carries an explicit offset (+0000, UTC+11:00,
AEDT, ...), the entry's time is the same instant as that copy. This is evidence
from the same message, so it outranks the zone rules. Run after the parsers and
before dedupe_same_instant.py.
"""
import difflib
import json
import os
from datetime import timedelta
from zoneinfo import ZoneInfo

import owner_zone_check as o

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "page_based")
ANALYSIS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analysis")
THRESHOLD = 0.95


def save(name, data, entries):
    if isinstance(data, dict) and "entries" in data:
        data["entries"] = entries
        json.dump(data, open(os.path.join(HERE, name), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    else:
        json.dump(entries, open(os.path.join(HERE, name), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    files = {"po-emails.json": o.load("po-emails.json"), "farrar-fauci.json": o.load("farrar-fauci.json")}
    raw = {n: json.load(open(os.path.join(HERE, n), encoding="utf-8")) for n in files}
    everything = [(e, n) for n, es in files.items() for e in es]
    explicit = []
    for e, _ in everything:
        if e.get("stamp_status") == "offset" or "explicit" in (e.get("zone_assumed") or ""):
            off = o.offset_of(e.get("stamp"))
            p = o.printed(e.get("stamp"))
            if off is not None and p is not None:
                explicit.append((e, p - timedelta(hours=off), o.norm_body(e)))
    changed = []
    for name, entries in files.items():
        for e in entries:
            if e.get("stamp_status") == "offset" or "explicit" in (e.get("zone_assumed") or ""):
                continue
            p = o.printed(e.get("stamp"))
            body = o.norm_body(e)
            if p is None or len(body) < 60:
                continue
            best = None
            for x, xu, xb in explicit:
                if x is e or abs((xu.date() - p.date()).days) > 1:
                    continue
                s = difflib.SequenceMatcher(None, body[:300], xb[:300]).ratio()
                if s >= THRESHOLD and (best is None or s > best[0]):
                    best = (s, xu, x.get("idx"))
            if best is None:
                continue
            s, xu, xidx = best
            # xu is the copy's own instant in UTC (its printed time minus its
            # explicit offset). The entry is the same message, so it is the same instant.
            eastern = xu.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("America/New_York"))
            old = (e["date"], e["time"])
            e["date"], e["time"] = eastern.strftime("%Y-%m-%d"), eastern.strftime("%H%M")
            e["zone_assumed"] = "anchored to an exact copy with an explicit offset (similarity %.2f, copy idx %s)" % (s, xidx)
            # keep the display fields in step with the new time (the app shows them)
            e["raw_date"] = "%s:%s ET · %s" % (e["time"][:2], e["time"][2:], e.get("subject") or "")
            e["stamp_line"] = "%s -> %s:%s ET (same instant as the explicit-offset copy, idx %s)" % (
                (e.get("stamp") or "").strip(), e["time"][:2], e["time"][2:], xidx)
            changed.append((name, e.get("idx"), old, (e["date"], e["time"]), xidx, round(s, 2)))
    for name in files:
        save(name, raw[name], files[name])
    for c in changed:
        print("anchored:", c)
    print("entries anchored:", len(changed))


if __name__ == "__main__":
    main()
