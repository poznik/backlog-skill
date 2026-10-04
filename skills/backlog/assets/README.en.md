# Backlog

The only place for the project's open tasks since {{DATE}}. No plans, "what is left" lists or TODOs
in other documents: a loose end noticed along the way becomes a task at once, and a long plan is a
document next to the code, which a task points to.

## What is where

| File | What | Who reads it |
|---|---|---|
| [INDEX.md](INDEX.md) | Summary: where the owner is needed, what is quick, what can run overnight. **Built by the script** | Every session, first |
| {{AREA_TABLES}} | All open tasks of an area, one table row each. **Built by the script** | A session of that area |
| {{AREA_DIRS}} | Open tasks, one file per task | Only the one needed |
| [inbox.md](inbox.md) | Ideas and wishes, one line each, not sorted yet | The owner writes, a session sorts |
| [done/](done/) | Ledger of closed tasks, by month | When history is needed |
| [config.json](config.json) | Areas, executors, places, tags, freezes | Whoever changes how the backlog is laid out |

Areas:

{{AREAS}}

**Freezing an area.** An area the owner froze is listed in `frozen` of [config.json](config.json)
with the reason and the date. Its tasks stay in the backlog, but sessions do not take them, and
INDEX.md and `list --owner`, `--quick`, `--night` leave them out. Only the owner unfreezes it: the
line leaves `frozen` and the index is rebuilt.

## A task

File `<area>/<ID>.md`, IDs are {{ID_EXAMPLES}}.

```markdown
---
id: {{EXAMPLE_ID}}
title: A short title                    # up to 70 characters
priority: P2                            # P0 blocks · P1 important, the next days · P2 normal · P3 someday
executor: {{OWNER}}                         # {{EXECUTORS}}
autonomous: no                          # yes — the agent does and verifies it alone, fit for overnight
                                        # partly — the agent does it, the owner checks or decides at the end
                                        # no — cannot start without the owner: a login, a device, a decision
effort: 5m                              # 15m, 2h, 1d, 2-3d — the executor's work
where: any                              # {{WHERE}} — where it is done
due:                                    # YYYY-MM-DD, if there is a deadline
tags: [check]                           # the vocabulary is below
related: [{{EXAMPLE_ID_2}}]                    # related tasks, including the other half of a port
after: [{{EXAMPLE_ID_2}}]                      # only when it cannot start before these are closed
created: {{DATE}}
from:                                   # where it came from: a document and section, a review, a talk
---
What to do — one to three paragraphs.

**For the owner:** what exactly is needed from them (when autonomous is not yes).
**Done when:** an outcome that can be checked.
**Context:** what confirms it, why it matters, what happens if it is left undone.
**Materials:** code (`path:line`), logs, documents.
```

The notes after `#` belong to this sample only: in a task file a field's value runs to the end of
the line. `after` is written only when the task waits for others: until they are closed it stays
out of the quick and overnight lists. A task taken into work gets one more field, `taken`: who and
when. After changing a field by hand, run `{{COMMAND}} index`.

Tags (`tags`):

{{TAGS}}

By the tags `check` and `decision` INDEX.md splits what waits for the owner into "To check" and
"To decide". A new tag goes into `tags` of [config.json](config.json) first.

## How to work

Everything goes through `{{COMMAND}}`, which also rebuilds INDEX.md and the area tables; they are
not edited by hand.

| Need | Command |
|---|---|
| A new task | `{{COMMAND}} new {{EXAMPLE_AREA}} "Title" --p P2 --who {{AGENT}} --auto yes --effort 2h` — a file with the template, then write the body. Also `--tags check,bug`, `--related {{EXAMPLE_ID_2}}`, `--after {{EXAMPLE_ID_2}}`, `--due`, `--where`, `--from` |
| The same for another area | `{{COMMAND}} port {{EXAMPLE_ID}} {{EXAMPLE_AREA_2}}` — a task linked to the source one |
| An idea on the go | `{{COMMAND}} idea "text"`, or a line in [inbox.md](inbox.md) by hand |
| Close | `{{COMMAND}} done {{EXAMPLE_ID}} ok "what came out, the commit"` — `ok` · `partial` · `failed` · `dropped` |
| Take into work | `{{COMMAND}} take {{EXAMPLE_ID}} "machine, session"`, let go with `release {{EXAMPLE_ID}}` |
| Where the owner is needed | `{{COMMAND}} list --owner` |
| Quick ones for the agent | `{{COMMAND}} list --quick` |
| Overnight | `{{COMMAND}} list --night` — `autonomous: yes`, by priority |
| Check | `{{COMMAND}} check` — fields, IDs, references, a fresh index |
| The task belongs to another area | `{{COMMAND}} move {{EXAMPLE_ID}} {{EXAMPLE_AREA_2}}` — a new number there, references to it rewritten |
| Another session took the number | `{{COMMAND}} reid {{EXAMPLE_ID}}` — the next free number |

Rules:

- A session reads INDEX.md, the table of its area and only the files of its own tasks. The whole
  directory is never read: the summaries exist so that it does not have to be.
- A loose end noticed along the way becomes a task at once instead of living in the conversation.
- Finished work is closed with `done`: the task file is removed and `done/<month>.md` gets a line
  with the date, the result and a comment — what came out and in which commit. Partly finished work
  is `partial`, with the rest as a new task; or the task stays open and its body is edited.
- `autonomous: yes` is only for work the agent can both do and verify alone. If the owner's eye or
  word is needed at the end it is `partly`; if the work cannot start without them it is `no`.
- Large work is a task with steps in its body; a step that stands on its own is a task of its own,
  linked through `related`. A long plan is a separate document next to the code, and the task
  points to it.
- Work for two areas is two tasks linked to each other through `related`, so each closes on its own.
- Work that waits for the owner's step — an account, a key, a decision — is two tasks: a small one
  for the owner and the agent's own with `after` naming it. The owner sees a few minutes of work,
  and the agent's task enters the lists the moment that one is closed.
- `inbox.md` is sorted by any session when the owner asks or when it has more than ten lines: a
  line becomes a task, or leaves if the owner turned it down.
- Before committing a change to the backlog, run `{{COMMAND}} check`.

Several sessions at once:

- `new` takes the next free number from the files on disk and from the upstream branch already
  fetched, so run `git pull` or `git fetch` before it. Create a task close to the commit, not at the
  start of the work: a number is free only until someone else pushes it.
- If a number was taken twice after all, `check` says so after the merge. `reid <ID>` gives your
  task a new number and names the files that still carry the old one; your own line in the `done/`
  ledger is fixed by hand.
- INDEX.md and the area tables are not merged on a conflict but rebuilt: `{{COMMAND}} index`.
- A task taken into work is marked with `take` and pushed at once. Before taking a task, `git pull`,
  and leave alone one marked by another session. `done` removes the mark together with the file;
  `release` lets go of a task that was dropped.
