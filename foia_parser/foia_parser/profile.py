"""The per-release configuration a FOIA email-correspondence parser supplies.

core.py holds the shared grammar (segmentation, header splitting, signature
cutting, stamp parsing, OCR clean-up); everything that varies release to
release -- who the correspondents are, which affiliation implies which time
zone, which OCR glyph patterns that scan's own junk leaves behind, which
language the headers can appear in -- lives here instead, supplied by the
caller as one Profile per release.

Keeping these as data on a Profile rather than baking them into core.py is
the point of extracting this library at all: a bug fixed in the shared
grammar (see RE_INLINE_QUOTE's history -- defined for years, never wired in)
now reaches every release that imports it, rather than needing to be ported
by hand into each project's own copy-pasted parser.
"""

from dataclasses import dataclass, field
import re


# ── grammar shared by every release ─────────────────────────────────────────
# Not part of Profile: these are the same for every release seen so far. A
# release that genuinely needs a different one can still override by passing
# its own compiled regex in the corresponding Profile field (msg_open_re,
# hdr_date_re, inline_quote_re all default to these).
HEADER_FIELDS = ("From", "To", "Cc", "Bcc", "Subject", "Sent", "Date",
                  "Importance", "Attachments")

RE_FROM = re.compile(r"^From:\s*(.+)$", re.I)

DEFAULT_MSG_OPEN_RE = re.compile(r"^(?:From|rom):\s*(.+)$", re.I)
DEFAULT_HDR_DATE_RE = re.compile(r"^(?:Sent|Date)\s*:\s*(.+)$", re.I)

# "On 8 Feb 2020, at 22:15, Kristian G. Andersen wrote:" and its variants.
# The trailing "wrote"/"writes" is OPTIONAL: the scan routinely misreads the
# one word right before the colon ("...Andersen 0%:" for what is "...Andersen
# wrote:") -- by the time "On <date> ... <time> ..." has already matched, the
# line is proven to be this kind of marker regardless of whether that word
# survived the scan. See SKILL foia-email-pdf for the full history of this
# marker, which was defined but never wired into po-emails' own segment() for
# a long time before being fixed.
#
# The optional leading ">" handles a marker printed as part of an already-
# quoted blockquote block ("> On Jan 30, 2020, at 7:13 AM, Jeremy Farrar ...
# wrote:") -- without it the line simply doesn't start with "On" and the
# quoted reply is silently glued into the body of whoever quoted it, with no
# reply_to/replied_by link recoverable afterwards either. Confirmed in
# Fauci_Diary's reparse_ebola.py, which already guards for this
# (`^>?\s*On\s+...`) on its own, narrower inline-quote regex.
#
# The trailing [:;] (not just ":") tolerates the scan misreading the colon
# as a semicolon ("On 17 Feb 2020, at 7:57 am, Garry, Robert F FP wrote;") --
# a real case that otherwise failed to match, leaving that reply glued into
# the PREVIOUS message's signature block with no boundary between them (once
# split_signature() has cut to signature mode, everything to the end of the
# body is signature, with no further break point of its own).
DEFAULT_INLINE_QUOTE_RE = re.compile(
    r"^>?\s*On\s+(?:[A-Za-z]{3,9},?\s+)?"
    r"((?:[A-Za-z]{3,9}\.?\s+\d{1,2}|\d{1,2}\s+[A-Za-z]{3,9}\.?)\s*,?\s*\d{4})"
    r",?\s*(?:at\s+)?(\d{1,2}:\d{2}(?:\s*[AaPp]\.?[Mm]\.?)?)\s*,?\s+"
    r"(.{2,45}?)\s*(?:wrote|writes)?\s*[:;]\s*$", re.I)

DEFAULT_HEADER_JUNK = re.compile(r"^[^A-Za-z0-9]+|[^A-Za-z0-9)\]]+$")
DEFAULT_AVATAR_BRACKET = re.compile(r"[\[(][^)\]]{0,2}[)\]]")
DEFAULT_AVATAR_GLYPH = re.compile(r"[€¢§¶©®™]")

DEFAULT_SIG_NAME_RE = re.compile(
    r"^(?:PROFESSOR|Professor|DR|Dr|MR|Mr|MS|Ms|SIR|Sir|DAME|Dame)\b"
    r"|^(?:[A-Z][A-Z.'-]+\s+){1,4}[A-Z][A-Z.'-]*"
    r"\s+(?:FAA|FRS|FBA|FRCS|FACP|PhD|Ph\.D|MD|M\.D|MP|MSc|BSc|MBBS)\b")

RE_SENTENCE_END = re.compile(r"[.!?:;…]['\")\]]?\s*$")
RE_SOFT_START = re.compile(r"^\s*[,;:.)\]]")
RE_ADDR_CONT = re.compile(r"[,;|/\\]|(?:^|[\s(])[\"']?[A-Za-z]{1,3}[\"']?(?:[\s,|]|$)")

DEFAULT_WORD_COMMENT_MARKER = re.compile(r"Commented\s*\[A\d+")
DEFAULT_ATTACHED_DOC_HEADING = re.compile(r"^(?:Overview)\s*$")

DEFAULT_SUBJECT_FALLBACK_RE = re.compile(r"^\s*Subjec\w*:?\s*(.+)$", re.I)

DEFAULT_STRIP_QUOTED_RE = re.compile(
    r"^(Best regards|Best wishes|Warm regards|Kinds?\s+regards|"
    r"With best wishes|Yours sincerely|Yours,|Best,)", re.I)
# "Thanks," and "Many thanks" are real sign-offs on their own, but are also
# how a lot of genuine prose opens ("Thanks, Jeremy. Great chatting with you
# and Patrick...", "Many thanks for the update..."). Verified against both
# corpora: every *bare* occurrence of these two phrases is a sign-off, every
# occurrence with more than a name/comma after it is not -- so these two are
# only trusted when the whole line is short (see strip_quoted() in core.py).
DEFAULT_STRIP_QUOTED_SHORT_RE = re.compile(r"^(Thanks,|Many thanks)", re.I)

DEFAULT_RECIPIENT_TOKENS = frozenset({"to", "cc", "bcc", "ce", "fe", "pe", "gc"})

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct",
     "nov", "dec"], 1)}

DEFAULT_STAMP_US_RE = re.compile(
    r"(\d{1,2})/(\d{1,2})/(\d{4})\s+(?:at\s+)?(\d{1,2}):(\d{2})(?::(\d{2}))?"
    r"\s*([AaPp]\.?[Mm]\.?)")
DEFAULT_STAMP_LONG_RE = re.compile(
    r"(?:[A-Za-z]+,?\s+)?([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})\s+"
    r"(?:at\s+)?(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([AaPp]\.?[Mm]\.?)")
DEFAULT_STAMP_DMY_RE = re.compile(
    r"(\d{1,2})\s+([A-Za-z]{3,9})\.?\s*,?\s*(\d{4})\s+(?:at\s+)?(\d{1,2}):(\d{2})"
    r"(?::(\d{2}))?\s*([AaPp]\.?[Mm]\.?)?")
DEFAULT_STAMP_OFFSET_RE = re.compile(r"\((?:UTC|GMT)?\s*([+-])\s*(\d{1,2}):?(\d{2})\)", re.I)
DEFAULT_STAMP_PARTIAL_RE = re.compile(
    r"(?:[A-Za-z]+,?\s+)?([A-Za-z]{3,9})\.?\s+(\d{1,2})\s*(?:,|:|$)")


@dataclass
class Profile:
    # ── identity / I/O ──────────────────────────────────────────────────────
    source_id: str
    source_file: str          # e.g. "po-emails.pdf" -- recorded in the output
    title: str                # e.g. "P.O. emails (FOI release)"
    ocr_txt: str
    out_json: str
    out_map: str

    # ── correspondents ───────────────────────────────────────────────────────
    sender_roster: list        # [(compiled regex, canonical name), ...]
    first_names: set           # lowercase first names seen in recipient lists
    # Full alternation of correspondent-name fragments, used by
    # is_header_fragment() to tell a torn-off header scrap from stray prose.
    header_fragment_name_re: "re.Pattern"

    # ── time zones ───────────────────────────────────────────────────────────
    zone_by_affiliation: list  # [(compiled regex, zoneinfo key, why), ...]
    default_zone: str
    default_zone_why: str
    zone_overrides: dict = field(default_factory=dict)
    # Zone chosen by the stamp's own date format, when no explicit offset is
    # present: {stamp_status: (zone key, why)}, e.g. {"day-month-year":
    # ("Europe/London", ...)}. A UK-locale client prints day-month-year on its
    # own clock, so a frozen quote in that format is London time whoever
    # sent it. Empty by default, so releases that don't set it are unaffected.
    # DISABLED: no release sets this. Kept only so the option can be re-tested;
    # see page_based/ZONE_AND_DATE_ANALYSIS.md, section 0c (P-a).
    zone_by_stamp_format: dict = field(default_factory=dict)
    # Named zone abbreviations that count as an explicit offset when a stamp
    # carries one: {"AEDT": 11, ...} (hours from UTC). Empty by default. A
    # stamp that names its zone is the strongest evidence there is, so it
    # outranks the stamp-format and page-owner rules.
    named_zone_offsets: dict = field(default_factory=dict)
    # A Congressional release can be a mash-up of several mailboxes' own
    # exports, each carrying its owner's Bates-style stamp in the bottom
    # corner of the page ("GARRY0000098", "LIP0003421", ...) -- a page is
    # matched against this regex (group(1) = the owner prefix) and the
    # prefix looked up in page_owners for a (zoneinfo key, why) pair. A
    # prefix present here with a None value means "recognised, but not
    # confidently a single owner's own mailbox" (e.g. a recurring legal-
    # review/processing stamp spanning many different real mailboxes) --
    # deliberately left unresolved rather than guessed at, until it can be
    # pinned down. See THREADING_PLAN.md (P.O. Slack project) for the
    # reasoning and the evidence behind a given release's table.
    page_owner_re: "re.Pattern" = None
    page_owners: dict = field(default_factory=dict)   # prefix -> (zone_key, why) | None

    # ── OCR clean-up (release-specific scanner/print noise) ─────────────────
    furniture_re: "re.Pattern" = None       # boilerplate lines to drop outright
    noise_tail_re: "re.Pattern" = None      # avatar/ribbon debris after a value
    # optional: str -> str, applied to every line (pipe/bullet/glued-word
    # fixes specific to one release)
    extra_clean_line: object = None

    # ── header grammar ───────────────────────────────────────────────────────
    field_aliases: dict = field(default_factory=dict)
    msg_open_re: "re.Pattern" = None
    hdr_date_re: "re.Pattern" = None
    inline_quote_re: "re.Pattern" = None
    max_header_lines: int = 80
    reopen_min_distance: int = 16
    # Tokens (lowercased field-alias forms) that mean "this is a recipient
    # field" rather than a terminal one (Subject/Sent/Date/Importance) --
    # decides both how long a wrapped To:/Cc: list is trusted, and which
    # field ends the body's top-of-message field-recovery sweep.
    recipient_tokens: frozenset = DEFAULT_RECIPIENT_TOKENS
    # Freeze rule: read a quoted/forwarded block on the clock of the author of
    # the message that quotes it (see reconcile_zones() in core.py).
    freeze_rule_author_zone: bool = True
    subject_fallback_re: "re.Pattern" = DEFAULT_SUBJECT_FALLBACK_RE

    # ── signature / quote / attachment cutting ───────────────────────────────
    sig_name_re: "re.Pattern" = DEFAULT_SIG_NAME_RE
    sig_affil_re: "re.Pattern" = None
    strip_quoted_re: "re.Pattern" = DEFAULT_STRIP_QUOTED_RE
    strip_quoted_short_re: "re.Pattern" = DEFAULT_STRIP_QUOTED_SHORT_RE
    word_comment_marker_re: "re.Pattern" = DEFAULT_WORD_COMMENT_MARKER
    attached_doc_heading_re: "re.Pattern" = DEFAULT_ATTACHED_DOC_HEADING

    # ── stamp parsing ─────────────────────────────────────────────────────────
    stamp_us_re: "re.Pattern" = DEFAULT_STAMP_US_RE
    stamp_long_re: "re.Pattern" = DEFAULT_STAMP_LONG_RE
    stamp_dmy_re: "re.Pattern" = DEFAULT_STAMP_DMY_RE
    stamp_offset_re: "re.Pattern" = DEFAULT_STAMP_OFFSET_RE
    stamp_bare_offset_re: "re.Pattern" = None   # e.g. "... 10:37:46 +0000"
    stamp_partial_re: "re.Pattern" = DEFAULT_STAMP_PARTIAL_RE
    stamp_de_re: "re.Pattern" = None            # German Von/Gesendet stamps
    months_de: dict = None

    def __post_init__(self):
        if self.msg_open_re is None:
            self.msg_open_re = DEFAULT_MSG_OPEN_RE
        if self.hdr_date_re is None:
            self.hdr_date_re = DEFAULT_HDR_DATE_RE
        if self.inline_quote_re is None:
            self.inline_quote_re = DEFAULT_INLINE_QUOTE_RE
        if self.furniture_re is None:
            # Matches nothing by default; a release should supply its own.
            self.furniture_re = re.compile(r"(?!)")
        if self.noise_tail_re is None:
            self.noise_tail_re = re.compile(
                r"\s*[|Il\[\]{}<>«»“”„’‘—–\-–—_=+*#§¶©®™✓✔✗✘»«»…]+"
                r"\s*(?:[a-zA-Z]{1,4})?\s*$")
        if self.sig_affil_re is None:
            self.sig_affil_re = re.compile(
                r"^(?:ARC |THE |UNIVERSITY|University|Institut|CENTRE|Centre|"
                r"School|Department|Dept\.|Faculty|College|Hospital|Institute|"
                r"Trust|Laborator|Director|Regents|Dean|Regent|"
                r"Professor Emeritus|Marie Bashir|Wellcome|MRC|NIH|NIAID|"
                r"Atlanta|Bethesda|London|Sydney)\b")
