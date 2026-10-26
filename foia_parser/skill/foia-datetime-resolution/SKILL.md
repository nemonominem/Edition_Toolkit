---
name: foia-datetime-resolution
description: >
  Decide the true date and time of each message in a FOIA'd or released email
  dump, when the printed stamps carry no reliable zone. Use this when a parser
  must turn printed "Sent:"/"Date:" stamps into one timeline, when copies of the
  same message disagree by hours, when a reply appears before the message it
  answers, or when a mailbox's clock is unknown. Covers the ordered rules, the
  evidence tests (exact copies with an explicit offset, reply-order sensitivity,
  same-instant duplicates), the rules that look right but fail, and how to report
  what is still unsettled. Read this together with foia-email-pdf, which covers
  OCR, segmentation and the basic zone grammar.
---

# FOIA datetime resolution

The question is not "what does the stamp say" but "on which clock was it printed".
A stamp is the time on the clock of whichever mailbox displayed or quoted the
message at that point. The sender's clock and the viewer's clock are often
different, and quoted copies are frozen in the replier's clock.

Work in this order. Do not skip the evidence tests to get to a rule faster.

## 1. Ordered rules (apply the first that matches)

1. **Explicit zone in the stamp.** A numeric offset (`+0000`, `UTC+11:00`) or a
   named zone (`AEDT`, `EST`, `PST`) is used as written. This outranks everything.
2. **Exact copy with an explicit offset (anchor).** If an entry's text matches an
   explicit-offset copy (similarity >= 0.95, same or adjacent day), take that copy's
   instant. The same message at the same moment is the strongest evidence there is.
   See `scripts/anchor_copies.py`.
3. **Verified from the page image.** A hand-checked correction, with its evidence
   recorded beside it (see `scripts/apply_verified_overrides.py` in the PO Slack
   project). Use it where the page or the message text fixes both the printed time
   and its clock, for example "It is 10pm now UK" beside a printed 5:23 PM. Never
   change the entry's identifier when you correct its time.
4. **Quoted or forwarded copy takes the replier's zone.** A frozen block is on the
   clock of the client that quoted it, where that link is known. This is *not*
   always the quoting author's own zone, and it is not the zone of the quoting
   message's own printed stamp (that stamp can be on yet another clock). Use it
   as a default, and expect exceptions that only evidence can fix.
5. **Unzoned top-level stamp, from a sender's institution.** Use the sender's own
   zone, as a stated assumption, recorded in the output.
6. **Unzoned top-level stamp, from a known exporting mailbox.** Use that owner's
   zone, as a stated assumption, recorded in the output.
7. **Otherwise: leave the time unresolved** and say so. Do not guess.

Record the rule that set each time, in plain words, next to the time. A reader must
be able to see which assumption a given time depends on.

## 2. Evidence tests

Use these to test an assumption, not to set times directly.

- **Exact-copy test.** Find copies of the same message that carry an explicit
  offset. Each one gives a direct check on the zone of its unzoned neighbours.
  Often there are only a few. Report how many tests you ran.
- **Reply-order test.** A reply cannot be sent before the message it answers. For a
  zone group, shift all its entries by whole hours and count linked reply pairs that
  then run backwards. The shifts with zero violations are the ones the data allows.
  A group whose only allowed shift is 0 is consistent with the data; a group with
  several allowed shifts is not decided. See `scripts/reply_order_check.py`.
  **Limit: it only catches a reply that comes before its parent.** A quoted copy
  that is simply too early causes no violation, so the test passed on an entry that
  was five hours wrong. Treat "only 0 allowed" as *supported*, never as *settled*.
  It also depends on the reply links being right, so check those first.
- **Same-instant duplicate test.** Copies with the same instant and the same text
  are one message. Keep the one with an explicit offset, then the fuller sender name.
  See `scripts/dedupe_same_instant.py`. **Never run it on a partial or unparsed
  stamp:** those carry a defaulted time (noon), so two different messages can share
  it. A "fragment" rule that ignored this deleted a real message.
- **Header-fragment test.** An entry with no body text, whose date, time, sender
  and subject all match a full entry (and whose time is real), is a broken copy of it.
- **Link integrity, after every removal.** Repoint reply links to the entry that was
  kept, drop links that become self-references or duplicates, and drop an *inferred*
  link that the corrected times put backwards (explicit links stay). Then check there
  are no dangling or one-sided links and no reply before its parent.

Run the owner or group test on the whole dataset first, then per group, and report
each group's status separately.

## 3. Rules that look right and fail

- **Date format as a clock.** A 24-hour day-month-year stamp may look like a UK
  client, but a US client can use a day-first format, and web clients may print no
  locale cue at all. It agreed with only two independent checks in one project.
  Do not use it as a working rule. Keep it as a hypothesis with its evidence.
- **Long (US) format as Eastern.** A US-format stamp is on a US clock, but which US
  zone depends on the mailbox. Eastern was the only zone tested.
- **A page owner decides every stamp on its pages.** The owner's export clock
  applies to messages it displays, not to every stamp; a copy quoted from another
  clock keeps that clock. Use the owner zone only for unzoned top-level stamps.
- **A default zone for a whole release.** One default for all unzoned stamps moved
  many entries by hours. Default only where a rule says so.
- **Sender institution for a frozen copy.** The sender's zone is right for the
  original, not for a copy forwarded from another mailbox. Where a copy has an
  explicit offset, it overrides the sender.
- **OCR-dropped stamps.** A stamp whose time was lost in OCR looks like a partial
  stamp. Read the time from the page image before deciding it has no time.
- **"The quoted block is on the quoting author's zone."** Tried as a rule from the
  author's institution. On one project it would have changed 59 of 150 quoted entries
  and created 11 reply-order violations, with shifts as large as 19 hours. The clock a
  block is frozen on depends on the client, not only on where the author lives.

## 4. What to report

For every zone source, report:

- how many entries it sets;
- the assumption, in one sentence;
- the evidence and how many tests it passed or failed;
- status: **settled** (fixed by the stamp, an exact copy, the page image, or a
  decision by the person who owns the data), **supported** (consistent with every
  test, including reply order, but the tests cannot prove it), or **not settled**
  (too few tests, or several zones survive).

Keep these as a table, and keep a per-entry column (rule, status, reason) so a
reader can filter the open entries. Do not describe an assumption as a fact.

## 5. Process

1. Build the entries with the parser, keeping each stamp's printed text and format.
2. Apply rules 1 to 7 in order, recording the rule for each entry.
3. Run the exact-copy test, the same-instant duplicate test and the header-fragment
   test. Apply their results.
4. Run the reply-order test per zone group. Update each group's status.
5. Regenerate the per-entry audit file and the status table after every rebuild.
   A stale audit file is worse than none.
6. Send the open items to the person who can settle them, each with the page
   reference, the entry and the question.

## Worked example

The PO Slack project (`PO_Slack/page_based`, `PO_Slack/tools`, `PO_Slack/analysis`)
applied these rules to two email releases (about 390 entries). It settled the
explicit stamps, one exact-copy anchor, three entries corrected from page images, and
the REV page owner (one exact pair, accepted by the data owner). LIP and two sender
institutions are *supported* by reply order only. It left open the GARRY owner, several
small sender groups, two quoted copies and eight undated entries. A review of that
project found, and fixed, a deleted message, dangling links and overstated statuses; the
lessons are in the rules above.
`analysis/ZONE_AND_DATE_ANALYSIS.md` is the full record, including the rejected rules.

## Scripts

- `scripts/anchor_copies.py`: rule 2 (exact-copy anchor).
- `scripts/owner_zone_check.py`: exact-copy pairs per page owner.
- `scripts/reply_order_check.py`: reply-order test per zone group.
- `scripts/dedupe_same_instant.py`: same-instant and header-fragment removal, with
  link repointing.
- `scripts/apply_verified_overrides.py`: rule 3 (verified corrections; needs a
  `verified_overrides.json` of entries, stamps, zones and evidence).

These are reference implementations written for the PO Slack JSON schema (entries
with `stamp`, `stamp_status`, `zone_assumed`, `thread_key`, `replied_by`). Adapt the
field names to a new release's schema before use.

See also `foia-email-pdf` for OCR, segmentation and the zone grammar.
