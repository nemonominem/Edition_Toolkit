#!/usr/bin/env python3
"""Reply-order test for zone groups.

A reply cannot be sent before the message it answers. For each linked reply pair
(replied_by / reply_to), shift every entry of one zone group by d hours and count
the pairs that then run backwards. The shifts with zero violations are the ones
the data allows. A group whose only allowed shift is 0 is settled by this test;
a group with several allowed shifts is not.
Writes reply_order_check.csv.
"""
import csv
import os
from datetime import datetime, timedelta

import owner_zone_check as o

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "page_based")
ANALYSIS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analysis")


def group_of(e, rel):
    z = e.get("zone_assumed") or ""
    if "explicit" in z or z.startswith("anchored") or z.startswith("verified"):
        return "explicit"
    if "REV mailbox" in z:
        return "PO page REV"
    if "Robert Garry's own" in z:
        return "PO page GARRY"
    if "W. Ian Lipkin's own" in z:
        return "PO page LIP"
    if z.startswith("frozen"):
        return "quoted copy"
    if not z:
        return "no zone"
    return z[:40]


def instant(e):
    if not e.get("date") or not e.get("time"):
        return None
    return datetime.fromisoformat(e["date"] + " " + e["time"][:2] + ":" + e["time"][2:])


def main():
    po = o.load("po-emails.json")
    ff = o.load("farrar-fauci.json")
    everything = [(e, "po-emails") for e in po] + [(e, "farrar-fauci") for e in ff]
    by_key = {e.get("thread_key"): e for e, _ in everything}
    pairs = []
    for e, rel in everything:
        for rep in e.get("replied_by") or []:
            k = rep.get("key") if isinstance(rep, dict) else None
            f = by_key.get(k)
            if f is not None and instant(e) and instant(f):
                pairs.append((e, f))
    groups = sorted({group_of(x, "") for pr in pairs for x in pr})
    rows = []
    for g in groups:
        allowed = []
        for d in range(-8, 9):
            bad = 0
            for e, f in pairs:
                te, tf = instant(e), instant(f)
                if group_of(e, "") == g:
                    te = te + timedelta(hours=d)
                if group_of(f, "") == g:
                    tf = tf + timedelta(hours=d)
                if tf < te:
                    bad += 1
            if bad == 0:
                allowed.append(d)
        touched = sum(1 for e, f in pairs if group_of(e, "") == g or group_of(f, "") == g)
        status = "only current zone allowed" if allowed == [0] else (
            "not decided" if len(allowed) > 1 else "no zone allowed (check)")
        rows.append([g, touched, " ".join("%+d" % d for d in allowed), status])
    with open(os.path.join(ANALYSIS, "reply_order_check.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["zone_group", "reply_pairs_touched", "allowed_shifts_hours", "status"])
        w.writerows(rows)
    for r in rows:
        print("%-42s pairs %3s  allowed %-28s %s" % (r[0], r[1], r[2] or "-", r[3]))


if __name__ == "__main__":
    main()
