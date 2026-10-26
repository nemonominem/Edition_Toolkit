"""Shared grammar for turning a FOIA'd, OCR'd email-correspondence PDF into
one structured entry per message.

This is the engine extracted from PO_Slack's parse_po_emails.py /
parse_farrar_fauci.py once both had converged on the same rules (written
down in that project's SPEC.md, itself borrowed from the Fauci diary's own
email work):

  * one entry per message -- an author at an instant -- never a whole thread
  * an entry holds only what its author wrote; quoted history is its own entry
  * an explicit UTC offset in the stamp always wins
  * otherwise the sender's own institution decides the zone, and the
    assumption is recorded, never silent
  * everything is normalised to ET for ordering, with the local stamp kept

Everything here is generic across releases; everything that is NOT -- who
the correspondents are, which OCR noise that particular scan leaves behind,
which affiliation implies which time zone -- is supplied by the caller as a
Profile (see profile.py). See also the `foia-email-pdf` skill alongside this
package for the hard-won lessons behind these rules, including: "when a
project has more than one release parsed by near-identical parsers, a bug
found in one is a reason to check the others, not just fix the one in front
of you" -- which is the reason this package exists at all.
"""

import json
import os
import re
from collections import Counter, OrderedDict, defaultdict
from difflib import SequenceMatcher
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .profile import (
    HEADER_FIELDS, RE_FROM, RE_SENTENCE_END, RE_SOFT_START, RE_ADDR_CONT,
    MONTHS,
)

ET = ZoneInfo("America/New_York")


# ── OCR clean-up ─────────────────────────────────────────────────────────────

def load_pages(profile):
    """-> [(page_no, [lines])]"""
    with open(profile.ocr_txt, encoding="utf-8") as f:
        raw = f.read()
    out = []
    for i, page in enumerate(raw.split("\x0c"), start=1):
        lines = [clean_line(l, profile) for l in page.split("\n")]
        lines = [l for l in lines if l and not profile.furniture_re.match(l)]
        if lines:
            out.append((i, lines))
    return out


def page_owner_map(profile):
    """-> {page_no: owner_prefix} for every page carrying profile's bottom-
    corner mailbox/Bates stamp (profile.page_owner_re).

    Read independently of segmentation, straight off the raw per-page text
    (not the furniture-filtered, cleaned lines segment() works from) -- the
    stamp is reliably the page's own last non-blank line, and this needs to
    survive regardless of whether some other cleanup step would otherwise
    touch it. Matched with search(), not match(): some stamp families print
    as the whole line ("GARRY0000098"), others glued onto trailing banner
    text ("MEMBERS AND STAFF ONLY LIP-000472") -- the code is always the
    tail of the line, not necessarily the whole of it.
    """
    if not profile.page_owner_re:
        return {}
    with open(profile.ocr_txt, encoding="utf-8") as f:
        raw = f.read()
    out = {}
    for i, page in enumerate(raw.split("\x0c"), start=1):
        lines = [l for l in page.split("\n") if l.strip()]
        if not lines:
            continue
        m = profile.page_owner_re.search(lines[-1].strip())
        if m:
            out[i] = m.group(1)
    return out


def clean_line(line, profile):
    line = line.replace("\xa0", " ")
    line = re.sub(r"[ \t]+", " ", line).strip()
    if RE_FROM.match(line):
        line = _HEADER_JUNK.sub("", line)
        line = profile.noise_tail_re.sub("", line)
    if profile.extra_clean_line:
        line = profile.extra_clean_line(line)
    return line.strip()


from .profile import DEFAULT_HEADER_JUNK as _HEADER_JUNK


# A field header, possibly OCR-glued to the next one ("Cc: Jeremy FarrarSubject:
# x"). split_fields() folds the OCR's misreadings (FIELD_ALIASES) back onto the
# real Outlook field name; without that a Cc list stays glued to a Subject line
# and "Subject: Fwd: ..." leaks into the message body.
def field_alias_re(profile):
    names = sorted(set(HEADER_FIELDS) | set(profile.field_aliases), key=len, reverse=True)
    return re.compile(r"\b(%s)\s*:" % "|".join(names), re.I)


def split_fields(block, profile):
    """Split a run of lines into header fields.

    The OCR glues fields together, so fields are found by their keywords
    rather than by line breaks. Only From/To/Cc/Bcc may continue onto the
    next line; Subject, Sent and Date are terminal -- that is what stops the
    header block swallowing the body.
    """
    re_field = field_alias_re(profile)
    fields, order = OrderedDict(), []
    current = None
    for line in block:
        parts = re_field.split(" " + line)
        if len(parts) == 1:
            if current in ("From", "To", "Cc", "Bcc"):
                fields[current] += " " + line.strip()
            continue
        if parts[0].strip():
            if current in ("From", "To", "Cc", "Bcc"):
                fields[current] += " " + parts[0].strip()
        for i in range(1, len(parts) - 1, 2):
            name = profile.field_aliases.get(parts[i].strip().lower()) \
                or parts[i].strip().title()
            if name not in HEADER_FIELDS:
                name = name.title()
            value = parts[i + 1].strip() if parts[i + 1].strip() else ""
            if name not in fields:
                order.append(name)
            fields[name] = (fields.get(name, "") + (" " if name in fields else "") + value).strip()
            current = name
    return fields


def is_junk_line(line):
    """True for the OCR scatter a quoted image leaves behind.

    A line that carries no real word -- nothing three letters or longer --
    no URL and no long number is that kind of noise. Real prose, names and
    even a bare "Tony" survive; the image scatter and stray glyph fragments
    do not.
    """
    s = (line or "").strip()
    if not s:
        return True
    return not (re.search(r"[A-Za-z]{3,}", s)
                or re.search(r"https?://|www\.|@", s)
                or re.search(r"\b\d{4,}\b", s))


def strip_glyph_soup(lines):
    return [ln for ln in lines if not is_junk_line(ln)]


# A long digit run inside a URL (a PubMed ID is the verified real case:
# "https://www.ncbi.nlm.nih.gov/pubmed/3 1996437" for what is really
# ".../pubmed/31996437") gets a stray space inserted by the scan, splitting
# it into a short (1-3 digit) tail still attached to the URL and the rest of
# the number stranded after a space. Narrow on purpose -- a URL ending in
# any OTHER kind of fragment is left alone rather than guessed at, since
# joining anything broader risks swallowing the start of the next, unrelated
# sentence into the link.
RE_URL_SPLIT_DIGITS = re.compile(r"(https?://\S*?\d{1,3})\s+(\d{4,}\b)")


def harden_urls(text):
    """Undo the one OCR artifact in a URL verified safe to fix outright.

    The UI linkifies whatever text survives either way (see index.html's
    linkifyUrls()) -- this only repairs a specific, narrow case rather than
    guaranteeing every link in the release is clickable-and-correct.
    """
    return RE_URL_SPLIT_DIGITS.sub(lambda m: m.group(1) + m.group(2), text)


def clean_field_value(name, value, sender, profile):
    """A header value as it should read on the card.

    From is the roster-canonical sender; the other fields get their avatar
    brackets and glyphs stripped. The raw value survives in `sender_raw`, so
    nothing is silently rewritten.
    """
    from .profile import DEFAULT_AVATAR_BRACKET, DEFAULT_AVATAR_GLYPH
    v = (value or "").strip()
    if name == "From":
        return sender
    v = DEFAULT_AVATAR_BRACKET.sub("", v)
    v = DEFAULT_AVATAR_GLYPH.sub("", v)
    v = re.sub(r"([)\]])\s+[A-Za-z]{1,3}\s*$", r"\1", v)
    v = re.sub(r"\s+", " ", v).strip()
    return v


# ── sender names ─────────────────────────────────────────────────────────────

def clean_sender(raw, profile):
    raw = re.sub(r"\s*<[^>]*>\s*$", "", (raw or "").strip())
    raw = re.sub(r"\s*\[[^\]]*\]\s*$", "", raw).strip()
    for rx, name in profile.sender_roster:
        if rx.search(raw):
            return name, raw
    tail = re.sub(r"[^A-Za-z].*$", "", raw).strip()
    return (tail or raw), raw


# ── timestamps ───────────────────────────────────────────────────────────────

def _ampm(h, ap):
    h = int(h)
    ap = (ap or "").lower().replace(".", "")
    if ap.startswith("p") and h != 12:
        h += 12
    if ap.startswith("a") and h == 12:
        h = 0
    return h


def parse_stamp(text, profile):
    """-> (naive datetime, offset-or-None, how) or (None, None, 'unparsed')

    Tried in order: an explicit parenthesised UTC/GMT offset, then a bare
    RFC-2822-style trailing offset (if this profile has stamps shaped that
    way); then each date shape this profile recognises, US-slash first, then
    day-month-year, then the long "Weekday, Month Day, Year" form, then a
    German Von/Gesendet stamp (if configured), then a partial (date with no
    time) stamp as the last resort.
    """
    t = text.strip()
    off = None
    om = profile.stamp_offset_re.search(t) if profile.stamp_offset_re else None
    if om:
        sign = 1 if om.group(1) == "+" else -1
        off = timedelta(hours=sign * int(om.group(2)), minutes=sign * int(om.group(3)))
    elif profile.stamp_bare_offset_re:
        bm = profile.stamp_bare_offset_re.search(t)
        if bm:
            sign = 1 if bm.group(1) == "+" else -1
            off = timedelta(hours=sign * int(bm.group(2)), minutes=sign * int(bm.group(3)))

    if off is None and profile.named_zone_offsets:
        nz = re.search(r"\b(%s)\b" % "|".join(map(re.escape, profile.named_zone_offsets)), t)
        if nz:
            off = timedelta(hours=profile.named_zone_offsets[nz.group(1)])

    m = profile.stamp_us_re.search(t) if profile.stamp_us_re else None
    if m:
        mo, day, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12:
            dt = datetime(yr, mo, day, _ampm(m.group(4), m.group(7)), int(m.group(5)))
            return dt, off, ("offset" if off is not None else "outlook-us")

    m = profile.stamp_dmy_re.search(t) if profile.stamp_dmy_re else None
    if m:
        mo = MONTHS.get(m.group(2)[:3].lower())
        if mo:
            ap = m.group(7) or "12:00am"
            dt = datetime(int(m.group(3)), mo, int(m.group(1)),
                          _ampm(m.group(4), ap), int(m.group(5)))
            return dt, off, ("offset" if off is not None else "day-month-year")

    m = profile.stamp_long_re.search(t) if profile.stamp_long_re else None
    if m:
        mo = MONTHS.get(m.group(1)[:3].lower())
        if mo:
            dt = datetime(int(m.group(3)), mo, int(m.group(2)),
                          _ampm(m.group(4), m.group(7)), int(m.group(5)))
            return dt, off, ("offset" if off is not None else "long")

    if profile.stamp_de_re and profile.months_de:
        m = profile.stamp_de_re.search(t)
        if m:
            mo = profile.months_de.get(m.group(2).lower())
            if mo:
                dt = datetime(int(m.group(3)), mo, int(m.group(1)),
                              int(m.group(4)), int(m.group(5)))
                return dt, off, ("offset" if off is not None else "german")

    m = profile.stamp_partial_re.search(t) if profile.stamp_partial_re else None
    if m:
        mo = MONTHS.get(m.group(1)[:3].lower())
        if mo:
            return datetime(2020, mo, int(m.group(2)), 12, 0), off, "partial-no-time"

    return None, None, "unparsed"


def zone_for(sender, subject, dt, profile):
    """Pick a zone and say why. Explicit offsets are handled by the caller."""
    if dt:
        ov = profile.zone_overrides.get((dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M"),
                                          (subject or "")[:40]))
        if ov:
            return ZoneInfo(ov[0]), ov[1]
    for rx, zone, why in profile.zone_by_affiliation:
        if rx.search(sender or ""):
            return ZoneInfo(zone), why
    return ZoneInfo(profile.default_zone), profile.default_zone_why


def to_et(dt, tzinfo, why):
    """Normalise to ET, keeping the local stamp for display.

    tzinfo is usually a ZoneInfo (an IANA zone, "America/Los_Angeles"), but
    can also be a plain fixed-offset `datetime.timezone` -- reconcile_zones()
    propagates a message's zone onto what it quotes, and the propagating
    message's own zone can itself be a bare UTC offset ("+0000") rather than
    a named zone, which has no `.key` to build the short zone label from.
    """
    local = dt.replace(tzinfo=tzinfo)
    et = local.astimezone(ET)
    if local.utcoffset() == et.utcoffset():
        return et, "%s %s" % (et.strftime("%H:%M"), "ET")
    zone_label = (tzinfo.key.split("/")[-1].replace("_", " ") if hasattr(tzinfo, "key")
                  else local.strftime("%z"))
    return et, "%s %s -> %s ET" % (local.strftime("%H:%M"), zone_label, et.strftime("%H:%M"))


# ── signature blocks ─────────────────────────────────────────────────────────

def is_signature_line(s, profile):
    """True if this line opens (or continues) a title/sign-off block."""
    s = (s or "").strip()
    if not s:
        return False
    return bool(profile.sig_name_re.match(s) or profile.sig_affil_re.match(s))


def is_address_continuation(line):
    s = (line or "").strip()
    if not s or RE_SENTENCE_END.search(s):
        return False
    if len(s) > 160:
        return False
    return bool(RE_ADDR_CONT.search(s))


def is_name_debris(line):
    """A scrap of a wrapped recipient list: names and glyphs, not prose."""
    s = (line or "").strip()
    if not s or RE_SENTENCE_END.search(s) or len(s) > 200:
        return False
    return not re.search(r"[a-z]{5,}", s)


def is_wrapped_recipient(line, nxt, profile):
    """True for a line inside a To:/Cc: list that the scan wrapped.

    Two ways to qualify. The cheap one is is_name_debris(): no sentence
    punctuation and no real word. When a line does carry a real word but is
    neither sentence-terminated nor anything but capitalised names, it still
    counts if the NEXT line continues the same list -- the signal the scan
    itself gives us.
    """
    if is_name_debris(line):
        return True
    s = (line or "").strip()
    if not s or RE_SENTENCE_END.search(s) or len(s) > 120:
        return False
    names = re.findall(r"[A-Z][a-zA-Z.'-]{2,}", s)
    words = re.findall(r"[A-Za-z']{2,}", s)
    if not names:
        return False
    comma_list = s.count(",") >= 2 and len(names) >= 2
    bare_names = s.count(",") == 0 and len(names) >= 3
    if comma_list or bare_names:
        return True
    tokens = re.findall(r"[A-Za-z']{2,}", s)
    all_known = bool(tokens) and all(
        (t.lower() in profile.first_names
         or any(rx.search(t) for rx, _ in profile.sender_roster))
        for t in tokens)
    if not all_known and len(names) * 2 < len(words):
        return False
    return nxt is not None and (is_name_debris(nxt) or field_alias_re(profile).match(nxt.strip()))


def looks_like_body_prose(line):
    """True once we're confident the message's real body text has started.

    The per-line "does this look like a recipient" classifiers are
    inherently fragile over a long redacted mailing list: a single
    OCR-garbled name can fail every one of them and wrongly end the scan
    many lines before the Subject/Attachments/Importance line it is looking
    for. The safer default is to keep scanning until a line positively looks
    like real body prose (a greeting, or a long sentence with several
    ordinary lowercase words), and only give up then.
    """
    s = (line or "").strip()
    if not s:
        return False
    if re.match(r"^(Dear|Hi|Hello|Hey)\b", s, re.I):
        return True
    if len(s) > 40 and RE_SENTENCE_END.search(s):
        if len(re.findall(r"[a-z]{3,}", s)) >= 5:
            return True
    return False


def continues_recipient_run(line, nxt=None):
    """Weaker recipient-continuation test, used only once already inside a
    run (never to open one). Kept for parity with the original per-project
    parsers; not currently wired into segment()/build_entries() there either
    -- carried forward as-is rather than silently dropped or wired in, since
    changing that behaviour was not asked for here.
    """
    s = (line or "").strip()
    if not s or RE_SENTENCE_END.search(s) or len(s) > 200:
        return False
    words = re.findall(r"[a-z]{3,}", s)
    names = re.findall(r"[A-Z][a-zA-Z.'-]{2,}", s)
    if len(words) > 4 and len(names) * 2 < len(words):
        return False
    if s.count(",") >= 2 and len(names) >= 2:
        return True
    if re.search(r"[.!?]\s+[A-Z][a-z]{2,}", s):
        return False
    return True


def unwrap_lines(lines):
    """Rejoin paragraphs that the scan width broke, keeping real returns."""
    out = []
    for line in lines:
        s = line.strip()
        if not s:
            out.append(line)
            continue
        if out and out[-1].strip() and not RE_SENTENCE_END.search(out[-1]):
            prev = out[-1].rstrip()
            cont = (prev.endswith("-")
                    or RE_SOFT_START.match(s)
                    or (s[:1].islower() and prev[-1:].isalpha()))
            if cont and not re.match(r"^(?:[-*•>]|\d+[.)])\s", s):
                out[-1] = (prev[:-1] if prev.endswith("-") else prev) + " " + s
                continue
        out.append(line)
    return out


def is_header_fragment(line, profile):
    """A stray scrap of a header that the two-column scan tore off.

    A quoted message printed beside its parent has its header lines split
    across the column boundary, so a name lands on its own line between
    fields. Such a scrap is short, has no sentence-ending punctuation, and
    does not read as prose.
    """
    s = (line or "").strip()
    if not s or len(s) > 40 or RE_SENTENCE_END.search(s):
        return False
    if not re.match(r"^[A-Z][A-Za-z'.-]*(?:[ /][A-Za-z][A-Za-z'.-]*){0,3}$", s):
        return False
    return bool(profile.header_fragment_name_re.search(s))


def split_signature(body, profile):
    """-> (body_lines, signature_lines): cut the sign-off block off the message.

    Recognised by shape -- a credentialed name line, or an affiliation line
    -- rather than by salutation, so a correspondent who signs off with a
    bare title block (no "Best regards") still has it recognised.

    The cut is only taken once some prose has been read, so a message that
    opens on an affiliation line keeps it -- unless NONE of the body is ever
    real prose (a recovered nested reply can be nothing but a title/
    affiliation block start to finish), in which case there is no prose to
    protect and keeping the first line out would just split one block into
    two instead of leaving it whole.

    The <=60 bound matters: the signature-name regex's title alternative
    matches on the opening word alone, with nothing to say how long the line
    runs after it -- "Dr Fauci is in back to back meetings but hopes to..."
    matches it exactly the same way "Dr Jeremy Farrar" does. A real
    title/name line is short; anything long starting with a title word is
    prose that merely mentions one, not a signature.
    """
    if (body and is_signature_line(body[0].strip(), profile)
            and len(body[0].strip()) <= 60
            and not any(looks_like_body_prose(line) for line in body)):
        return [], body
    out, sig, cut = [], [], None
    for i, line in enumerate(body):
        s = line.strip()
        if cut is None and out and is_signature_line(s, profile):
            cut = i
        if cut is None:
            out.append(line)
        else:
            sig.append(line)
    return out, sig


def strip_quoted(body, profile):
    """Drop the signature block: everything from the sign-off onwards.

    profile.strip_quoted_short_re holds phrases that are only trustworthy as
    a sign-off when the WHOLE line is short (<=20 chars) -- "Thanks," and
    "Many thanks" are real sign-offs on their own, but are also how a great
    deal of genuine prose opens ("Thanks, Jeremy. Great chatting with you
    and Patrick. Will stay in close touch." -- a real reply, verified in the
    farrar-fauci corpus, that strip_quoted_re alone wiped out entirely,
    taking the rest of the body with it since the cut is unconditional once
    triggered). strip_quoted_re itself has no such false positives in either
    corpus checked so far (every "Best regards"/"Best,"/etc. occurrence is a
    genuine sign-off), so it keeps matching regardless of line length.
    """
    out, cut = [], None
    for i, line in enumerate(body):
        s = line.strip()
        if cut is None and profile.strip_quoted_re.match(s):
            cut = i
        elif (cut is None and profile.strip_quoted_short_re
              and len(s) <= 20 and profile.strip_quoted_short_re.match(s)):
            cut = i
        if cut is None:
            out.append(line)
    return out


def strip_embedded_attachment(body, profile):
    """A document attached straight into this release reads as part of the
    covering email's body unless specifically guarded against."""
    for i, line in enumerate(body):
        if profile.word_comment_marker_re.search(line):
            return body[:i] + ["== ATTACHMENT: document with reviewer comments "
                                "(not transcribed) =="]
        if profile.attached_doc_heading_re.match(line.strip()):
            return body[:i] + ["== ATTACHMENT: document (not transcribed) =="]
    return body


# ── segmentation ──────────────────────────────────────────────────────────────

_LITERAL_HEADER_NEXT = re.compile(r"^\s*(?:From|To|Cc|Subject)\s*:", re.I)


def _opens_literal_header(lines, li):
    """True when the Date:/Sent: line at lines[li] starts a whole nested header.

    A quoted message printed inside another message's body is a Date:/Sent:
    line followed at once by To:/From:/Cc:/Subject: lines. The reopen guard in
    segment() (reopen_min_distance) exists so that a scan which ate the From:
    line does not split a message in two; a complete nested header is not that
    case, so it opens a message even when it sits close to the quote marker
    that introduced it (e.g. "Maybe ... / Date: ... / To: ... / Subject: ...").
    """
    for nl in lines[li + 1:li + 4]:
        if _LITERAL_HEADER_NEXT.match(nl):
            return True
    return False


def segment(pages, profile):
    """Split the page stream into messages.

    Three kinds of boundary open a new message: a From: header (or this
    profile's own alias of it, e.g. German "Von:"); a Date:/Sent: line
    reopening a message whose From: the scan ate (guarded by
    reopen_min_distance, a SEPARATE, smaller threshold from
    max_header_lines -- conflating the two silently breaks one or the other,
    see profile.py); and an inline "On <date>, <person> wrote:" marker, which
    recovers the quoted reply it introduces as its own entry rather than
    leaving it glued into the message quoting it.
    """
    re_field = field_alias_re(profile)
    messages = []
    cur = None
    cur_from_at = -1
    pos = 0
    in_body = False
    for pageno, lines in pages:
        body_mode = in_body
        for li, line in enumerate(lines):
            nxt = lines[li + 1] if li + 1 < len(lines) else None
            if profile.msg_open_re.match(line):
                # A literal nested From:/To:/.../Subject: header, printed
                # (not recovered from a marker) inside the PREVIOUS message's
                # body, gets the same explicit quotes_msg link an inline
                # marker does -- but only when that previous message was
                # itself recovered_inline. Scoped that narrowly on purpose:
                # an ordinary top-level message's body can legitimately
                # absorb an unrelated attached document (the Pope/NASEM case
                # that caused a real chronology violation -- see
                # run_release()'s own safety check), so linking EVERY such
                # boundary would resurface that risk for top-level messages,
                # which have no comparable guarantee of actually being
                # nested quoted content. A recovered-inline message, by
                # construction, already IS a fragment of a deeper quote
                # chain -- a literal header inside ONE of those is reliably
                # the next link in that SAME chain, not unrelated content.
                if cur is not None and cur.get("recovered_inline"):
                    quoting_msg = cur
                    cur = {"header_lines": [line], "body": [], "pages": [pageno]}
                    quoting_msg["quotes_msg"] = cur
                else:
                    cur = {"header_lines": [line], "body": [], "pages": [pageno]}
                messages.append(cur)
                cur_from_at = pos
                body_mode = False
                in_body = False
                pos += 1
                continue
            if profile.hdr_date_re.match(line) and cur is not None and body_mode \
                    and (pos - cur_from_at > profile.reopen_min_distance
                         or _opens_literal_header(lines, li)):
                if cur.get("recovered_inline"):
                    quoting_msg = cur
                    cur = {"header_lines": [line], "body": [], "pages": [pageno]}
                    quoting_msg["quotes_msg"] = cur
                else:
                    cur = {"header_lines": [line], "body": [], "pages": [pageno]}
                messages.append(cur)
                cur_from_at = pos
                body_mode = False
                in_body = False
                pos += 1
                continue
            iq = cur is not None and profile.inline_quote_re.match(line)
            if iq:
                date_str, time_str, name = iq.groups()
                quoting_msg = cur    # the message whose body carries this marker
                # A space, not a comma, between date and time: parse_stamp()'s
                # own regexes (built against real Sent:/Date: lines, which
                # never carry a comma there) all fail to match "Feb 5, 2020,
                # 7:20 AM" -- every one falls through to the date-only
                # partial-stamp fallback, silently discarding a time the
                # marker itself gave us cleanly, defaulting to noon instead.
                # Found via a real chronology violation this caused once
                # recovered-inline messages started getting reply_to links
                # (the bogus noon default put several out of true order).
                cur = {"header_lines": ["From: %s" % name.strip(),
                                         "Sent: %s %s" % (date_str.strip(), time_str.strip())],
                       "body": [], "pages": [pageno], "recovered_inline": True}
                # Record which message quotes this one, explicitly -- this is
                # certain (the marker says so), unlike thread_entries()'s own
                # subject-matching, which can't link these at all: a recovered
                # inline message never carries a Subject (none is invented),
                # so it could never land in the same subject-group as the
                # message that quotes it even if its subject DID happen to
                # survive. Resolved into a reply_to/replied_by pair once
                # thread_keys exist (see run_release()).
                quoting_msg["quotes_msg"] = cur
                messages.append(cur)
                cur_from_at = pos
                # Unlike a real From:/Date: boundary, this header is already
                # complete -- built entirely from the one matched line, with
                # no To:/Cc:/Subject: of its own to follow. Going to body
                # mode immediately stops a deeper nested quote's own header
                # lines (it can easily be a forwarded message with a full
                # header) from being absorbed as continuation fields of
                # THIS one.
                body_mode = True
                in_body = True
                pos += 1
                continue
            pos += 1
            if cur is None:
                continue
            cur["pages"].append(pageno)
            if not body_mode:
                if len(cur["header_lines"]) > 1 and is_junk_line(line):
                    continue
                has_field = bool(re_field.search(line))
                if cur["header_lines"] and not has_field and len(cur["header_lines"]) > 1:
                    if (cur.get("in_addr") and len(cur["header_lines"]) <= profile.max_header_lines
                            and (is_address_continuation(line)
                                 or is_wrapped_recipient(line, nxt, profile))):
                        cur["header_lines"].append(line)
                        continue
                    body_mode = True
                    in_body = True
                    cur["body"].append(line)
                elif has_field or len(cur["header_lines"]) == 1:
                    cur["header_lines"].append(line)
                    names = [n.strip().lower() for n in re_field.findall(line)]
                    if names:
                        cur["in_addr"] = names[-1] in profile.recipient_tokens
                else:
                    body_mode = True
                    in_body = True
                    cur["body"].append(line)
            else:
                cur["body"].append(line)
                in_body = True
        in_body = body_mode
    return messages


# ── entries ───────────────────────────────────────────────────────────────────

def build_entries(messages, profile):
    re_field = field_alias_re(profile)
    entries = []
    for msg in messages:
        fields = split_fields(msg["header_lines"], profile)
        sender, sender_raw = clean_sender(fields.get("From") or "", profile)
        sender_how = "inline quote marker (On ... wrote:)" if msg.get("recovered_inline") \
            else ("From: line" if fields.get("From") else "")
        stamp = fields.get("Sent") or fields.get("Date") or ""
        body = strip_embedded_attachment(strip_quoted(msg["body"], profile), profile)
        recovered_inline = bool(msg.get("recovered_inline"))

        # Anything plainly a header field at the very top of the body
        # belongs to the header, not the message text -- skipped entirely
        # for a recovered-inline message, whose header is already complete
        # (built from the one matched marker line alone): a deeper nested
        # quote can start with its OWN full header right at the top of this
        # body, and absorbing that would bolt on a second, unrelated
        # To:/Subject:/Date: that reads as if it belonged to this message.
        while body and not recovered_inline:
            head = body[0].strip()
            if re_field.match(head):
                extra = split_fields(body[:1], profile)
                for k, v in extra.items():
                    if v and not fields.get(k):
                        fields[k] = v
                body = body[1:]
                continue
            if is_junk_line(head) or is_header_fragment(head, profile):
                body = body[1:]
                continue
            break

        window = min(len(body), 8)
        found = -1
        if not recovered_inline:
            for i in range(window):
                if re_field.match(body[i].strip()):
                    found = i
                    break
        if found >= 0:
            j = found + 1
            while j < min(len(body), 150):
                if re_field.match(body[j].strip()):
                    names = [n.strip().lower() for n in re_field.findall(body[j])]
                    if any(n in profile.recipient_tokens for n in names):
                        found = j
                        j += 1
                        continue
                    found = j
                    break
                if looks_like_body_prose(body[j]):
                    break
                j += 1
            else:
                found = j - 1
        if found < 0 and not recovered_inline:
            i = max(0, window - 1)
            while i < min(len(body), 150):
                if re_field.match(body[i].strip()):
                    found = i
                    break
                if looks_like_body_prose(body[i]):
                    break
                i += 1
            if found >= 0:
                j = found + 1
                while j < min(len(body), 150):
                    if re_field.match(body[j].strip()):
                        names = [n.strip().lower() for n in re_field.findall(body[j])]
                        if not any(n in profile.recipient_tokens for n in names):
                            found = j
                            break
                        found = j
                        j += 1
                        continue
                    if looks_like_body_prose(body[j]):
                        break
                    j += 1
        if found < 0 and not fields.get("Subject") and body and not recovered_inline:
            m = profile.subject_fallback_re.match(body[0])
            if m and len(m.group(1).strip()) > 3:
                fields["Subject"] = m.group(1).strip()
                body = body[1:]
                found = 0
        if found >= 0:
            last_field = None
            for j in range(found + 1):
                extra = split_fields(body[j:j + 1], profile)
                if extra:
                    for k, v in extra.items():
                        if v and not fields.get(k):
                            fields[k] = v
                    last_field = next(iter(extra))
                elif last_field == "Subject" and not looks_like_body_prose(body[j]):
                    fields["Subject"] = (fields.get("Subject", "") + " "
                                         + body[j].strip()).strip()
            body = body[found + 1:]

        # "[NA]" rather than leaving this blank: a recovered-inline message
        # never has one (none is invented from the marker alone), and
        # leaving it "" meant such a message could never be linked into any
        # conversation -- not even the one it was quoted FROM -- since
        # thread_entries() groups by subject and an empty subject is never a
        # group. The real link for these is set explicitly below instead
        # (quotes_msg, resolved after this loop), so "[NA]" here is purely
        # the display value, not a signal thread_entries() acts on.
        subject = (fields.get("Subject") or "").strip() or "[NA]"
        body = strip_glyph_soup(body)
        body, signature = split_signature(body, profile)
        if not fields.get("From"):
            for sline in signature:
                hit = next((name for rx, name in profile.sender_roster
                            if rx.search(sline.strip())), None)
                if hit:
                    sender, sender_raw = hit, sline.strip()
                    sender_how = "signature block (From: lost in scan)"
                    break
        body = unwrap_lines(body)
        content_body = harden_urls("\n".join(body).strip())

        dt, off, how = parse_stamp(stamp, profile)
        if dt is None:
            entries.append({
                "date": None, "time": None, "kind": "email",
                "raw_date": subject,
                "sender": sender, "sender_raw": sender_raw, "sender_how": sender_how,
                "subject": subject,
                "content": header_block(fields, content_body, sender, subject, profile, signature),
                "date_note": "no usable timestamp in the release; not plotted",
                "pages": sorted(set(msg["pages"])), "source": profile.source_id,
                "stamp_status": how,
                "recovered_inline": recovered_inline,
            })
            continue

        if off is not None:
            # dt is naive here, read as a LOCAL stamp at a fixed offset from
            # UTC (not a ZoneInfo, since "+0000"/"-05:00" names no IANA zone
            # by itself) -- this tzinfo represents the zone for
            # reconcile_zones() below too, in case something deeper quotes
            # THIS message and needs to inherit the zone it was read in.
            from datetime import timezone as _timezone
            tzinfo = _timezone(off)
            local = dt.replace(tzinfo=tzinfo)
            et = local.astimezone(ET)
            zone_why = "explicit UTC%s%02d:%02d in the stamp" % (
                "+" if off.total_seconds() >= 0 else "-",
                abs(off.total_seconds()) // 3600,
                (abs(off.total_seconds()) % 3600) // 60)
            stamp_line = "%s %s -> %s ET" % (
                stamp.strip(), ("UTC%s%02d:%02d" % (
                    "+" if off.total_seconds() >= 0 else "-",
                    int(abs(off.total_seconds()) // 3600),
                    int(abs(off.total_seconds()) % 3600 // 60))), et.strftime("%H:%M"))
            zone_source = "offset"
            dt_for_tz = dt
        else:
            # A 24-hour stamp only: a day-month-year stamp with am/pm is a US-style
            # client on whatever clock its mailbox uses, so it falls through to
            # the older rules (page owner, affiliation).
            fmt_zone = profile.zone_by_stamp_format.get(how)
            if fmt_zone and how == "day-month-year" and re.search(r"\b[ap]\.?m\.?\b", stamp, re.I):
                fmt_zone = None
            if fmt_zone:
                tzinfo, zone_why = ZoneInfo(fmt_zone[0]), fmt_zone[1]
                zone_source = "stamp-format"
            else:
                tzinfo, zone_why = zone_for(sender, subject, dt, profile)
                zone_source = "affiliation"
            et, stamp_line = to_et(dt, tzinfo, zone_why)
            if how == "partial-no-time":
                stamp_line += " (time not recovered)"
            dt_for_tz = dt

        entries.append({
            "date": et.strftime("%Y-%m-%d"),
            "time": et.strftime("%H%M"),
            "kind": "email",
            "raw_date": "%s ET · %s" % (et.strftime("%H:%M"), subject),
            "sender": sender, "sender_raw": sender_raw,
            "sender_how": sender_how,
            "subject": subject,
            "content": header_block(fields, content_body, sender, subject, profile, signature),
            "signature": "\n".join(signature).strip() if signature else None,
            "stamp": stamp.strip(),
            "stamp_status": how,
            "zone_assumed": zone_why,
            "stamp_line": stamp_line,
            "recovered_inline": recovered_inline,
            "pages": sorted(set(msg["pages"])),
            "source": profile.source_id,
            # Transient -- popped before JSON is written. Lets
            # reconcile_zones() recompute date/time/stamp_line/zone_assumed
            # from scratch if better zone evidence than this (the sender's
            # own affiliation, tried first here) turns out to be available:
            # an explicit quote-chain link to a message whose OWN zone is
            # more confidently known, or this message's page-owner code.
            "_dt_naive": dt_for_tz,
            "_tzinfo": tzinfo,
            "_zone_source": zone_source,
        })

    # Resolve segment()'s "this message quotes that one" links (quotes_msg,
    # set on the QUOTING message, pointing at the recovered-inline message it
    # introduces) into entry references. entries[i] is built from messages[i]
    # 1:1, in order -- nothing above skips appending an entry for a message --
    # so a positional id() map is enough; no stable key exists yet (thread_key
    # isn't assigned until run_release(), after sorting).
    msg_idx_by_id = {id(m): i for i, m in enumerate(messages)}
    for i, msg in enumerate(messages):
        quoted = msg.get("quotes_msg")
        if quoted is None:
            continue
        j = msg_idx_by_id.get(id(quoted))
        if j is not None:
            entries[i]["_explicit_reply_to_entry"] = entries[j]
    return entries


def header_block(fields, body, sender, subject, profile, signature=None):
    """From/To/Cc/Subject/Sent stay inside `content` so they remain
    searchable and highlightable; the UI splits on the rule to style them
    apart. The signature block is appended after its own rule, one line per
    return, so it reads as a signature rather than as more of the message --
    its returns are the sender's own, so they are kept exactly as scanned.

    Subject always shows, "[NA]" when none was recovered (a recovered-inline
    message never has one), rather than silently omitting the line -- so a
    reader sees the field was looked for and genuinely isn't there, not that
    it was never checked."""
    head = []
    for k in ("From", "To", "Cc", "Bcc", "Subject", "Sent", "Date", "Importance", "Attachments"):
        if k == "Subject":
            head.append("Subject: %s" % (clean_field_value(k, fields[k], sender, profile)
                                          if fields.get(k) else subject))
        elif fields.get(k):
            head.append("%s: %s" % (k, clean_field_value(k, fields[k], sender, profile)))
    out = "\n\n".join(head) + "\n\n----------\n\n" + body
    if signature:
        out += "\n\n----------\n\n" + "\n".join(signature).strip()
    return out


# ── page-break repair ────────────────────────────────────────────────────────

RE_WS = re.compile(r"\s+")


def _norm_line(line):
    return RE_WS.sub(" ", line).strip().lower()


def _dedupe_prefix(addition, existing, threshold=0.8):
    """Trim a leading run of `addition`'s own lines that are already present
    in `existing` -- tolerating the kind of OCR noise that makes two
    independent scans of the same real text differ by a handful of
    characters (a misread glyph, a dropped word) -- and return only the
    genuinely new remainder (possibly empty).

    Works line by line rather than as one whole-blob similarity check: the
    release can print the SAME real email twice (once in each of two
    different mailboxes' own exports, each OCR'd independently) with a
    GENUINELY new reply glued on after it in one copy but not the other --
    e.g. a nested "Date:/To:/Subject:" header block that should have opened
    its own message but didn't (a short message can fall under
    REOPEN_MIN_DISTANCE; see profile.py). Treating `addition` as one blob
    and asking "is ALL of this already present" dilutes the match ratio
    with that genuinely-new tail and answers no when the true answer is
    "the first half is a duplicate, the second half is new" -- this instead
    walks forward from the top only as long as each line keeps matching
    something already held, and keeps everything from the first line that
    doesn't.
    """
    existing_lines = [_norm_line(l) for l in existing.split("\n")]
    existing_lines = [l for l in existing_lines if l]
    add_lines = addition.split("\n")
    cut = 0
    for i, line in enumerate(add_lines):
        norm = _norm_line(line)
        if not norm:
            continue
        if any(SequenceMatcher(None, norm, el, autojunk=False).ratio() >= threshold
               for el in existing_lines):
            cut = i + 1
        else:
            break
    return "\n".join(add_lines[cut:]).strip()


def merge_page_splits(entries):
    """Join messages the printer split across a page boundary.

    A long message printed over two pages shows its header again at the top
    of the continuation, so it arrives as two entries with the same sender,
    stamp and subject but different bodies -- and, because the entry key is
    built from the date and minute, colliding keys. The halves are not
    adjacent in the stream (other messages print between them), so they are
    grouped by identity and rejoined in page order.
    """
    groups, order = {}, []
    for e in entries:
        # A stamp that failed to parse carries no "stamp" field at all (see
        # build_entries()'s undated branch) and a fixed stamp_status of
        # "unparsed" -- identical for every such message from the same
        # sender, regardless of which distinct message it actually is. Real
        # case found: a synthesized inline-quote stamp that failed to parse
        # (a since-fixed bug) put 42 of Robert Garry's genuinely separate
        # messages under one (sender, "[NA]", None, "unparsed", "email")
        # identity, silently splicing them into a single garbled entry. A
        # stamp is only trustworthy evidence of "the same physical message,
        # reprinted" once it actually parsed -- give every date-less entry
        # its own identity instead, so this can't recur for some other
        # unparseable stamp shape.
        if not e.get("date"):
            ident = ("_unparsed_", id(e))
        else:
            ident = (e.get("sender"), e.get("subject"), e.get("stamp"),
                     e.get("stamp_status"), e.get("kind"))
        if ident not in groups:
            groups[ident] = []
            order.append(ident)
        groups[ident].append(e)

    redirect = {}   # id(dropped duplicate) -> the head entry it merged into
    out = []
    for ident in order:
        parts = groups[ident]
        head = parts[0]
        for extra in parts[1:]:
            h, sep, body = extra["content"].partition("----------")
            addition = (body if sep else extra["content"]).strip()
            # The release can print some messages twice (e.g. the same real
            # email appearing in two different mailboxes' own exports, each
            # OCR'd independently): same stamp, same body repeated, but NOT
            # necessarily byte-identical -- a real case had "Lj External
            # Sender..." in one copy and "(J External Sender..." in the
            # other, two OCR misreads of the same glyph, which defeated an
            # exact substring check and printed the body twice.
            # _dedupe_prefix() tolerates that noise AND the case where one
            # copy has a genuinely new reply glued on after the duplicate
            # part (see its own docstring) -- appending only whatever is
            # left once the duplicate leading run is trimmed off. Skipped
            # entirely (cheap) when `addition` is already an exact substring.
            if addition and addition not in head["content"]:
                addition = _dedupe_prefix(addition, head["content"])
                if addition:
                    head["content"] = head["content"].rstrip() + "\n" + addition
            head["pages"] = sorted(set(head.get("pages", []) + extra.get("pages", [])))
            head["merged_pages"] = head.get("merged_pages", 0) + 1
            redirect[id(extra)] = head
        out.append(head)

    # An explicit reply link (see build_entries()) can point at an entry that
    # turned out to be a dropped duplicate here -- follow it to the head it
    # actually merged into, so the link still resolves once thread_keys exist.
    for e in out:
        tgt = e.get("_explicit_reply_to_entry")
        if tgt is not None and id(tgt) in redirect:
            e["_explicit_reply_to_entry"] = redirect[id(tgt)]
    return out


# ── dedup: the same real email, printed more than once ─────────────────────
# merge_page_splits() above only merges an EXACT (sender, subject, stamp,
# stamp_status, kind) identity match -- the common case of one message
# printed twice with an identical raw header. It does NOT catch the harder
# case this release also has: the SAME real email appearing more than once
# with a DIFFERENT raw header each time -- once as a literal From:/To:/Cc:/
# Subject: block, again recovered from a bare inline-quote marker (From:/
# Sent: only), or printed once in each of two different mailboxes' own
# exports. Those never share an identity tuple, so they survive as separate
# entries today. See THREADING_PLAN.md §3 for the full design (this covers
# the matching + representative-picking parts of it; the thread panel UI is
# separate, later work).
def _content_body_raw(content):
    """Everything after the content's first '----------' separator (body +
    signature), or the whole string if there's no separator at all -- the
    header is deliberately excluded from comparison, since it legitimately
    differs between two appearances of the same real email (a recovered-
    inline copy carries only From:/Sent:; a literal header carries the full
    To:/Cc:/Subject: as well)."""
    _, sep, rest = content.partition("----------")
    return (rest if sep else content).strip()


# A nested From:/To:/Cc:/Subject:/Sent:/Date: block (English or the German
# Von:/Gesendet:/An:/Betreff: export form) that segmentation failed to open
# as its own message, OR a plain "On <date> ... wrote:" inline marker that
# likewise didn't trigger recovery -- both are documented, known
# segmentation limitations (THREADING_PLAN.md §2b), and either marks the
# point past which a body is no longer reliably this message's OWN words.
RE_NESTED_HEADER_LINE = re.compile(
    r"^(?:From|To|Cc|Bcc|Subject|Sent|Date|Von|Gesendet|An|Betreff)\s*:\s", re.I)
RE_GENERIC_INLINE_QUOTE = re.compile(
    r"^>?\s*On\s+.{3,60}?\s*(?:wrote|writes)?\s*[:;]\s*$", re.I)

# An automated mail-gateway banner, not author-written text -- it appears,
# OCR'd slightly differently each time (a leading glyph read as "Lj", "(J",
# "ia", "[|", ...), on a huge fraction of messages in this release
# regardless of sender or content, and at ~65 characters it can be LONGER
# than a short message's own real text -- enough on its own to push two
# genuinely DIFFERENT short replies over even a strict similarity
# threshold. Stripped from the comparison text only, never from what's
# actually displayed.
RE_EXTERNAL_SENDER_BANNER = re.compile(
    r"external\s+sender\.?\s*be\s+aware\s+of\s+links,?\s*attachments?\s+and\s+requests\.?", re.I)


def _content_body_only(content):
    """Just the body -- excluding BOTH the header and the signature (the
    middle '----------'-delimited segment, or everything after the one
    separator there is if split_signature() found no signature to cut).
    Comparing WITH the signature included is dangerous for similarity
    matching: a correspondent's own identical multi-line signature block
    (Edward Holmes's 5-line academic one, say) can be LONGER than a short
    message's own real text, enough to make two genuinely DIFFERENT
    one-line replies score as near-identical purely because of the shared,
    repeated signature -- a real, confirmed case this exclusion exists to
    rule out (four distinct short Holmes replies, each followed by his own
    identical signature, wrongly clustered into one entry before this fix)."""
    parts = content.split("----------")
    return parts[1].strip() if len(parts) >= 2 else content.strip()


def _content_own_text(content):
    """The prefix of a message's body most likely to actually BE its own
    words -- truncated at the first line that looks like a nested quote
    boundary the parser failed to open as its own entry. Comparing the
    WHOLE body blob instead risks two genuinely DIFFERENT short messages,
    each trailed by an unrecovered quote of much of the SAME underlying
    thread, scoring as near-identical on that shared tail alone -- a real,
    confirmed case this truncation exists specifically to rule out (two
    distinct one-line Robert Garry replies, each followed by overlapping
    quoted history, wrongly clustered through that shared tail before this
    fix)."""
    lines = _content_body_only(content).split("\n")
    cut = len(lines)
    for i, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        if RE_NESTED_HEADER_LINE.match(s) or RE_GENERIC_INLINE_QUOTE.match(s):
            cut = i
            break
    kept = []
    for line in lines[:cut]:
        s = RE_EXTERNAL_SENDER_BANNER.sub("", line).strip()
        if s:
            kept.append(s)
    return "\n".join(kept).strip()


def _content_own_text_norm(content):
    return RE_WS.sub(" ", _content_own_text(content)).strip().lower()


def _body_similarity(content_a, content_b):
    """Fraction of the SHORTER message's own leading text found (in order,
    allowing OCR noise) within the other's -- not a ratio over the combined
    pair, which would understate a short recovered-inline copy matching a
    mere subset of a longer literal-header copy's body (the exact dilution
    bug _dedupe_prefix() above was built to avoid for a related case); and
    not the whole body+signature blob either -- see _content_own_text().

    Requires the SINGLE LONGEST contiguous matching run to itself cover a
    real share of the shorter text, not just the sum of every matching run
    found: a real case had "Sounds correct to me." (21 characters) score
    0.95 against a long, completely unrelated message purely from many tiny
    scattered coincidental character runs ('s', 'nd', ' co', ' to me', ...)
    that happened to sum to 20 of its 21 characters -- the longest any
    single one of those runs reached was 6 characters. A genuine duplicate,
    even noisy OCR, reads as mostly ONE long run broken by a handful of
    garbled characters, not many short, scattered coincidences -- so a
    short string is never trusted on the sum alone.
    """
    a, b = _content_own_text_norm(content_a), _content_own_text_norm(content_b)
    if not a or not b:
        return 0.0
    sm = SequenceMatcher(None, a, b, autojunk=False)
    blocks = [blk for blk in sm.get_matching_blocks() if blk.size > 0]
    if not blocks:
        return 0.0
    shorter = min(len(a), len(b))
    longest = max(blk.size for blk in blocks)
    if longest / shorter < 0.5:
        return 0.0
    matched = sum(blk.size for blk in blocks)
    return matched / shorter


def _field_richness(entry):
    """How much header this copy recovered -- From/To/Cc/Subject/Sent each
    add one ':' to the header block header_block() builds. A copy with more
    fields is a strictly better thing to show as the representative."""
    head, sep, _ = entry["content"].partition("----------")
    return head.count(":")


def _entry_minutes(e):
    """Absolute minutes since an arbitrary epoch, for a dated+timed entry --
    lets two appearances be compared by actual elapsed time rather than by
    calendar-DATE string equality, which would never even compare two
    appearances a few minutes apart if that drift happens to cross a
    midnight boundary (23:58 one day vs 00:02 the next: 4 minutes apart in
    reality, but two different `date` strings, and so two different buckets
    under a date-keyed grouping). -> None if date/time can't be parsed."""
    try:
        d = datetime.strptime(e["date"], "%Y-%m-%d")
    except (ValueError, TypeError, KeyError):
        return None
    t = e.get("time") or "0000"
    try:
        hh, mm = int(t[:2]), int(t[2:4])
    except (ValueError, IndexError):
        hh, mm = 0, 0
    return d.toordinal() * 1440 + hh * 60 + mm


def dedupe_similar_entries(entries, close_minutes=10, max_compare_days=14,
                           same_time_threshold=0.78, cross_time_threshold=0.93,
                           min_body_chars=20):
    """Collapse separate appearances of the SAME real email into one entry.

    Bucketed by SENDER only, not also a calendar date or exact time --
    candidates are compared by actual ELAPSED TIME instead (_entry_minutes()),
    for two reasons, both confirmed directly against this corpus:

    1. The same original message's own embedded quoted timestamp ("On
       <date> at <time> ... wrote:") legitimately reads DIFFERENTLY each
       time it is quoted, because each quoter's own mail client rendered
       that quoted stamp in THEIR OWN zone before ever typing their reply
       (see THREADING_PLAN.md §2's "frozen in the replier's zone"
       principle) -- so the exact same real email surfaces at several
       different literal times through one release, each a legitimate
       per-quoter rendering of the same instant, not a parsing error. One
       real example: a short Jeremy Farrar message recurs across
       farrar-fauci.json at eleven different times across one day, each
       pair scoring 0.6-1.00 similarity.
    2. Separately, the exact clock reading for the SAME real send can
       differ by a few minutes between two copies even with no zone
       confusion at all -- different mail providers/relays stamping a
       message, or simple clock drift -- and that drift can straddle a
       midnight boundary (23:58 one day vs 00:02 the next: 4 minutes apart
       in reality, but two different calendar `date` strings). A
       date-string-keyed bucket, as originally tried, would never even
       compare that pair.

    A match within close_minutes of each other is trusted at a lower bar
    (same_time_threshold) since the near-matching time is itself
    corroborating evidence; anything further apart (but still within
    max_compare_days, the outer bound on how far apart two candidates are
    even considered -- email reprints cluster within a thread's own active
    period, not months apart) needs a stronger body match
    (cross_time_threshold) to compensate for that evidence being weaker or
    absent. Bodies shorter than min_body_chars are skipped entirely for a
    non-close-time match (never for a close-time one, where the time match
    already does the corroborating) -- a short, generic line ("Thanks,"
    "Agreed.") can otherwise cross even a strict ratio threshold by
    coincidence between two genuinely different messages, with no time
    match to rule that out.

    Within a bucket, each candidate is compared only against the fixed
    ANCHOR (first-seen member) of each cluster found so far -- NOT pairwise
    transitive union-find. A-matches-B and B-matches-C does NOT imply A and
    C are grouped unless A itself also matches C directly: a real case had
    exactly this chain (two distinct Garry one-liners each scoring high
    against a shared intermediate, but under 0.4 against EACH OTHER)
    wrongly merge three unrelated messages into one under naive transitive
    clustering. Comparing against a fixed anchor instead of a growing
    aggregate also means a cluster can't "drift" further from what it
    originally matched as more members join. Undated entries are left
    alone entirely: no stable key to compare an unparsed stamp by (see
    merge_page_splits()'s own, identical reasoning).
    """
    buckets = defaultdict(list)
    minutes = {}
    for i, e in enumerate(entries):
        m = _entry_minutes(e)
        if m is None:
            continue
        minutes[i] = m
        buckets[e.get("sender")].append(i)

    cluster_of = {i: i for i in range(len(entries))}   # default: its own, singleton cluster
    max_compare_minutes = max_compare_days * 1440

    for idxs in buckets.values():
        if len(idxs) < 2:
            continue
        idxs = sorted(idxs, key=lambda i: minutes[i])   # chronological, for stable, explicable anchor order
        anchors = []   # indices that anchor a cluster, in first-seen order
        for i in idxs:
            placed = False
            for anchor in anchors:
                diff = abs(minutes[anchor] - minutes[i])
                if diff > max_compare_minutes:
                    continue
                ea, eb = entries[anchor], entries[i]
                close_time = diff <= close_minutes
                threshold = same_time_threshold if close_time else cross_time_threshold
                if not close_time:
                    shorter = min(len(_content_own_text_norm(ea["content"])),
                                  len(_content_own_text_norm(eb["content"])))
                    if shorter < min_body_chars:
                        continue
                if _body_similarity(ea["content"], eb["content"]) >= threshold:
                    cluster_of[i] = anchor
                    placed = True
                    break
            if not placed:
                anchors.append(i)
                cluster_of[i] = i

    groups = defaultdict(list)
    for i in range(len(entries)):
        groups[cluster_of[i]].append(i)

    redirect = {}   # id(dropped duplicate) -> the representative it merged into
    out = []
    for idxs in groups.values():
        if len(idxs) == 1:
            out.append(entries[idxs[0]])
            continue
        # Representative: most header fields recovered, then longest
        # content, then earliest appearance as a final, stable tiebreak.
        idxs_sorted = sorted(idxs, key=lambda i: (
            -_field_richness(entries[i]), -len(entries[i]["content"]), i))
        head = entries[idxs_sorted[0]]
        for i in idxs_sorted[1:]:
            extra = entries[i]
            addition = _dedupe_prefix(_content_body_raw(extra["content"]), head["content"])
            if addition:
                head["content"] = head["content"].rstrip() + "\n" + addition
            head["pages"] = sorted(set(head.get("pages", []) + extra.get("pages", [])))
            head["dedup_merged"] = head.get("dedup_merged", 0) + 1
            redirect[id(extra)] = head
        out.append(head)

    # An explicit reply link (see build_entries()) can point at an entry
    # that turned out to be a dropped duplicate here -- follow it to the
    # representative it actually merged into.
    for e in out:
        tgt = e.get("_explicit_reply_to_entry")
        if tgt is not None and id(tgt) in redirect:
            e["_explicit_reply_to_entry"] = redirect[id(tgt)]
    return out


# ── zone reconciliation ──────────────────────────────────────────────────────
# A quoted message's printed stamp is frozen in the REPLIER's zone at reply
# time, not the original sender's own -- a simple mail client renders the
# "Sent:" time of the message it's replying to in the zone of whoever hits
# reply, and that text is then immutable, carried along unchanged by every
# further reply. zone_for()'s sender-affiliation guess (tried first, in
# build_entries() above) is right for a message's own top-level, authored
# stamp; it is wrong for a quoted copy of an earlier message, which must
# instead inherit the zone of whoever quoted it. See THREADING_PLAN.md (the
# P.O. Slack project) for the full reasoning and the evidence this was built
# against.
def reconcile_zones(entries, owner_by_page, profile):
    """Upgrade a message's zone from the default sender-affiliation guess
    when better evidence is available, preferred in order:

      1. An explicit UTC offset in its own stamp -- unchanged, never
         touched here (already the strongest possible evidence).
      2. The zone of the message that quotes this one (only the explicit
         inline-quote link, i.e. segment()'s quotes_msg -- there is no
         reliable signal yet for the literal nested From:/Date: header
         case, which still relies on sender affiliation; see
         THREADING_PLAN.md §2 for why that one is harder). Resolved by
         propagating from whichever end of a quote chain already has
         independent evidence (an explicit offset, or no quote link at
         all) -- a fixed-point iteration, since a chain can nest several
         quotes deep.
      3. This message's own page-owner code, if profile.page_owners
         recognises it with a zone (not None).

    Leaves zone_source == "affiliation" (the existing guess, untouched)
    wherever none of the above applies.
    """
    for e in entries:
        e.setdefault("_zone_source", "affiliation")

    # Page-owner code: independent of the quote-chain, so applied first.
    # Only upgrades a message still on the plain affiliation guess -- an
    # explicit offset always outranks it.
    for e in entries:
        if e.get("_zone_source") != "affiliation" or "_dt_naive" not in e:
            continue
        pages = e.get("pages") or []
        owners = [owner_by_page[p] for p in pages if p in owner_by_page]
        if not owners:
            continue
        # A message spanning a splice point between two mailboxes' own
        # exports can carry a tied count of each code. `owners` is already
        # in ascending page order (see build_entries()'s "pages": sorted(...)),
        # so breaking a tie by the first (earliest-page) occurrence is
        # deterministic -- max(set(owners), key=owners.count) is NOT: a set's
        # iteration order depends on Python's per-process hash randomisation,
        # so a tied message could silently get a different owner (and zone)
        # from one run to the next. Caught via exactly that: the same release
        # parsed twice in separate processes disagreeing on one entry's zone.
        counts = Counter(owners)
        top = max(counts.values())
        owner = next(o for o in owners if counts[o] == top)
        mapping = profile.page_owners.get(owner)
        if not mapping:
            continue   # recognised code, deliberately left unresolved
        zone_key, why = mapping
        et, stamp_line = to_et(e["_dt_naive"], ZoneInfo(zone_key), why)
        if e.get("stamp_status") == "partial-no-time":
            stamp_line += " (time not recovered)"
        e["date"], e["time"] = et.strftime("%Y-%m-%d"), et.strftime("%H%M")
        e["raw_date"] = "%s ET · %s" % (et.strftime("%H:%M"), e.get("subject") or "")
        e["zone_assumed"], e["stamp_line"] = why, stamp_line
        e["_tzinfo"], e["_zone_source"] = ZoneInfo(zone_key), "owner_code"

    # Quote-chain propagation: repeat until nothing changes. _explicit_reply
    # _to_entry is set on the QUOTING entry, pointing at the entry it
    # quotes -- so once the QUOTING entry's own zone is confidently known,
    # that zone (not the quoted message's own guess) is what the quoted
    # entry should be read in.
    changed = True
    while changed:
        changed = False
        for e in entries:
            tgt = e.get("_explicit_reply_to_entry")
            if tgt is None or "_tzinfo" not in e or "_dt_naive" not in tgt:
                continue
            if e.get("_zone_source") == "affiliation":
                continue   # e's own zone isn't trustworthy evidence yet either
            if tgt.get("_zone_source") != "affiliation":
                continue   # already resolved (by a confident source)
            why = "frozen in %s's zone (quoted in their %s reply)" % (
                e.get("sender") or "the replier's", e.get("date") or "later")
            et, stamp_line = to_et(tgt["_dt_naive"], e["_tzinfo"], why)
            if tgt.get("stamp_status") == "partial-no-time":
                stamp_line += " (time not recovered)"
            tgt["date"], tgt["time"] = et.strftime("%Y-%m-%d"), et.strftime("%H%M")
            tgt["raw_date"] = "%s ET · %s" % (et.strftime("%H:%M"), tgt.get("subject") or "")
            tgt["zone_assumed"], tgt["stamp_line"] = why, stamp_line
            tgt["_tzinfo"], tgt["_zone_source"] = e["_tzinfo"], "inherited"
            changed = True


# ── threading ─────────────────────────────────────────────────────────────────
# A release prints a conversation grouped by thread, not necessarily in time
# order. What that does give us for free is thread membership: messages
# sharing a normalised subject belong to one conversation, so once sorted by
# their own stamps, each links to the one before it. The link is marked
# inferred: there is no message-id to prove it, unlike the explicit inline
# "On <date>, <person> wrote:" markers.
RE_SUBJ_PREFIX = re.compile(r"^\s*(re|fw|fwd?|fwd)\s*[:\-]\s*", re.I)


def norm_subject(subject):
    prev = None
    s = (subject or "").strip()
    while prev != s:
        prev = s
        s = RE_SUBJ_PREFIX.sub("", s).strip()
    return s.lower()


def thread_entries(entries):
    """Link messages that share a conversation, in time order.

    "[NA]" (the placeholder for a Subject that could not be recovered -- see
    build_entries()) is deliberately never a grouping key here: it would
    cluster every subject-less message in the release into one fake
    "conversation" sorted by date, regardless of whether they ever had
    anything to do with each other. Subject-less recovered-inline messages
    still get linked, just explicitly (see run_release(), which resolves
    segment()'s quotes_msg into reply_to/replied_by before this runs) -- a
    link this function must not overwrite with a weaker inferred one.
    """
    groups = defaultdict(list)
    for e in entries:
        if e.get("date") and e.get("subject") != "[NA]":
            groups[norm_subject(e.get("subject"))].append(e)
    linked = 0
    for key, group in groups.items():
        if not key or len(group) < 2:
            continue
        group.sort(key=lambda e: (e["date"], e.get("time") or ""))
        for prev_e, e in zip(group, group[1:]):
            if e.get("link_kind", "").startswith("explicit"):
                continue
            e["reply_to"] = prev_e["thread_key"]
            e["reply_to_label"] = prev_e["thread_label"]
            e["link_kind"] = "inferred (same conversation)"
            prev_e.setdefault("replied_by", []).append(
                {"key": e["thread_key"], "label": e["thread_label"]})
            linked += 1
    return linked


# ── page map ──────────────────────────────────────────────────────────────────

def build_page_map(entries, n_pages):
    """Map each entry to the PDF pages its text came from."""
    pmap = {}
    for i, e in enumerate(entries):
        pages = [p for p in e.get("pages") or [] if 1 <= p <= n_pages]
        if not pages:
            continue
        pmap[entry_key(e, i)] = {"start": pages[0], "end": pages[-1], "breaks": []}
    return pmap


def entry_key(e, i):
    return e.get("thread_key") or "%s|%s" % (e.get("source"), e.get("idx", i))


# ── driver ────────────────────────────────────────────────────────────────────

def run_release(profile, print_stats=True):
    """Parse one release end to end and write out_json/out_map.

    -> the entries list, for a caller that wants to inspect it further
    (build_po_guide.py reads po-emails.json back in, not this directly, but
    tests may want it).
    """
    pages = load_pages(profile)
    messages = segment(pages, profile)
    entries = merge_page_splits(build_entries(messages, profile))

    # Before thread_key is built from date/time below, so a correction here
    # is reflected in the key -- and before the explicit-link pop just below
    # (reconcile_zones() itself walks the same _explicit_reply_to_entry
    # references to propagate a quoting message's zone onto what it quotes).
    reconcile_zones(entries, page_owner_map(profile), profile)

    # After zones are corrected (this buckets on sender + the now-accurate
    # date/time) and before thread_key is assigned (merging here can still
    # use object identity for the explicit-link redirect, the same way
    # merge_page_splits() above does, rather than needing to rewrite
    # already-assigned string keys).
    entries = dedupe_similar_entries(entries)

    seen_keys = {}
    for e in entries:
        e["source"] = profile.source_id
        base = "%s|%s|%s" % (profile.source_id, e.get("date") or "undated",
                             e.get("time") or e["raw_date"][:40])
        n = seen_keys.get(base, 0)
        seen_keys[base] = n + 1
        e["thread_key"] = base if n == 0 else "%s|%d" % (base, n)
        if n:
            e["date_note"] = (e.get("date_note", "") +
                              ("same minute as another message" if n == 1 else "")).strip()
        e["thread_label"] = "%s %s · %s" % (e.get("date") or "undated",
                                            (e.get("time") or "")[:2] + ":" +
                                            (e.get("time") or "")[2:4] if e.get("time") else "",
                                            e.get("sender") or "")
        e["replied_by"] = []

    # Explicit inline-quote links (segment()'s quotes_msg, carried through
    # build_entries()/merge_page_splits() as object references) now have
    # thread_keys to resolve into -- do this before thread_entries(), which
    # must not overwrite an explicit link with a weaker inferred one.
    #
    # Trusted only when it doesn't claim a message was quoted before it was
    # sent, AND both ends have an actual date to check that with. segment()
    # matches an inline marker (or, now, a literal nested header -- see its
    # own docstring) ANYWHERE in a message's body, which is usually right --
    # but a message's body can also absorb an unrelated attached document
    # wholesale (two confirmed real cases, both from Robert Pope broadcast
    # emails whose body ran on into a glued-in NASEM comment compilation,
    # itself quoting an unrelated "On Tue, Feb 4 ... Peter Daszak wrote:"
    # from a different conversation entirely) -- segment() has no way to
    # know the marker it just matched belongs to a different conversation
    # than the message it's physically sitting inside, but a reply dated
    # BEFORE what it supposedly quotes is proof it does. An UNDATED side is
    # just as untrustworthy here, not a free pass: one of the two confirmed
    # cases had exactly that shape (a garbled, unparseable stamp on the
    # Pope message), and skating past the date-vs-date check because one
    # side simply had no date to compare would have asserted the same wrong
    # link anyway. Silently dropping the claim in either case (not
    # asserting a wrong link) is safer than inventing a fix for the
    # underlying over-absorption.
    for e in entries:
        tgt = e.pop("_explicit_reply_to_entry", None)
        if tgt is None or tgt is e:
            continue
        if not e.get("date") or not tgt.get("date"):
            continue
        if (tgt["date"], tgt.get("time") or "") > (e["date"], e.get("time") or ""):
            continue
        e["reply_to"] = tgt["thread_key"]
        e["reply_to_label"] = tgt["thread_label"]
        e["link_kind"] = "explicit (quoted inline)"
        tgt["replied_by"].append({"key": e["thread_key"], "label": e["thread_label"]})

    entries.sort(key=lambda e: (e.get("date") or "9999", e.get("time") or "9999"))
    for i, e in enumerate(entries):
        e["idx"] = i
    linked = thread_entries(entries)

    n_pages = len(open(profile.ocr_txt, encoding="utf-8").read().split("\x0c"))
    page_map = build_page_map(entries, n_pages)
    for e in entries:
        e.pop("pages", None)
        e.pop("_dt_naive", None)
        e.pop("_tzinfo", None)
        e.pop("_zone_source", None)

    dated = [e for e in entries if e.get("date")]
    undated = [e for e in entries if not e.get("date")]
    senders = defaultdict(int)
    for e in dated:
        senders[e["sender"]] += 1

    out = OrderedDict([
        ("source_file", profile.source_file),
        ("source_id", profile.source_id),
        ("title", profile.title),
        ("total_entries", len(entries)),
        ("date_range", {"start": min(e["date"] for e in dated) if dated else None,
                        "end": max(e["date"] for e in dated) if dated else None}),
        ("entries", entries),
    ])
    with open(profile.out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    with open(profile.out_map, "w", encoding="utf-8") as f:
        json.dump(page_map, f, indent=1)

    if print_stats:
        print("Messages segmented: %d" % len(messages))
        print("Thread links (same conversation): %d" % linked)
        print("Entries: %d (%d dated, %d undated)"
              % (len(entries), len(dated), len(undated)))
        if dated:
            print("Range: %s .. %s" % (out["date_range"]["start"], out["date_range"]["end"]))
        print("Senders:")
        for s, c in sorted(senders.items(), key=lambda kv: -kv[1]):
            print("  %4d  %s" % (c, s))
        st = defaultdict(int)
        for e in dated:
            st[e["stamp_status"]] += 1
        print("Stamp parsing: %s" % dict(st))
        print("Page map: %d keys over %d PDF pages" % (len(page_map), n_pages))
        print("Wrote %s and %s" % (profile.out_json, profile.out_map))

    return entries
