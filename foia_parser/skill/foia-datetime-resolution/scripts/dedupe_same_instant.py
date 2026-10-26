#!/usr/bin/env python3
"""Remove same-instant, same-text copies within each email release.

Two entries are the same message when their body text (first 90 normalised
characters, headers stripped) matches and their date and time are identical.
Keep one: an explicit-offset copy first, then the one with the fuller sender
name. Every removal is written to zone_rule_dedupe.log.

Cross-release copies (the same message in the PO and Farrar-Fauci releases)
are not removed here; they are two sources for one message and are reported.
"""
import json
import os
import re
from collections import defaultdict

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "page_based")
ANALYSIS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analysis")
FILES = ["farrar-fauci.json", "po-emails.json"]


def load(path):
    data = json.load(open(path, encoding="utf-8"))
    return data, (data["entries"] if isinstance(data, dict) and "entries" in data else data)


def body_key(e):
    lines = [l for l in (e.get("content") or "").split("\n")
             if l.strip()
             and not re.match(r"^\s*(>?\s*)(From|To|Cc|Bcc|Subject|Sent|Date|Attachments|Importance)\s*:", l, re.I)
             and not re.match(r"^-{3,}$", l.strip())]
    return re.sub(r"[^a-z0-9]", "", " ".join(lines).lower())[:90]


def has_real_time(e):
    """A partial or unparsed stamp carries a defaulted time (noon), which says
    nothing about identity: two different messages can share it."""
    return bool(e.get("date") and e.get("time")) and e.get("stamp_status") not in ("partial-no-time", "unparsed")


def rank(e):
    explicit = 1 if (e.get("stamp_status") == "offset" or "explicit" in str(e.get("zone_assumed"))) else 0
    return (explicit, len(e.get("sender") or ""))


def repoint_links(entries, replaced):
    """Entries that pointed at a removed entry now point at the one that was kept.
    Without this the thread panel meets a reply link to an entry that does not exist."""
    by_key = {e.get("thread_key"): e for e in entries}
    for e in entries:
        me = e.get("thread_key")
        rt = e.get("reply_to")
        if rt in replaced:
            rt = replaced[rt]
            k = by_key.get(rt)
            if rt == me or k is None:
                e.pop("reply_to", None)
                e.pop("reply_to_label", None)
            else:
                e["reply_to"] = rt
                e["reply_to_label"] = k.get("thread_label", e.get("reply_to_label"))
        seen, rebuilt = set(), []
        for rep in e.get("replied_by") or []:
            key = rep.get("key") if isinstance(rep, dict) else rep
            was_replaced = key in replaced
            key = replaced.get(key, key)
            if key == me or key in seen or key not in by_key:
                continue
            # A message has one parent. If the kept copy has a different parent
            # from the removed copy's, the kept copy's own parent wins.
            if was_replaced and by_key[key].get("reply_to") != me:
                continue
            seen.add(key)
            rebuilt.append({"key": key, "label": by_key[key].get("thread_label", "")})
        if "replied_by" in e:
            e["replied_by"] = rebuilt


def drop_page_map_keys(name, replaced):
    """Remove page-map keys of removed entries, so the map matches the data."""
    pm_name = name.replace(".json", "_page_map.json")
    path = os.path.join(HERE, pm_name)
    if not replaced or not os.path.exists(path):
        return
    pm = json.load(open(path, encoding="utf-8"))
    for k in replaced:
        pm.pop(k, None)
    json.dump(pm, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    log = []
    for name in FILES:
        path = os.path.join(HERE, name)
        raw, entries = load(path)
        groups = defaultdict(list)
        for e in entries:
            if len(body_key(e)) >= 60 and has_real_time(e):
                groups[(body_key(e), e["date"], e["time"])].append(e)
        drop = set()
        replaced = {}          # removed thread_key -> kept thread_key
        # Header-only fragments: an entry with no body text is a broken copy of a
        # full entry when date, time, sender and subject all agree. Its subject
        # must appear in the full entry's subject (e.g. "Phone call" in
        # "Re: Phone call").
        full = [e for e in entries if len(body_key(e)) >= 20 and has_real_time(e)]
        for e in entries:
            if len(body_key(e)) >= 20 or not has_real_time(e) or not e.get("sender"):
                continue
            subj = (e.get("subject") or "").strip().lower()
            for f in full:
                if (f["date"], f["time"], f.get("sender")) == (e["date"], e["time"], e["sender"]) \
                        and subj and subj in (f.get("subject") or "").strip().lower():
                    drop.add(id(e))
                    replaced[e["thread_key"]] = f["thread_key"]
                    log.append((name, e["idx"], e["date"], e["time"], e.get("sender"), f["idx"], f.get("sender")))
                    break
        for v in groups.values():
            if len(v) < 2:
                continue
            keep = max(v, key=rank)
            for e in v:
                if e is not keep:
                    drop.add(id(e))
                    replaced[e["thread_key"]] = keep["thread_key"]
                    log.append((name, e["idx"], e["date"], e["time"], e.get("sender"), keep["idx"], keep.get("sender")))
        kept = [e for e in entries if id(e) not in drop]
        repoint_links(kept, replaced)
        drop_page_map_keys(name, replaced)
        if isinstance(raw, dict) and "entries" in raw:
            raw["entries"] = kept
            json.dump(raw, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        else:
            json.dump(kept, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("%s: removed %d, now %d" % (name, len(drop), len(kept)))
    with open(os.path.join(ANALYSIS, "zone_rule_dedupe.log"), "w", encoding="utf-8") as fh:
        fh.write("Same-instant, same-text copies removed within each release\n")
        fh.write("file | removed idx | date | time | sender | kept idx | kept sender\n")
        for r in log:
            fh.write(" | ".join(str(x) for x in r) + "\n")


if __name__ == "__main__":
    main()
    # Keep the audit file in step with the data (dedupe is the last step of a rebuild)
    import build_zone_audit
    build_zone_audit.main()
