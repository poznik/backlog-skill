## Tasks

**Tasks live only in [backlog/](backlog/README.md)**, since {{DATE}}: one file per open task in
`backlog/<area>/`, the summary is [backlog/INDEX.md](backlog/INDEX.md), closed tasks are a line in
`backlog/done/`. A session reads INDEX.md and only the files of its own tasks. Tasks are
created, ported between areas and closed with `{{COMMAND}}` (`new`, `port`, `done`, `idea`), which
also rebuilds the index; run `{{COMMAND}} check` before committing a change to the backlog. No
plans, "what is left" lists or TODOs in other documents: a loose end noticed along the way becomes
a task at once, and a long plan is a document next to the code, which a task points to.
