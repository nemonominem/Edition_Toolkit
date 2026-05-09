# Contributing & LLM Usage

This repository uses a simple convention to coordinate human contributors and LLM-powered edits. This file is the single source of truth for that workflow.

## Summary

- Use `//` markers in Markdown files to give short, actionable instructions to an LLM. Put each `//` instruction on its own line.
- After the LLM performs the requested action, it must remove the `//` marker line to indicate the instruction has been handled.
- Always update the project TODO list (file `TODO.md` in the repo root) when tasks are completed.

## How to write `//` instructions

- Keep instructions concise and localized near the content they affect.
- Prefer clear verbs and minimal metadata.
- Place the `//` line directly above the paragraph, figure, or block it pertains to.
- Keep a single `//` instruction per line.

### Common instruction patterns

- `// IMPORT_IMAGE: path=<rel-path> caption="..."`
  - Insert the image markdown at the instruction location and remove the `//` line.

- `// INSERT_TEXT: target=<marker-id> text="..."`
  - Replace or insert the specified text at the named location, then remove the `//` line.

- `// INSERT_CAPTION: target=<rel-path> caption="..."`
  - Add or replace the caption for the referenced image or figure, then remove the `//` line.

- `// TODO_MARK_DONE: id=<todo-id>`
  - Mark the referenced TODO entry as completed in `TODO.md` and remove the `//` line.

- `// TODO_DONE: <short description>`
  - Use for simple local tasks when no TODO identifier is present; once handled, remove the `//` line and update `TODO.md` if relevant.

- `// REVIEW: note="..."`
  - Leave a short review note; do not remove surrounding content unless explicitly instructed.

## Best practices for LLMs and automation

- Always remove the `//` line after successfully performing the instruction.
- When a `// TODO_MARK_DONE` instruction is present, update `TODO.md` to reflect completion.
- If human review is required, prefer `// REVIEW: reason` rather than a destructive edit.
- If an instruction cannot be completed safely, leave a brief plain-text note explaining why rather than another `//` instruction.

## Todo bookkeeping

- Update `TODO.md` when work is completed. If automation is present, ensure the automation marks tasks completed immediately after execution.
- Use clear task titles or IDs in the TODO list so collaborators and bots can match items to `//` instructions reliably.

## Examples

Markdown before LLM action:

```markdown
Some analysis paragraph.
// IMPORT_IMAGE: path=images/image2.png caption="Figure 2 — site photo"
```

After LLM action:

```markdown
Some analysis paragraph.
![Figure 2 — site photo](images/image2.png)
```

Another example:

```markdown
Analysis paragraph.
// REVIEW: note="Check whether this quote needs a stronger source"
```

If you have questions about this workflow, open an issue.

## Chat commands

Short commands prefixed with `*` can be typed directly in chat to trigger standard actions without writing out a full instruction.

| Command | Default | Action |
|---|---|---|
| `*todo` | same as `*todo list` | Display the current state of `.github/workflow/todos.md` — all tasks with their statuses. |
| `*todo list` | — | Display the current state of `.github/workflow/todos.md`. |
| `*todo done <n>` | — | Mark task `<n>` as `Closed` in `.github/workflow/todos.md`. |
| `*todo validate <n>` | — | Mark task `<n>` as `Validate` (awaiting human review) in `.github/workflow/todos.md`. |
| `*todo working <n>` | — | Mark task `<n>` as `Working` in `.github/workflow/todos.md`. |
| `*todo add <text>` | — | Append a new `Open` task with `<text>` as its description. |
| `*todo order` | — | Analyse all `Open` and `Working` tasks and propose a recommended processing order with brief rationale for each step; flag dependencies between tasks. |

When a `*todo` command is received, execute the action immediately and confirm with a brief summary. No need to ask for permission.
