# Moving existing task lists into the backlog

Use this when a project already has TODO.md, roadmaps, audit reports, "what is left" sections,
exported issues or notes with tasks in them. The aim: after the migration there is exactly one
place with open tasks, every old entry is accounted for, and nothing useful in the old
documents is lost.

## Principles

- **Every entry gets a fate.** Each item of the old lists either becomes a task or gets a
  written reason why not: done, obsolete, turned down by the owner, covered by another entry,
  not a task (a rule, a decision, background). Silent dropping is what makes owners distrust a
  migration.
- **Old documents become reference, not a to-do list.** They usually hold more than tasks:
  protocol notes, decisions with dates, designs. Freeze them in an archive folder instead of
  deleting or rewriting them.
- **A task must stand without the old document.** Copy the facts it needs into its Context and
  Materials; `from` only says where it came from.
- **Do not judge for the owner.** If it is unclear whether an entry is still wanted, make it a
  task tagged `decision` with `executor: owner`, or put it in `inbox.md` - do not drop it.
- **Rules still in force do not go into the archive alone.** An old list often carries a decision
  among its tasks ("payments only through provider X", "no new dependencies in the core"). It
  is not a task, but a later session will never open the archive to find it: copy it to where
  the project keeps its rules (`CLAUDE.md`, a decisions document) and note that in the map.
- **The ledger is for work closed through the backlog.** Entries that were already done before
  the migration get a line in the map ("not moved: done"), not a line in `done/`.

## Steps

1. **Install the backlog** (SKILL.md, "Setting it up") if it is not there.
2. **Inventory the sources.** Search for task-bearing documents: `TODO*`, `ROADMAP*`, `PLAN*`,
   `AUDIT*`, `NOTES*`, "TODO"/"осталось"/"next steps" sections in READMEs and docs. Code comments
   (`TODO`, `FIXME`) are a separate question - ask the owner before sweeping them in; usually
   they stay. Tell the owner the list of sources and the rough number of entries before starting;
   if nobody is there to answer, go on and put the same list into the final report.
3. **Go source by source, entry by entry.** For each entry decide: task(s), or not moved and why.
   - One entry may become several tasks (one per area), and several entries one task.
   - Create with `new`, passing `--from "TODO.md, «Section» / «Item»"`; then write the body.
   - The same entry for a second area: `port <ID> <area>`, then give the new task a title of
     its own and a `from` naming the old document - a port made during a migration is an
     ordinary task of that area, not a follow-up.
   - An entry that waits for another ("after the API is ready") gets `--after <ID>`.
   - Set fields honestly from what the entry says. Verification items the owner must do by hand
     are `--who owner --auto no --tags check` with their minutes as effort; open questions are
     `--tags decision`.
   - Half-formed wishes with no plan go to `inbox.md` (`idea`), not into tasks.
4. **Write the map** as you go: `MIGRATION.md` in the archive folder, one line per old entry:
   ```
   - TODO.md «Login» / «Remember me checkbox» → WEB-014
   - TODO.md «Login» / «Captcha» → not moved: turned down by the owner 2026-03-02
   - ROADMAP.md «Phase 2», item 3 → API-007, WEB-015
   - ROADMAP.md «Principles», item 1 → not a task: a rule, now in CLAUDE.md «Payments»
   ```
   The map is what lets anyone later find where an old reference went. Write it with the IDs
   the tasks have at that moment; step 6 rewrites them together with the tasks.
5. **Archive the sources**: move them (`git mv`, so history follows) to something like
   `docs/archive/<date>-tasks/` with a short README saying what the folder is, that it is
   reference and not a list of work, and that new tasks go only to `backlog/`. Fix links that
   pointed to the moved files.
6. **Renumber densely, once.** During a migration tasks are created, merged and deleted, and the
   numbers end up with gaps and in no order. Before anything is closed:
   ```bash
   backlog.py renumber --also docs/archive/<date>-tasks/MIGRATION.md
   ```
   It numbers each area from 001 by priority and rewrites IDs in the backlog and in the files
   given with `--also`. It refuses once the ledger has closed tasks - numbers are permanent from
   then on.
7. **Point the project at the backlog**: the rule in `CLAUDE.md` / `AGENTS.md`, a note where the
   old files were mentioned, and remove instructions like "add it to TODO.md".
8. **Run `check`**, then show the owner: how many entries, how many became tasks, how many were
   not moved and the main reasons, and the top of INDEX.md.

## Large migrations

Hundreds of entries are too many for one pass in one context.

- Split by source and line range and hand ranges to subagents. Each returns its part of the map.
- Parallel workers would take the same numbers. Give each a disjoint number range to write task
  files into by hand (worker A: 001-199, worker B: 200-399), or let workers return task drafts
  and create the files in one place. The final `renumber` makes the numbers dense either way.
- Give every worker the same brief on fields and on the "every entry gets a fate" rule, and the
  list of areas with what belongs to each.
- Afterwards read the area tables yourself: look for duplicates between workers (two tasks from
  entries that described the same thing in different documents) and merge them, keeping both
  `from` trails in the map.

## After the migration

For some weeks old habits and old memories will say "it is in TODO.md" or "see ROADMAP". Treat
such a reference as pointing into the archive, find the task through the map, and do not
resurrect the old files.
