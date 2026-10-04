---
name: backlog
description: File-based project backlog for work shared between an owner and coding agents - one Markdown file per open task (priority, executor, autonomy, effort), a generated INDEX.md answering "where is the owner needed / what is quick / what can run overnight", an idea inbox and a ledger of closed tasks, all kept by one stdlib Python script that lives in the repo. Use this skill whenever the user wants task tracking, a backlog, a TODO system or a roadmap set up in a project; says tasks are scattered over TODO.md, ROADMAP files, audits or chat; asks to move existing task lists into one place; asks what to check, what is quick or what to leave for the night; or when the repo already has backlog/config.json and tasks have to be created, taken, ported, closed, or areas, executors and freezes changed. Also for the same requests in Russian - «беклог», «заведи задачу», «список задач», «разбери inbox», «перенеси TODO в беклог», «что взять на ночь».
---

# Backlog

A backlog that lives in the repository as plain files and is kept by a script, built for a
project where a human owner and one or more agents work together.

In the commands below `<skill>` is the directory this SKILL.md is in, and `backlog.py` stands for
the command the project's own `backlog/README.md` names (usually `python tools/backlog.py`).

## Why it is shaped this way

Each choice answers a failure seen in practice; knowing them lets you judge cases the rules
do not name.

- **One place.** Tasks scattered over TODO.md, roadmaps, audit reports and chat get lost and get
  done twice. Everything open is in `backlog/`, and other documents carry no "what is left" lists.
- **One file per task, generated summaries.** A single TODO file grows until every session pays
  for all of it in context. A session reads `INDEX.md`, the table of its area and only the task
  files it needs.
- **Only the script changes the structure.** IDs, the index, the ledger and cross-links are
  written by `backlog.py`, so they stay consistent and `check` can prove it. Hands write only the
  body and fields of a task.
- **Fields answer the owner's questions.** `executor`, `autonomous` and `effort` exist so the
  index can say where the owner is needed, what an agent can finish quickly and what can be left
  to an unattended run. A task whose fields are careless poisons those lists.
- **Ideas cost one line.** A thought on the go goes to `inbox.md` without fields; it becomes a
  task or leaves when someone sorts the inbox.
- **Closed tasks leave.** A closed task is one line in `done/<month>.md`; its body stays in git
  history. The open set stays small and true.

## Which situation is this

| The repo has | Do |
|---|---|
| `backlog/config.json` | Work with it: see "Working with the backlog". The project's `backlog/README.md` is the local law; where it differs from this file, it wins |
| No backlog, no task lists | "Setting it up" |
| No backlog, but TODO.md, roadmaps, issue dumps, audit findings | "Setting it up", then [references/migrate.md](references/migrate.md) |
| A backlog that needs a new area, executor, machine, tag, freeze, another language, or a newer tool | [references/config.md](references/config.md) |

## Setting it up

1. **Read the project before asking anything.** Find what the installer needs:
   - *Areas* - the streams of work a session can own: modules, platforms, clients, services.
     Usually 2-7, plus `other` (prefix `GEN`) for process, design, repository and the owner's
     decisions. A small single-module project takes one area named after the product, and `other`
     only if there is real work outside the code. An area is a folder name and an ID prefix:
     `web` / `WEB`. Keep prefixes to 2-5 capitals and away from tokens that occur in text with
     numbers (`UTF`, `ISO`, `RFC`, `HTTP`): IDs are found by pattern.
   - *Language* of the project's documents: `en` and `ru` are built in. Task text, README and
     the index follow it.
   - *Executors* - who can be assigned: `claude` (agent) and `owner` by default. Add another
     agent (`--executor codex:Codex:X:agent`) or a named person (`...:human`) only if they
     really take tasks; each needs a one-letter mark of its own.
   - *Places* - only if some tasks can be done on one machine or environment and not another
     (a Mac for the iOS build, a server with the data). Two machines that can both do everything
     need no places: `take` keeps their sessions apart.
   - *Tool path* - where the project keeps scripts (`tools/`, `scripts/`), and how it calls
     Python (`python`, `python3`, `py`).
2. **Ask only what the repository cannot tell**, in one message, with your proposal already
   filled in - typically the list of areas. If the layout is obvious, or nobody is there to
   answer, take the reasonable choice, go on and say what you chose: areas and executors are
   cheap to change later ([references/config.md](references/config.md)).
3. **Install:**
   ```bash
   python <skill>/scripts/init_backlog.py --root <project> --lang en \
       --area api:API:"Server" --area web:WEB:"Web client" --area other:GEN:"Other" \
       [--where pc,mac] [--night-where pc] [--executor codex:Codex:X:agent] \
       [--tag "stand:needs the test server"] [--tool tools/backlog.py] [--python python3]
   ```
   It writes `backlog/` (config, README, empty inbox, `done/`), copies `backlog.py` into the
   project and builds the index. The project then owns its copy: nothing depends on this skill
   being installed, so other agents and people can use the backlog too.
4. **Put the rule it prints into the project's agent instructions**, fitted to that file's
   language and style: `CLAUDE.md` (create it if the project has none), and `AGENTS.md` as well
   when it exists or when an agent other than Claude is an executor. This step is what makes
   later sessions use the backlog: without the rule it decays into one more TODO file. Remove or
   redirect older instructions that point to TODO files. If the project has a place that lists
   its documents (a README section, a docs index), link `backlog/INDEX.md` there; do not invent
   such a place.
5. **Do not invent tasks to fill it.** Move in what already exists (migration), add what the user
   names, and record loose ends you actually saw while reading the project.
6. Run `check` and show the user `INDEX.md`. Commit only if the project's rules or the user ask
   for it, by the project's own commit rules.

## Working with the backlog

**At the start of a session** read `backlog/INDEX.md`, then the table of your area
(`backlog/<area>.md`), then only the task files you will touch. Never read the whole directory:
the summaries exist so that you do not have to.

| The user says | Do |
|---|---|
| "Where am I needed?", "what should I check?" | `backlog.py list --owner`, or the first section of INDEX.md |
| "Anything quick?" | `backlog.py list --quick` |
| "What can you do overnight / while I am away?" | `backlog.py list --night`, then work down it by priority |
| "Note this idea" | `backlog.py idea "text"` - no questions, no fields |
| "Make a task", or you notice a loose end | `backlog.py new`, see below, then write the body |
| "The same for the other client/module" | `backlog.py port <ID> <area>` - a linked task there; the source stays |
| The task sits in the wrong area | `backlog.py move <ID> <area>` - a new ID there, references rewritten |
| Work finished | `backlog.py done <ID> ok "what came out, commit"` |
| "Sort the inbox" | Each line becomes a task or, if the owner turns it down, leaves |

**Creating a task.** Say the fields instead of relying on defaults: a bare `new` gives `P2`, the
first agent and `autonomous: yes`, which is the optimistic reading of any task.

```bash
backlog.py new web "Show the unread count on the tab" --p P1 --who claude --auto partly \
    --effort 3h --tags check,bug --related API-004 --after API-002 --due 2026-01-31 \
    --from "review of the inbox screen"
```

Lists are comma-separated. `--related` links the named open tasks back to the new one;
`--after` names tasks that have to be closed first. The command prints the file: open it and
replace the template with the real body - `check` refuses a body left as the template. The index
is rebuilt by every command; after editing a field by hand, run `backlog.py index`.

**Record loose ends at once.** When you notice something undone that is outside the current
change, make it a task then, not a remark in the final message: the conversation ends and takes
its memory with it.

**Close honestly.** `ok` only when "Done when" holds. `partial` when part is done - and the rest
becomes a new task, or the task stays open with its body edited. `failed` when it was tried and
did not work; `dropped` when it is no longer wanted. The comment says what came out and names
the commit, because the ledger line is all a later reader sees without digging in git.

**Before committing** a change to the backlog run `backlog.py check`. It verifies fields, IDs,
references between tasks and that the generated files are fresh.

**In reports to the owner** name task IDs: created, closed, and the ones now waiting for them.

## Writing a task another session can pick up

A task is read by someone with none of your context - often another agent weeks later. Write for
that reader.

| Field | How to decide |
|---|---|
| `title` | The outcome, up to 70 characters, in the project's language. "Show the unread count on the tab", not "Unread" |
| `priority` | `P0` blocks work now · `P1` important, the next days · `P2` normal, the default · `P3` someday. If everything is P1, nothing is |
| `executor` | Who does the work. The owner only when it truly needs their hands: a decision, a login, a device, a purchase |
| `autonomous` | `yes` only if an agent can both do it *and verify the result* alone - this is what "fit for overnight" means. `partly` if the agent does it and the owner checks or decides at the end. `no` if it cannot start without the owner |
| `effort` | The executor's working time, upper bound: `15m`, `2h`, `1d`, `2-3d`. For the owner's tasks - their minutes, so they see what fits into a spare moment |
| `where` | A machine or environment the task is bound to; `any` otherwise |
| `due` | A real deadline, `YYYY-MM-DD`; empty when there is none |
| `tags` | `check` (verify by hand or eye) and `decision` (the owner decides) sort the owner's section; the rest is the project's vocabulary in `config.json` |
| `related` | Tasks this one pairs with or should be read with. Both directions for a port |
| `after` | Tasks that have to be closed before this one can start. While any is open the task stays out of the quick and overnight lists |
| `from` | Where it came from: document and section, review, conversation. It keeps the trail when lists are migrated |

`taken` is not written by hand: `take` and `release` set it.

The body, in this order, each part short:

- **What to do** - one to three paragraphs; numbered steps if the work is large.
- **For the owner** - exactly what is needed from them, if `autonomous` is not `yes`. Make it
  doable from this line alone: where to click, what to look at, what answer you need.
- **Done when** - an outcome that can be checked. This is the contract for closing.
- **Context** - what confirms the problem, why it matters, what happens if it is left.
- **Materials** - `path:line`, logs, documents, related commits.

How work is cut into tasks:

- Work for two areas is two tasks linked through `related`, so each closes on its own.
- A step of a large task that stands by itself is its own task.
- Work that waits for something only the owner can give - an account, a key, a decision - is two
  tasks: a small one for the owner (`--who owner`, their minutes as effort) and the agent's own
  with `--after` naming it. The owner sees a five-minute item instead of a two-day task they
  cannot judge, and the agent's task enters the lists the moment the owner closes theirs.
- A check the owner has to do lives in the area of the thing checked, not in `other`: the area
  table then shows the work and its verification side by side.
- A long plan is a document next to the code, and the task points to it - the backlog holds
  tasks, not designs.

## Several sessions at once

Skip this part for one agent on one machine. It matters as soon as two sessions, two machines or
two agents write to the same backlog: task numbers are unique only once pushed, so sessions
working side by side can take the same one.

- `git pull` or `git fetch` before `new`: it counts the files on disk and the fetched upstream.
- Create a task close to the commit that carries it, not at the start of the work.
- After a merge or rebase run `check`. If it reports a number taken twice, `backlog.py reid <ID>`
  gives your task the next free number, fixes the links it made itself and lists files that
  still carry the old one. Change those by hand, and only where they mean *your* task - the other
  session's references share the number. Your own line in the `done/` ledger is fixed by hand too.
- `INDEX.md` and the area tables are never merged by hand: on a conflict take either side and
  run `backlog.py index`.
- When several sessions or machines pick from the same list, mark what you start:
  `backlog.py take <ID> "machine, session"`, push at once, and leave alone what another session
  marked. `done` clears the mark; `release` returns a task you dropped.

## Reference files

- [references/migrate.md](references/migrate.md) - moving TODO files, roadmaps, audits and issue
  lists into the backlog without losing entries; read before a migration.
- [references/config.md](references/config.md) - `config.json` fields, adding and freezing areas,
  executors, places, tags, another language, upgrading the tool; read before changing the layout.
- `scripts/backlog.py` - the tool; `scripts/init_backlog.py` - the installer and upgrader;
  `assets/` - templates of the project's `backlog/README.md` and of the agent-instructions rule.
