# TODO

## Management rules

- **Statuses:** `Open` · `Working` · `Validate` · `Closed` · `Implicit`
- **Open** — task is queued and not yet started.
- **Working** — task is actively in progress in the current session.
- **Validate** — task is finished by the AI and awaiting human review. Use automatically for any non-trivial completed task where genAI output should be checked (substantive writing, structural changes, factual claims). Trivial tasks with no genAI risk (formatting, file moves, mechanical edits) skip this and go straight to `Closed`.
- **Closed** — task is fully done and verified (or trivial enough to need no review); keep the entry for record.
- **Implicit** — task was requested directly in chat without referencing this list, was large enough to be worth logging, and has been completed. Kept for record.
- On each pass, move tasks through their correct status before starting work and again after completing it. Never leave a task as `Working` at the end of a session.
- Menial or trivial tasks (single-step edits, quick formatting fixes) do not need an entry here.

---

## Tasks
1. `Open` · **Fix footer declaration in md_to_pdf** — there is some hardcoding going on, that refers to the generic style css. We need to keep that generic. So either have a local copy, or a local json, with specific overwrite.

2. `Open` · **There are issues with the references/notes in the Proximal Origin mds** — oddities - needs investigatingthen fixing.

3. `Open` · **Style review / style conversion utility** — Create utility to review Markdown against Demaneuf_Medium style guide or convert between article writing styles (see `.github/docs/writing-styles.md` for style definitions).

4. `Open` · **Fact-check utility** — Create utility to validate factual claims in Markdown articles against sources, cross-reference footnotes, and flag unsourced assertions (integrates with grounding protocol if needed).

5. `Open` · **Batch processing pipeline** — Extend medium_to_md to support extracting multiple Medium articles and combining into single Markdown file or booklet structure for md_to_booklet.
