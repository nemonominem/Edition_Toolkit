# Contributing & LLM Usage

This repository uses a simple convention to coordinate human contributors and LLM-powered edits. This file is the single source of truth for that workflow.

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
