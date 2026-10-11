#!/usr/bin/env bash
# Refresh the local Markdown export of the three "Proximal Origin -- A
# Tragicomedy of our Times" Medium pieces (Summary, Part 1, Part 2) after an
# online correction, into the exact files PO_Slack's build_po_guide.py reads
# (page_based's DEFAULT_ARTICLE_DIR).
#
# Run this on a machine with normal network access to medium.com -- the
# Claude session that asked for this script is Cloudflare-blocked from
# reaching Medium at all (confirmed both via a direct Playwright test and
# via this exact tool), so it cannot run this itself.
#
# What this does NOT do: medium-to-md.py has no PDF export. The three .pdf
# twins next to the .md files (used by PO_Slack's Tragicomedy reader tab)
# were produced some other way (most likely: open each article in a
# browser, Print -> Save as PDF). After this script finishes, re-do that
# for each of the three articles and save over the matching .pdf filename
# printed below -- this script will remind you again at the end.
#
# Usage:
#   cd /Users/gillesdemaneuf/Work/Edition/medium_to_md
#   ./refresh_proximal_origin.sh
#
# Output:
#   examples/proximal_origin/<slug>.md   -- overwritten in place, 3 files
#   logs/refresh_proximal_origin_<timestamp>.log -- full audit log of this run

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$HERE/examples/proximal_origin"
LOG_DIR="$HERE/logs"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/refresh_proximal_origin_${TS}.log"
WAIT_SECONDS="${WAIT_SECONDS:-6}"

mkdir -p "$OUT_DIR" "$LOG_DIR"

# Each entry: slug (-> <slug>.md, the exact filename PO_Slack expects) and
# the article's own URL on the author's subdomain (medium-to-md.py derives
# the output filename from the URL's last path segment, so this must be the
# long-slug form, not a short medium.com/p/<id> link, or the filename won't
# match what's already on disk / what PO_Slack's PARTS list names).
SLUGS=(
  "summary-proximal-origin-a-tragicomedy-of-our-times-1ed5b4dae506"
  "full-text-proximal-origin-a-tragicomedy-of-our-times-draft-p1-626c72cb05b1"
  "full-text-proximal-origin-a-tragicomedy-of-our-times-draft-p2-39b90684bf01"
)
LABELS=("Summary" "Part 1" "Part 2")

log() { echo "$*" | tee -a "$LOG_FILE"; }

log "=== Refresh run started $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
log "Output dir: $OUT_DIR"
log "Log file:   $LOG_FILE"
log ""

# --- environment check -------------------------------------------------
if command -v conda >/dev/null 2>&1; then
  # shellcheck disable=SC1091
  source "$(conda info --base)/etc/profile.d/conda.sh"
  if conda env list | grep -q 'python_313x'; then
    conda activate python_313x
    log "Activated conda env: python_313x"
  else
    log "WARNING: conda env 'python_313x' not found -- using whatever 'python3' resolves to."
  fi
else
  log "WARNING: conda not found -- using whatever 'python3' resolves to."
fi

if ! python3 -c "import playwright" >/dev/null 2>&1; then
  log "FATAL: the 'playwright' package is not importable in this Python. Run:"
  log "  pip install -r requirements.txt   (or: conda install -c conda-forge playwright)"
  exit 1
fi

# playwright install is idempotent/fast if the browser is already present.
log "Ensuring the Playwright Chromium browser is installed..."
playwright install chromium >>"$LOG_FILE" 2>&1

# --- fetch each article --------------------------------------------------
FAILED=()
for i in "${!SLUGS[@]}"; do
  slug="${SLUGS[$i]}"
  label="${LABELS[$i]}"
  url="https://gillesdemaneuf.medium.com/${slug}"
  out_md="$OUT_DIR/${slug}.md"

  log ""
  log "--- ${label}: ${url}"
  log "    -> ${out_md}"

  # medium-to-md.py prints its own debug trail (page title, block/char
  # counts, a Cloudflare-challenge warning if blocked) -- captured verbatim
  # into the log for audit, in addition to going to the console. Success is
  # judged below from the actual output file, not this exit code.
  #
  # --headed: headless Chrome gets fingerprinted by Medium's Cloudflare
  # protection and served a hard "Attention Required!" challenge instead of
  # the article (confirmed on this exact script, both from the sandboxed
  # Claude session and from a real machine with normal network access) -- a
  # real, visible browser window passes it with no interaction needed. This
  # requires an actual display; it will not work over a headless/CI session.
  python3 "$HERE/medium-to-md.py" "$url" --dir "$OUT_DIR" --wait "$WAIT_SECONDS" --headed 2>&1 \
    | tee -a "$LOG_FILE"

  if [ ! -s "$out_md" ]; then
    log "    FAILED: ${out_md} is missing or empty."
    FAILED+=("$label")
    continue
  fi
  chars=$(wc -c < "$out_md" | tr -d ' ')
  if [ "$chars" -lt 1000 ]; then
    log "    FAILED: ${out_md} is only ${chars} bytes -- almost certainly a blocked/challenge page, not the article."
    FAILED+=("$label")
    continue
  fi
  log "    OK: ${chars} bytes"
done

# --- summary ---------------------------------------------------------------
log ""
log "=== Summary ==="
if [ "${#FAILED[@]}" -eq 0 ]; then
  log "All 3 articles fetched successfully."
else
  log "FAILED (${#FAILED[@]}): ${FAILED[*]}"
  log "Re-run this script, or increase WAIT_SECONDS, e.g.: WAIT_SECONDS=15 ./refresh_proximal_origin.sh"
fi

log ""
log "=== Still needed: the PDF twins (this tool has no PDF export) ==="
for slug in "${SLUGS[@]}"; do
  log "  - open https://gillesdemaneuf.medium.com/${slug} in a browser,"
  log "    Print -> Save as PDF, overwrite: $OUT_DIR/${slug}.pdf"
done

log ""
log "=== Refresh run finished $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

[ "${#FAILED[@]}" -eq 0 ]
