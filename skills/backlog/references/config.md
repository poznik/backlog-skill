# config.json and changing the layout

`backlog/config.json` holds everything that differs between projects. The tool reads it on every
run; after any change run `backlog.py index` and `backlog.py check`, and update the matching
passage of `backlog/README.md` (the list of areas, the tag vocabulary, the sample task) - the
README is written once at install time and is the project's own file from then on.

```json
{
  "lang": "en",
  "command": "python tools/backlog.py",
  "areas": {
    "api": {"prefix": "API", "title": "Server"},
    "web": {"prefix": "WEB", "title": "Web client"},
    "other": {"prefix": "GEN", "title": "Other"}
  },
  "frozen": {
    "web": "frozen 2026-03-02 by the owner: the web client is paused until the API settles"
  },
  "executors": {
    "claude": {"title": "Claude", "mark": "C", "role": "agent"},
    "owner": {"title": "owner", "mark": "O", "role": "owner"},
    "codex": {"title": "Codex", "mark": "X", "role": "agent"},
    "anna": {"title": "Anna, design", "mark": "A", "role": "human"}
  },
  "where": ["pc", "mac", "any"],
  "night_where": ["pc", "any"],
  "night_executors": ["claude"],
  "tags": {
    "check": "verify by hand or by eye",
    "decision": "the owner's decision",
    "stand": "needs the test server"
  },
  "blocks": {
    "login": "Sign-in and accounts",
    "billing": "Billing"
  },
  "quick_minutes": 60,
  "labels": {}
}
```

| Field | Meaning |
|---|---|
| `lang` | `en` or `ru`: the language of INDEX.md, area tables, ledger lines and task templates |
| `command` | How the project's documents call the tool; printed in generated files |
| `areas` | Folder → ID prefix and heading. Order here is the order in the index |
| `frozen` | Area → reason with a date. Its tasks stay but leave the owner, quick and overnight lists |
| `executors` | Key used in task files → heading, one-letter mark for tables (each its own), and `role`. Installed with `claude` and `owner` |
| `where` | Places a task can be bound to. With a single entry the column is not shown |
| `night_where` | Places the overnight list takes tasks from; empty means any |
| `night_executors` | Executors the overnight list is for; empty means every agent |
| `tags` | Allowed tags with their meaning. `check`, `decision` and `port` are always allowed |
| `blocks` | Optional. Functional block → heading, the same keys for every area. A task names one in its `block` field; `report` groups by them in this order. Without it tasks carry no block |
| `quick_minutes` | The upper bound of the "quick" list |
| `labels` | Overrides for single lines the tool writes; see "Another language" |

Roles drive the views: `owner` puts a task into "Owner needed" whatever its `autonomous` is;
`agent` makes it eligible for the quick and overnight lists; `human` is anyone else - a
colleague, a contractor - whose tasks show only in the area tables.

## Common changes

**Add an area.** Add it to `areas` with a new prefix, run `index` (its table appears), add it to
the list in README.md. Tasks that belong to it but sit elsewhere are moved one by one with
`backlog.py move <ID> <area>`: the task gets the next number of the new area and every reference
to the old ID inside `backlog/` is rewritten. References outside the backlog (reports, commit
messages) keep the old ID, so say in the task's `from` where it came from if that matters.

**Remove an area.** Close or `move` its open tasks first, then delete it from `areas`. Its
closed tasks stay in the ledger; keep the prefix unused so old IDs remain unambiguous.

**Freeze an area.** Only on the owner's word. Add `"area": "reason, date"` to `frozen`, run
`index`. Tasks stay; sessions do not take them; do not create ports into a frozen area. Unfreeze
the same way, again only on the owner's word.

**Add an executor.** A second agent or a named person: add to `executors` with a unique mark and
a role. If the overnight list should stay with one agent, name it in `night_executors`. An agent
that is not Claude reads `AGENTS.md`, not `CLAUDE.md`: put the backlog rule there too.

**Add a place.** Only when some tasks can be done in one place and not another. Put it before
`any` in `where`; decide whether unattended runs can use it and add it to `night_where` if so.
From then on tasks bound to a machine carry `where: <place>`.

**Change a task's fields.** Edit the front matter of its file, then run `index`: the summaries are
built from the files and go stale otherwise, which `check` reports.

**Add functional blocks.** When the owner wants the backlog cut by feature and not only by area:
agree on 5-12 blocks that cover the product (features the owner would name, plus one for
architecture and upkeep), add them to `blocks`, then write `block: <key>` after `tags:` in the
task files - by reading titles, and bodies where a title is not enough. `check` refuses a block
that `blocks` does not name; a task without one is allowed and falls under "No block" in the
report. New tasks get it with `new --block`, a port inherits its source's. Add the field and the
list of blocks to the project's `backlog/README.md`.

**Add a tag.** Add it to `tags` with a one-line meaning and to the list in README.md. Keep the
vocabulary small: tags that describe a needed resource (a test server, a live counterpart, a
device) earn their place; tags that repeat a field do not.

## Another language

`lang` selects a built-in table (`en`, `ru`). For any other language keep `lang` as the nearest
built-in one and override lines in `labels`. The keys are those of the `LABELS` table at the top
of `backlog.py` - copy the `en` table, translate the values, keep the `{placeholders}`:

```json
"labels": {
  "index_title": "Backlog-Übersicht",
  "owner": "Inhaber gefragt",
  "result_ok": "erledigt"
}
```

Translate `backlog/README.md` and the rule in CLAUDE.md by hand. The result words
(`result_ok` …) are parsed back from the ledger, so set them before the first task is closed and
do not change them later. Messages the tool prints to the terminal stay in English.

## Upgrading the tool

The project owns its copy of `backlog.py`. To replace it with the one in this skill:

```bash
python <skill>/scripts/init_backlog.py --root <project> --upgrade
```

It copies the tool to the path named in `command`, prints the old and new versions, rebuilds the
index and runs `check`. Look at the diff before committing: if the project changed its copy,
carry those changes over by hand.

## Bringing an older hand-rolled backlog under this tool

A project that already has `backlog/<area>/<ID>.md` files in this format but a script with areas
written into its code needs only a `config.json` describing the same areas, executors, places
and tags. Write it, run `index`, and compare the generated files with the committed ones: apart
from wording they should match. `check` may warn about numbers that were closed twice in the
past - those are old races between sessions; a warning does not fail the check, and the history
stays as it is.
