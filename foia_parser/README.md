# foia_parser

Shared grammar for turning a FOIA'd, OCR'd email-correspondence PDF into one
structured entry per message (sender, timestamp, zone, subject, thread
links, page map). Extracted from the Proximal Origin project's
`parse_po_emails.py` / `parse_farrar_fauci.py` once both had converged on the
same rules, so a fix (or a bug) in the shared grammar reaches every release
that imports it instead of needing to be ported by hand into each project's
own copy-pasted parser.

See `skill/foia-email-pdf/SKILL.md` alongside this README for the hard-won lessons behind the
rules (OCR-vs-native-text-layer detection, the segmentation grammar, time
zone handling, OCR noise patterns, long/redacted mailing lists, embedded
attachments) — load it before writing or debugging a parser for a new
release.

## Install

From a consuming project:

```
pip install "git+https://github.com/nemonominem/Edition_Toolkit.git#subdirectory=foia_parser"
```

Or, during development, an editable local install:

```
pip install -e /Users/gillesdemaneuf/Work/Edition/foia_parser
```

Pin to a commit SHA once a release's parser depends on this in a way that
needs to be reproducible — git tags on this repo apply to the whole
Edition_Toolkit, not to this subdirectory alone, so there is no clean
per-package semver tag to pin to instead.

## Usage

Everything generic (segmentation, header splitting, signature cutting, stamp
parsing, OCR clean-up, threading, page-map building, JSON output) lives in
`core.py`. Everything that varies release to release — the correspondent
roster, which affiliation implies which time zone, which OCR glyph noise
that particular scan leaves behind, which header-field spellings/languages
appear — is supplied by the caller as one `Profile` (see `profile.py`):

```python
from foia_parser import Profile, run_release
import re

profile = Profile(
    source_id="my-release",
    source_file="my-release.pdf",
    title="My release (FOI)",
    ocr_txt="my-release_ocr.txt",
    out_json="my-release.json",
    out_map="my-release_page_map.json",
    sender_roster=[(re.compile(r"andersen", re.I), "Kristian G. Andersen"), ...],
    first_names={"kristian", "edward", ...},
    header_fragment_name_re=re.compile(r"andersen|holmes|...", re.I),
    zone_by_affiliation=[(re.compile(r"scripps", re.I), "America/Los_Angeles",
                          "Scripps Research"), ...],
    default_zone="Europe/London",
    default_zone_why="Wellcome Trust (the release's convener)",
    furniture_re=re.compile(r"^(CONFIDENTIAL|...)", re.I),
    field_aliases={"ce": "Cc", "fe": "To", ...},
)
run_release(profile)
```

A project keeps its own `parse_<release>.py` as a thin script: it defines the
`Profile` for that release (its roster, its zone table, its own OCR noise
patterns) and calls `run_release()`. See PO_Slack's `parse_po_emails.py` and
`parse_farrar_fauci.py` for two worked examples drawing on the same library.
