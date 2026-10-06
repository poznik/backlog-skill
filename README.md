# backlog

[По-русски](README.ru.md)

A skill for Claude that keeps a project's tasks in the repository as plain files, for work shared
between a human owner and one or more coding agents.

- One Markdown file per open task, with a few fields: priority, executor, how far an agent can go
  alone, effort.
- A generated `INDEX.md` that answers three questions: where is the owner needed, what can an agent
  finish quickly, what can be left to an unattended run.
- An inbox for ideas, one line each, and a ledger of closed tasks by month.
- One Python script, standard library only, that lives in the project. After the setup nothing
  depends on the skill or on Claude: any agent or person can use the backlog.

The scheme comes from a real project: several clients on a shared core, about 300 open tasks,
agent sessions on two machines at once.

## What it looks like

```
backlog/
  INDEX.md            built by the script: owner needed / quick / overnight
  api.md  web.md      built by the script: all open tasks of an area, one row each
  api/API-001.md      an open task
  web/WEB-001.md
  inbox.md            ideas, one line each
  done/2026-10.md     closed tasks, one line each
  config.json         areas, executors, places, tags, freezes
  README.md           the rules, in the project's language
tools/backlog.py      the script
```

A task:

```markdown
---
id: API-002
title: Send the weekly digest from staging
priority: P2
executor: claude
autonomous: yes
effort: 1h
where: any
due:
tags: []
related: []
after: [GEN-001]
created: 2026-10-04
from: review of the mail module
---
What to do, in one to three paragraphs.

**Done when:** an outcome that can be checked.
**Context:** what confirms it, why it matters.
**Materials:** `src/mail/digest.py:40`, logs, documents.
```

The index built from six such tasks, shortened:

```markdown
## Owner needed — 2

### To decide — 1

- [GEN-002](other/GEN-002.md) · P2 · 5m · Decide: keep or drop the dark theme

### To do or to give access — 1

- [GEN-001](other/GEN-001.md) · P2 · 10m · Create the staging account at the mail provider

### The agent does it, the owner comes in at the end — 1

- Web client: [WEB-001](web/WEB-001.md)

## Quick: the agent alone, up to 1 h — 1

## Overnight — 1

[API-001](api/API-001.md) 2h
```

`API-002` is in neither list: it comes `after` the owner's `GEN-001` and enters them when that
one is closed.

## Install

**Claude Code, as a plugin:**

```
/plugin marketplace add poznik/backlog-skill
/plugin install backlog@backlog-skill
```

**Claude Code, as a personal skill:**

```bash
git clone https://github.com/poznik/backlog-skill
cp -r backlog-skill/skills/backlog ~/.claude/skills/backlog
```

**Claude apps:** take `backlog.skill` from the
[latest release](https://github.com/poznik/backlog-skill/releases/latest) and add it in the skills
settings.

**Without Claude:** the installer and the tool are plain Python 3.8+.

```bash
python backlog-skill/skills/backlog/scripts/init_backlog.py --root <project> \
    --area api:API:"Server" --area web:WEB:"Web client" --area other:GEN:"Other"
```

## Use

In a project, say what you need:

- "Set up a backlog here" — Claude reads the project, proposes areas, installs `backlog/` and the
  script, and prints the rule to put into `CLAUDE.md` or `AGENTS.md`.
- "Move TODO.md and the roadmap into the backlog" — every old entry becomes a task or gets a
  written reason why not; the old files go to an archive with a map from entries to tasks.
- "Where am I needed?", "anything quick?", "what can you do overnight?"
- "Note this idea", "make a task", "the same for the other client", "sort the inbox".

The commands behind them:

| Need | Command |
|---|---|
| A new task | `backlog.py new api "Title" --p P2 --who claude --auto yes --effort 2h` |
| The same work for another area | `backlog.py port API-001 web` |
| An idea on the go | `backlog.py idea "text"` |
| Close | `backlog.py done API-001 ok "what came out, the commit"` |
| Take into work, let go | `backlog.py take API-001 "machine, session"`, `release API-001` |
| Lists | `backlog.py list --owner`, `--quick`, `--night`, `--area api`, `--tag bug` |
| A report: who does it, priority, block, cost | `backlog.py report --area api,web --p P1,P2 --who alone` |
| Check before a commit | `backlog.py check` |
| Move to another area | `backlog.py move API-001 web` |
| A fresh number after two sessions took one | `backlog.py reid API-001` |

## Settings

Everything that differs between projects is in `backlog/config.json`: areas with their ID
prefixes, frozen areas, executors and their roles (agent, owner, another person), places a task
can be bound to, the tag vocabulary, the language of the generated files. English and Russian are
built in; other languages go through `labels`. See
[references/config.md](skills/backlog/references/config.md).

## Several sessions at once

Task numbers are unique only once pushed. The tool counts the numbers of the fetched upstream when
it creates a task, `check` reports a number taken twice after a merge, and `reid` gives one of the
two a fresh number. `INDEX.md` and the area tables are never merged: on a conflict they are
rebuilt.

## What is inside

| Path | What |
|---|---|
| [skills/backlog/SKILL.md](skills/backlog/SKILL.md) | The instructions Claude follows |
| [skills/backlog/scripts/backlog.py](skills/backlog/scripts/backlog.py) | The tool that is copied into a project |
| [skills/backlog/scripts/init_backlog.py](skills/backlog/scripts/init_backlog.py) | The installer and upgrader |
| [skills/backlog/references/](skills/backlog/references/) | Migration of old task lists; `config.json` and changing the layout |
| [skills/backlog/assets/](skills/backlog/assets/) | Templates of the project's `backlog/README.md` and of the rule for agent instructions |

Upgrading the tool in a project that already has a backlog:

```bash
python backlog-skill/skills/backlog/scripts/init_backlog.py --root <project> --upgrade
```

## License

[Apache-2.0](LICENSE).
