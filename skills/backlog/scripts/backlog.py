#!/usr/bin/env python3
"""Keep a project backlog in ``backlog/``: tasks, their index and the ledger of closed ones.

Each open task is ``backlog/<area>/<ID>.md`` with a small front matter block (see
``backlog/README.md``). ``backlog/INDEX.md`` and one table per area are generated from those
files and are never edited by hand; a closed task leaves its file and becomes one line in
``backlog/done/<YYYY-MM>.md``. Areas, executors, places, tags and the language of the generated
files come from ``backlog/config.json``.

Usage, from anywhere in the repository::

    python tools/backlog.py index                       # rebuild INDEX.md and the area tables
    python tools/backlog.py check                       # fields, IDs, references, fresh index
    python tools/backlog.py list [--owner|--quick|--night] [--area web] [--tag bug]
    python tools/backlog.py report [--area web,api] [--p P1,P2] [--who alone,together]
                                   [--block login] [--tag bug] [--group area,block]
                                   [--sort who,priority,effort]   # Markdown: who, cost, blocks
    python tools/backlog.py new web "Title" [--p P2] [--who claude] [--auto yes]
                                [--effort 2h] [--where any] [--due 2026-01-31]
                                [--tags check,bug] [--related API-004] [--after API-002]
                                [--block login] [--from "TODO.md, Login"]
    python tools/backlog.py port WEB-012 ios            # the same work for another area
    python tools/backlog.py idea "text"                 # one line into backlog/inbox.md
    python tools/backlog.py done WEB-012 ok "comment"   # ok | partial | failed | dropped
    python tools/backlog.py take WEB-012 ["who"]        # mark as in work; release WEB-012 undoes
    python tools/backlog.py reid WEB-012                # a fresh ID after two sessions took one
    python tools/backlog.py move WEB-012 api            # the task belongs to another area
    python tools/backlog.py renumber [--also FILE]      # dense IDs, only before anything is closed

The backlog directory is ``backlog/`` next to or above this script, then above the current
directory; ``--dir`` or the ``BACKLOG_DIR`` variable name another one.

Exit code 0 on success, 1 when ``check`` finds problems or a command is refused.
Python 3.8+, standard library only.
"""

import argparse
import datetime
import json
import os
import re
import socket
import subprocess
import sys

__version__ = "1.1.0"

CONFIG_NAME = "config.json"
PRIORITIES = ("P0", "P1", "P2", "P3")
AUTONOMOUS = ("yes", "partly", "no")
AUTO_MARK = {"yes": "+", "partly": "~", "no": "−"}
ROLES = ("agent", "owner", "human")
RESULTS = ("ok", "partial", "failed", "dropped")
FIELDS = ("id", "title", "priority", "executor", "autonomous", "effort", "where", "due", "tags",
          "block", "related", "after", "created", "from", "taken")
LISTS = ("tags", "related", "after")
OPTIONAL = ("block", "after", "taken")  # written only when set
REQUIRED = ("id", "title", "priority", "executor", "autonomous", "effort", "where", "created")
# Tags the tool itself relies on: the owner's section groups by the first two, `port` sets the third.
STRUCTURAL_TAGS = ("check", "decision", "port")
RESERVED = ("done", "index", "readme", "inbox", "config")
AREA_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
PREFIX = re.compile(r"^[A-Z][A-Z0-9]{1,7}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EFFORT = re.compile(r"^(\d+(?:[.,]\d+)?)(?:-(\d+(?:[.,]\d+)?))?\s*(m|h|d)$")
UNIT = {"m": 1, "h": 60, "d": 480}
# Who a task waits for, as the report tells it: the agent alone, the agent with the owner's
# hands or word, the owner, anyone else.
WHO = ("alone", "together", "owner", "other")
REPORT_GROUPS = ("area", "block", "who", "priority")
REPORT_SORTS = ("who", "priority", "effort", "area", "block", "id")
DEFAULT_EXECUTORS = {
    "claude": {"title": "Claude", "mark": "C", "role": "agent"},
    "owner": {"title": "owner", "mark": "O", "role": "owner"},
}

# Everything the tool writes into the backlog's own files. `lang` in config.json picks a table,
# `labels` there overrides single lines, which is also how a third language is added.
LABELS = {
    "en": {
        "index_title": "Backlog index",
        "generated": "Built by `{cmd} index`, do not edit by hand.",
        "index_see": "Rules and fields — [README.md](README.md), closed — [done/](done/), "
                     "ideas — [inbox.md](inbox.md).",
        "open": "Open {n}: {counts}.",
        "inbox_count": "Ideas in the inbox: {n}.",
        "frozen_index": "**Frozen:** [{title}]({area}.md) — {why}. Its tasks are left out below.",
        "frozen_area": "**Frozen:** {why}.",
        "owner": "Owner needed",
        "owner_check": "To check",
        "owner_decide": "To decide",
        "owner_do": "To do or to give access",
        "owner_later": "The agent does it, the owner comes in at the end",
        "quick": "Quick: the agent alone, up to {limit}",
        "quick_note": "P0–P2 below, all {n} — `{cmd} list --quick`.",
        "night": "Overnight",
        "night_note": "The agent alone, P0–P2{where}, by priority. In detail — "
                      "`{cmd} list --night`.",
        "night_where": ", where: {places}",
        "area_see": "Built by `{cmd} index`, do not edit by hand; summary — [INDEX.md](INDEX.md).",
        "legend": "Who: {who}. Alone: + yes, ~ partly, − no.",
        "col_who": "Who",
        "col_auto": "Alone",
        "col_where": "Where",
        "col_effort": "Effort",
        "col_task": "Task",
        "due": "due {date}",
        "taken": "in work: {who}",
        "after": "after {ids}",
        "minutes": "{n} min",
        "hours": "{n} h",
        "result_ok": "done",
        "result_partial": "partly",
        "result_failed": "failed",
        "result_dropped": "dropped",
        "ledger_title": "Closed tasks — {month}",
        "ledger_intro": "One line per task: date, ID, title, result, comment. The task body is "
                        "in the git history.",
        "inbox_title": "Ideas and wishes",
        "inbox_intro": "One line per thought: date and text. How they are sorted — "
                       "[README.md](README.md).",
        "body": "\nWhat to do.\n\n{owner}**Done when:** \n**Context:** \n**Materials:** \n",
        "body_owner": "**For the owner:** \n",
        "port_title": "Port: {title}",
        "port_body": "\nBring to «{area}» what was done in {id}: {title}.\n\n**Done when:** \n"
                     "**Context:** \n**Materials:** {id}\n",
        "port_from": "port of {id}",
        "report_title": "Backlog report — {n} tasks, {cost}",
        "report_legend": "Who: {alone} — the agent does and verifies it alone; {together} — the "
                         "agent does it, the owner acts or decides (* cannot start without the "
                         "owner); {owner} — only the owner's own actions. Cost is the sum of the "
                         "estimates, low–high, a day is 8 hours.",
        "report_filter": "Chosen: {what}.",
        "report_summary": "Summary",
        "report_total": "Total",
        "report_none": "no tasks",
        "col_group": "Group",
        "col_tasks": "Tasks",
        "col_cost": "Cost",
        "who_alone": "agent",
        "who_together": "together",
        "who_owner": "owner",
        "who_other": "other",
        "no_block": "No block",
    },
    "ru": {
        "index_title": "Индекс беклога",
        "generated": "Собран `{cmd} index`, руками не править.",
        "index_see": "Правила и поля — [README.md](README.md), закрытые — [done/](done/), "
                     "идеи — [inbox.md](inbox.md).",
        "open": "Открыто {n}: {counts}.",
        "inbox_count": "Идей в inbox: {n}.",
        "frozen_index": "**Заморожено:** [{title}]({area}.md) — {why}. В сводках ниже задач "
                        "этой области нет.",
        "frozen_area": "**Заморожено:** {why}.",
        "owner": "Нужен владелец",
        "owner_check": "Проверить",
        "owner_decide": "Решить",
        "owner_do": "Сделать или дать доступ",
        "owner_later": "Агент делает, в конце — владелец",
        "quick": "Быстрое: агент сам, до {limit}",
        "quick_note": "P0–P2 ниже, все {n} — `{cmd} list --quick`.",
        "night": "На ночь",
        "night_note": "Агент сам, P0–P2{where}; по приоритету. Подробно — `{cmd} list --night`.",
        "night_where": ", где: {places}",
        "area_see": "Собран `{cmd} index`, руками не править; сводка — [INDEX.md](INDEX.md).",
        "legend": "Кто: {who}. Сам: + — да, ~ — частично, − — нет.",
        "col_who": "Кто",
        "col_auto": "Сам",
        "col_where": "Где",
        "col_effort": "Оценка",
        "col_task": "Задача",
        "due": "до {date}",
        "taken": "в работе: {who}",
        "after": "после {ids}",
        "minutes": "{n} мин",
        "hours": "{n} ч",
        "result_ok": "сделано",
        "result_partial": "частично",
        "result_failed": "не вышло",
        "result_dropped": "отменено",
        "ledger_title": "Закрытые задачи — {month}",
        "ledger_intro": "Строка на задачу: дата, ID, заголовок, итог, комментарий. Тело задачи — "
                        "в истории git.",
        "inbox_title": "Идеи и хотелки",
        "inbox_intro": "Строка на мысль: дата и текст. Разбор — [README.md](README.md), "
                       "«Как работать».",
        "body": "\nЧто сделать.\n\n{owner}**Готово, когда:** \n**Контекст:** \n**Материалы:** \n",
        "body_owner": "**Владельцу:** \n",
        "port_title": "Перенос: {title}",
        "port_body": "\nПеренести в область «{area}» то, что сделано в {id}: {title}.\n\n"
                     "**Готово, когда:** \n**Контекст:** \n**Материалы:** {id}\n",
        "port_from": "перенос с {id}",
        "report_title": "Отчёт по беклогу — задач: {n}, стоимость: {cost}",
        "report_legend": "Кто: {alone} — агент делает и проверяет сам; {together} — агент "
                         "делает, владелец действует или решает (* — без владельца не начать); "
                         "{owner} — только действия владельца. Стоимость — сумма оценок, от "
                         "нижней до верхней, день — 8 часов.",
        "report_filter": "Выбрано: {what}.",
        "report_summary": "Сводка",
        "report_total": "Всего",
        "report_none": "задач нет",
        "col_group": "Группа",
        "col_tasks": "Задач",
        "col_cost": "Стоимость",
        "who_alone": "агент",
        "who_together": "вместе",
        "who_owner": "владелец",
        "who_other": "другой",
        "no_block": "Без блока",
    },
}

CFG = None  # set by main()


class Config:
    """``backlog/config.json``: what differs from project to project."""

    def __init__(self, folder):
        self.folder = os.path.abspath(folder)
        self.root = os.path.dirname(self.folder)
        self.index = os.path.join(self.folder, "INDEX.md")
        self.inbox = os.path.join(self.folder, "inbox.md")
        self.done = os.path.join(self.folder, "done")
        path = os.path.join(self.folder, CONFIG_NAME)
        try:
            with open(path, encoding="utf-8-sig") as handle:
                data = json.load(handle)
        except (OSError, ValueError) as error:
            raise SystemExit(f"{path}: {error}")
        self.problems = []
        where = os.path.relpath(path, self.root).replace(os.sep, "/")
        self.command = data.get("command") or "python tools/backlog.py"
        self.areas = {}  # directory: (ID prefix, heading)
        for name, value in (data.get("areas") or {}).items():
            prefix = str(value.get("prefix", ""))
            if not AREA_NAME.match(name) or name in RESERVED:
                self.problems.append(f"{where}: area name {name!r}")
            if not PREFIX.match(prefix):
                self.problems.append(f"{where}: area {name}: prefix {prefix!r} is not like WEB")
            if prefix in [p for p, _ in self.areas.values()]:
                self.problems.append(f"{where}: prefix {prefix} is used twice")
            self.areas[name] = (prefix, value.get("title") or name)
        if not self.areas:
            raise SystemExit(f"{path}: no areas")
        self.frozen = dict(data.get("frozen") or {})
        for name in self.frozen:
            if name not in self.areas:
                self.problems.append(f"{where}: frozen {name!r} is not an area")
        self.frozen = {k: v for k, v in self.frozen.items() if k in self.areas}
        self.executors = data.get("executors") or DEFAULT_EXECUTORS
        for name, value in self.executors.items():
            if value.get("role") not in ROLES:
                self.problems.append(f"{where}: executor {name}: role is one of {', '.join(ROLES)}")
        marks = [value.get("mark", name) for name, value in self.executors.items()]
        for mark in sorted(set(m for m in marks if marks.count(m) > 1)):
            self.problems.append(f"{where}: the mark {mark!r} stands for two executors")
        self.open_ids = set()  # filled by load_tasks()
        self.where = list(data.get("where") or ["any"])
        self.night_where = list(data.get("night_where") or [])
        self.night_executors = list(data.get("night_executors") or [])
        self.tags = tuple(dict.fromkeys(list(STRUCTURAL_TAGS) + list(data.get("tags") or [])))
        self.blocks = {}  # key: heading; a functional block cuts across areas
        for name, value in (data.get("blocks") or {}).items():
            if not AREA_NAME.match(name):
                self.problems.append(f"{where}: block name {name!r}")
            self.blocks[name] = str(value or name)
        self.quick_minutes = int(data.get("quick_minutes") or 60)
        self.labels = dict(LABELS["en"])
        self.labels.update(LABELS.get(data.get("lang") or "en", {}))
        self.labels.update(data.get("labels") or {})
        prefixes = sorted((re.escape(p) for p, _ in self.areas.values()), key=len, reverse=True)
        one = r"(?:" + "|".join(prefixes) + r")-\d{3,}"
        self.id = re.compile(r"\b" + one + r"\b")
        self.entry = re.compile(r"^- \d{4}-\d{2}-\d{2} · \*\*(" + one + r")\*\*\s+(.*)$")

    @property
    def places(self):
        """Whether tasks differ by place at all: one place means no column for it."""
        return len(self.where) > 1


def label(key, **values):
    return CFG.labels[key].format(**values)


def find_backlog(explicit=None):
    chosen = explicit or os.environ.get("BACKLOG_DIR")
    if chosen:
        return chosen
    for start in (os.path.dirname(os.path.abspath(__file__)), os.getcwd()):
        folder = start
        while True:
            candidate = os.path.join(folder, "backlog")
            if os.path.isfile(os.path.join(candidate, CONFIG_NAME)):
                return candidate
            parent = os.path.dirname(folder)
            if parent == folder:
                break
            folder = parent
    raise SystemExit(f"no backlog/{CONFIG_NAME} next to the script, above it or above the "
                     "current directory; pass --dir or set BACKLOG_DIR")


class Task:
    def __init__(self, path, fields, body):
        self.path = path
        self.fields = fields
        self.body = body

    def __getitem__(self, key):
        return self.fields.get(key, [] if key in LISTS else "")

    @property
    def id(self):
        return self.fields.get("id", "")

    @property
    def area(self):
        return os.path.basename(os.path.dirname(self.path))

    @property
    def minutes(self):
        return effort_minutes(self["effort"])

    @property
    def role(self):
        return CFG.executors.get(self["executor"], {}).get("role", "")

    @property
    def who(self):
        """One of WHO: whose hands the task needs."""
        if self.role == "owner":
            return "owner"
        if self.role != "agent":
            return "other"
        return "alone" if self["autonomous"] == "yes" else "together"

    def link(self):
        return f"[{self.id}]({self.area}/{self.id}.md)"

    def sort_key(self):
        number = int(self.id.rpartition("-")[2]) if self.id.rpartition("-")[2].isdigit() else 0
        return (self["priority"] or "P9", self.minutes if self.minutes is not None else 10**9,
                self.id.rpartition("-")[0], number)


def effort_minutes(text):
    match = EFFORT.match((text or "").strip())
    if not match:
        return None
    high = match.group(2) or match.group(1)
    return round(float(high.replace(",", ".")) * UNIT[match.group(3)])


def effort_range(text):
    """(low, high) minutes of an estimate; `2-3d` is a range, `2h` is both ends."""
    match = EFFORT.match((text or "").strip())
    if not match:
        return None
    low = float(match.group(1).replace(",", "."))
    high = float((match.group(2) or match.group(1)).replace(",", "."))
    return round(low * UNIT[match.group(3)]), round(high * UNIT[match.group(3)])


def cost_parts(minutes):
    """Minutes in the unit the estimates are written in: (45, "m"), (3.5, "h"), (12, "d")."""
    for unit in ("d", "h"):
        if minutes >= UNIT[unit]:
            value = minutes / UNIT[unit]
            return round(value) if value >= 10 else round(value, 1), unit
    return minutes, "m"


def cost(tasks):
    """The summed estimates of tasks: `5d`, `5–8d`, `40m–1.5h`, with `+?` when some have none."""
    spans = [effort_range(x["effort"]) for x in tasks]
    low, high = (cost_parts(sum(span[end] for span in spans if span)) for end in (0, 1))
    if low == high:
        text = f"{low[0]:g}{low[1]}"
    elif low[1] == high[1]:
        text = f"{low[0]:g}–{high[0]:g}{high[1]}"
    else:
        text = f"{low[0]:g}{low[1]}–{high[0]:g}{high[1]}"
    return text + (" +?" if None in spans else "")


def parse_list(value):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [item.strip() for item in value.split(",") if item.strip()]


def read_text(path):
    with open(path, encoding="utf-8-sig") as handle:
        return handle.read().replace("\r\n", "\n")


def write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def read_task(path):
    text = read_text(path)
    if not text.startswith("---\n"):
        raise ValueError("no front matter")
    end = text.find("\n---\n", 3)
    if end < 0:
        raise ValueError("front matter is not closed")
    fields = {}
    for row in text[4:end].split("\n"):
        if not row.strip():
            continue
        key, sep, value = row.partition(":")
        if not sep:
            raise ValueError(f"not a field: {row!r}")
        key = key.strip()
        value = value.strip()
        fields[key] = parse_list(value) if key in LISTS else value
    return Task(path, fields, text[end + 5:])


def write_task(task):
    lines = ["---"]
    for key in FIELDS:
        value = task.fields.get(key, [] if key in LISTS else "")
        if key in OPTIONAL and not value:
            continue
        if isinstance(value, list):
            value = "[" + ", ".join(value) + "]"
        lines.append(f"{key}: {value}".rstrip())
    for key in task.fields:
        if key not in FIELDS:
            lines.append(f"{key}: {task.fields[key]}".rstrip())
    lines.append("---")
    write_text(task.path, "\n".join(lines) + "\n" + task.body)


def load_tasks():
    tasks, problems = [], []
    for area in CFG.areas:
        folder = os.path.join(CFG.folder, area)
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".md"):
                continue
            path = os.path.join(folder, name)
            try:
                tasks.append(read_task(path))
            except ValueError as error:
                problems.append(f"{rel(path)}: {error}")
    CFG.open_ids = {x.id for x in tasks}
    return tasks, problems


def ledger_files():
    if not os.path.isdir(CFG.done):
        return []
    return [os.path.join(CFG.done, name) for name in sorted(os.listdir(CFG.done))
            if name.endswith(".md")]


def ledger_title(rest):
    results = "|".join(re.escape(label("result_" + result)) for result in RESULTS)
    match = re.match(r"(.*?)\s+—\s+(?:" + results + r")\.", rest)
    return match.group(1) if match else rest.split(" — ")[0]


def closed_entries(text=None):
    """(ID, title) of every ledger line that closes a task."""
    rows = []
    for chunk in ([text] if text is not None else [read_text(p) for p in ledger_files()]):
        for row in chunk.split("\n"):
            match = CFG.entry.match(row)
            if match:
                rows.append((match.group(1), ledger_title(match.group(2))))
    return rows


def ledger_ids():
    """Every ID the ledger names, in a closing line or in a comment."""
    ids = set()
    for path in ledger_files():
        ids.update(CFG.id.findall(read_text(path)))
    return ids


def git(*args):
    try:
        done = subprocess.run(["git", "-C", CFG.root] + list(args), capture_output=True,
                              encoding="utf-8", errors="replace", timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def upstream_ids():
    """IDs the fetched upstream already holds.

    A task number is only unique once it is pushed, so sessions working side by side take the
    same one. Looking at the upstream the checkout already knows narrows that window; it does
    not fetch, and without git or an upstream it changes nothing.
    """
    for ref in ("@{upstream}", "origin/HEAD", "origin/main", "origin/master"):
        if git("rev-parse", "--verify", "--quiet", ref) is None:
            continue
        base = os.path.basename(CFG.folder)
        names = git("ls-tree", "-r", "--name-only", ref, "--", base + "/")
        if names is None:
            return set()
        ids = set(CFG.id.findall(names))
        for name in names.splitlines():
            if name.startswith(base + "/done/") and name.endswith(".md"):
                ids.update(CFG.id.findall(git("show", f"{ref}:./{name}") or ""))
        return ids
    return set()


def rel(path):
    return os.path.relpath(path, CFG.root).replace(os.sep, "/")


def today():
    return datetime.date.today().isoformat()


# --- views -----------------------------------------------------------------------------------

def needs_owner(task):
    return task.role == "owner" or task["autonomous"] == "no"


def checked_by_owner(task):
    return not needs_owner(task) and task["autonomous"] == "partly"


def waits_for(task):
    """The tasks this one comes after that are still open."""
    return [other for other in task["after"] if other in CFG.open_ids]


def free_for_agent(task):
    return (task["autonomous"] == "yes" and task.role == "agent" and not task["taken"]
            and not waits_for(task))


def quick(task):
    minutes = task.minutes
    return free_for_agent(task) and minutes is not None and minutes <= CFG.quick_minutes


def night(task):
    return (free_for_agent(task) and task["priority"] in PRIORITIES[:3]
            and (not CFG.night_executors or task["executor"] in CFG.night_executors)
            and (not CFG.night_where or task["where"] in CFG.night_where))


def line(task):
    parts = [task.link(), task["priority"], task["effort"] or "?"]
    if CFG.places:
        parts.append(task["where"])
    if task["due"]:
        parts.append(label("due", date=task["due"]))
    text = "- " + " · ".join(parts) + " · " + task["title"]
    if waits_for(task):
        text += " · " + label("after", ids=", ".join(waits_for(task)))
    if task["taken"]:
        text += " · " + label("taken", who=task["taken"])
    return text


def inbox_count():
    if not os.path.exists(CFG.inbox):
        return 0
    return sum(1 for row in read_text(CFG.inbox).split("\n") if row.startswith("- "))


def area_file(area):
    return os.path.join(CFG.folder, f"{area}.md")


def limit_text(minutes):
    if minutes % 60 == 0:
        return label("hours", n=minutes // 60)
    return label("minutes", n=minutes)


def build_index(tasks):
    """Return {path: text} for INDEX.md and one table per area."""
    cmd, areas = CFG.command, CFG.areas
    CFG.open_ids = {x.id for x in tasks}
    out = [f"# {label('index_title')}", "", label("generated", cmd=cmd), label("index_see"), ""]
    by_area = {area: [x for x in tasks if x.area == area] for area in areas}
    counts = " · ".join(f"[{areas[a][1]}]({a}.md) {len(v)}" for a, v in by_area.items())
    prio = " · ".join(f"{p} {sum(1 for x in tasks if x['priority'] == p)}" for p in PRIORITIES)
    out += [label("open", n=len(tasks), counts=counts), "",
            f"{prio}. {label('inbox_count', n=inbox_count())}", ""]
    for area, why in CFG.frozen.items():
        out += [label("frozen_index", title=areas[area][1], area=area, why=why), ""]
    live = [x for x in tasks if x.area not in CFG.frozen]

    owner = sorted((x for x in live if needs_owner(x)), key=Task.sort_key)
    later = sorted((x for x in live if checked_by_owner(x)), key=Task.sort_key)
    out += [f"## {label('owner')} — {len(owner)}", ""]
    groups = ((label("owner_check"), lambda x: "check" in x["tags"]),
              (label("owner_decide"), lambda x: "decision" in x["tags"] and "check" not in x["tags"]),
              (label("owner_do"), lambda x: "check" not in x["tags"]
               and "decision" not in x["tags"]))
    for name, test in groups:
        chosen = [x for x in owner if test(x)]
        if chosen:
            out += [f"### {name} — {len(chosen)}", ""] + [line(x) for x in chosen] + [""]
    if later:
        out += [f"### {label('owner_later')} — {len(later)}", ""]
        for area in areas:
            ids = [x for x in later if x.area == area]
            if ids:
                out.append(f"- {areas[area][1]}: " + ", ".join(x.link() for x in ids))
        out.append("")
    if not owner and not later:
        out += ["—", ""]

    fast = sorted((x for x in live if quick(x)), key=Task.sort_key)
    urgent = [x for x in fast if x["priority"] in PRIORITIES[:3]]
    out += [f"## {label('quick', limit=limit_text(CFG.quick_minutes))} — {len(fast)}", "",
            label("quick_note", n=len(fast), cmd=cmd), ""]
    out += ([line(x) for x in urgent] or ["—"]) + [""]

    nightly = sorted((x for x in live if night(x)), key=Task.sort_key)
    places = label("night_where", places=", ".join(CFG.night_where)) if CFG.night_where else ""
    out += [f"## {label('night')} — {len(nightly)}", "",
            label("night_note", where=places, cmd=cmd), "",
            ", ".join(f"{x.link()} {x['effort']}" for x in nightly) or "—", ""]
    files = {CFG.index: "\n".join(out).rstrip() + "\n"}

    who = ", ".join(f"{value.get('mark', name)} — {value.get('title', name)}"
                    for name, value in CFG.executors.items())
    columns = ["ID", "P", label("col_who"), label("col_auto")]
    columns += [label("col_where")] if CFG.places else []
    columns += [label("col_effort"), label("col_task")]
    for area, chosen in by_area.items():
        rows = [f"# {areas[area][1]} — {len(chosen)}", "", label("area_see", cmd=cmd), ""]
        if area in CFG.frozen:
            rows += [label("frozen_area", why=CFG.frozen[area]), ""]
        rows += [label("legend", who=who), "",
                 "| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
        for x in sorted(chosen, key=Task.sort_key):
            title = x["title"].replace("|", "/")
            if x["due"]:
                title += f" ({label('due', date=x['due'])})"
            if x["tags"]:
                title += f" `{' '.join(x['tags'])}`"
            if waits_for(x):
                title += f" *({label('after', ids=', '.join(waits_for(x)))})*"
            if x["taken"]:
                title += f" *({label('taken', who=x['taken'])})*"
            cells = [x.link(), x["priority"],
                     CFG.executors.get(x["executor"], {}).get("mark", "?"),
                     AUTO_MARK.get(x["autonomous"], "?")]
            cells += [x["where"]] if CFG.places else []
            cells += [x["effort"], title]
            rows.append("| " + " | ".join(cells) + " |")
        files[area_file(area)] = "\n".join(rows).rstrip() + "\n"
    return files


def write_index(tasks=None):
    if tasks is None:
        tasks, _ = load_tasks()
    for path, text in build_index(tasks).items():
        write_text(path, text)


# --- commands --------------------------------------------------------------------------------

def cmd_index(_):
    tasks, problems = load_tasks()
    for problem in problems:
        print(problem)
    write_index(tasks)
    print(f"{rel(CFG.index)}: {len(tasks)} tasks")
    return 1 if problems else 0


def cmd_check(_):
    tasks, problems = load_tasks()
    problems = list(CFG.problems) + problems
    seen = {}
    closed = {}
    for task_id, title in closed_entries():
        closed.setdefault(task_id, set()).add(title)
    known = {x.id for x in tasks} | set(closed) | ledger_ids()
    for x in tasks:
        where = rel(x.path)
        for key in REQUIRED:
            if not x[key]:
                problems.append(f"{where}: no {key}")
        prefix = CFG.areas[x.area][0]
        if not re.fullmatch(re.escape(prefix) + r"-\d{3,}", x.id):
            problems.append(f"{where}: id {x.id!r} does not fit area {x.area}")
        if os.path.basename(x.path) != f"{x.id}.md":
            problems.append(f"{where}: file name differs from id {x.id}")
        if x.id in seen:
            problems.append(f"{where}: id {x.id} repeats {seen[x.id]}")
        seen[x.id] = where
        if x.id in closed:
            problems.append(f"{where}: id {x.id} is already closed in the ledger — another "
                            f"session took the number; run reid {x.id}")
        if x["priority"] and x["priority"] not in PRIORITIES:
            problems.append(f"{where}: priority {x['priority']!r}")
        if x["executor"] and x["executor"] not in CFG.executors:
            problems.append(f"{where}: executor {x['executor']!r}")
        if x["autonomous"] and x["autonomous"] not in AUTONOMOUS:
            problems.append(f"{where}: autonomous {x['autonomous']!r}")
        if x["where"] and x["where"] not in CFG.where:
            problems.append(f"{where}: where {x['where']!r}")
        if x["effort"] and x.minutes is None:
            problems.append(f"{where}: effort {x['effort']!r} is not like 15m, 2h, 1-2d")
        for key in ("due", "created"):
            if x[key] and not DATE.match(x[key]):
                problems.append(f"{where}: {key} {x[key]!r} is not YYYY-MM-DD")
        for tag in x["tags"]:
            if tag not in CFG.tags:
                problems.append(f"{where}: tag {tag!r}")
        if x["block"] and x["block"] not in CFG.blocks:
            problems.append(f"{where}: block {x['block']!r} is not in blocks of {CONFIG_NAME}")
        for key in ("related", "after"):
            for other in x[key]:
                if other not in known:
                    problems.append(f"{where}: {key} {other} is neither open nor closed")
        if x.id in x["after"]:
            problems.append(f"{where}: comes after itself")
        if x.body.strip() in (template_body(False).strip(), template_body(True).strip()):
            problems.append(f"{where}: the body is still the empty template")
        for other in sorted(set(CFG.id.findall(x.body))):
            if other not in known:
                problems.append(f"{where}: mentions {other}, which is neither open nor closed")
        if x.role == "owner" and x["autonomous"] == "yes":
            problems.append(f"{where}: executor {x['executor']} cannot be autonomous yes")
    # Closed lines cannot be told fresh from old, and an old race is history: a warning only.
    warnings = [f"warning: {rel(CFG.done)}: {task_id} closes {len(titles)} different tasks — two "
                "sessions took the number; if one of the lines is yours and new, renumber it"
                for task_id, titles in sorted(closed.items()) if len(titles) > 1]
    for name in sorted(os.listdir(CFG.folder)):
        folder = os.path.join(CFG.folder, name)
        if (os.path.isdir(folder) and name not in CFG.areas and name != "done"
                and any(n.endswith(".md") for n in os.listdir(folder))):
            problems.append(f"{rel(folder)}: not an area of {CONFIG_NAME}, its tasks are not seen")
    for path, fresh in build_index(tasks).items():
        current = read_text(path) if os.path.exists(path) else ""
        if fresh != current:
            problems.append(f"{rel(path)}: stale, run {CFG.command} index")
    for problem in problems + warnings:
        print(problem)
    print(f"{len(tasks)} tasks, {len(problems)} problems" +
          (f", {len(warnings)} warnings" if warnings else ""))
    return 1 if problems else 0


def cmd_list(args):
    tasks, _ = load_tasks()
    if args.area:
        tasks = [x for x in tasks if x.area == args.area]
    if args.tag:
        tasks = [x for x in tasks if args.tag in x["tags"]]
    if args.owner or args.quick or args.night:
        tasks = [x for x in tasks if x.area not in CFG.frozen]
    if args.owner:
        tasks = [x for x in tasks if needs_owner(x) or checked_by_owner(x)]
    if args.quick:
        tasks = [x for x in tasks if quick(x)]
    if args.night:
        tasks = [x for x in tasks if night(x)]
    wide = max([len(x.id) for x in tasks] + [1])
    who = max([len(name) for name in CFG.executors] + [1])
    place = max(len(name) for name in CFG.where)
    for x in sorted(tasks, key=Task.sort_key):
        notes = f"  [{label('after', ids=', '.join(waits_for(x)))}]" if waits_for(x) else ""
        notes += f"  [{label('taken', who=x['taken'])}]" if x["taken"] else ""
        print(f"{x.id:{wide}} {x['priority']:2} {x['executor']:{who}} {x['autonomous']:6} "
              f"{x['where']:{place}} {x['effort']:>6}  {x['title']}{notes}")
    print(f"{len(tasks)} tasks")
    return 0


def report_key(task, key):
    """(position, heading) of a task under one way of grouping."""
    if key == "area":
        return list(CFG.areas).index(task.area), CFG.areas[task.area][1]
    if key == "block":
        names = list(CFG.blocks)
        block = task["block"]
        if block in names:
            return names.index(block), CFG.blocks[block]
        return len(names), block or label("no_block")
    if key == "who":
        return WHO.index(task.who), label("who_" + task.who)
    return PRIORITIES.index(task["priority"]) if task["priority"] in PRIORITIES else 9, \
        task["priority"] or "?"


def report_order(task, keys):
    """Sort key of a row inside its table."""
    order = []
    for key in keys:
        if key == "effort":
            order.append(task.minutes if task.minutes is not None else 10**9)
        elif key == "id":
            order.append(task.sort_key()[2:])
        else:
            order.append(report_key(task, key)[0])
    return tuple(order) + (task.sort_key(),)


def build_report(tasks, groups, sorts, chosen=""):
    """Markdown: a summary of the groups by who and cost, then a table for each group."""
    kinds = [kind for kind in WHO if kind != "other" or any(x.who == "other" for x in tasks)]
    out = [f"# {label('report_title', n=len(tasks), cost=cost(tasks))}", "",
           label("report_legend", **{kind: label("who_" + kind) for kind in WHO})]
    out += [label("report_filter", what=chosen)] if chosen else []
    out.append("")
    if not tasks:
        return "\n".join(out + [label("report_none")]) + "\n"
    sections = {}
    for x in tasks:
        path = tuple(report_key(x, key) for key in groups)
        sections.setdefault(path, []).append(x)
    ordered = sorted(sections.items(), key=lambda item: [part[0] for part in item[0]])

    def counts(rows):
        return [str(sum(1 for x in rows if x.who == kind) or "") for kind in kinds]

    if groups:
        head = [label("col_group"), label("col_tasks")]
        head += [label("who_" + kind) for kind in kinds] + [label("col_cost")]
        out += [f"## {label('report_summary')}", "", "| " + " | ".join(head) + " |",
                "|---|" + "---:|" * (len(head) - 1)]
        for path, rows in ordered:
            name = " · ".join(part[1] for part in path)
            out.append("| " + " | ".join([name, str(len(rows))] + counts(rows) + [cost(rows)])
                       + " |")
        out += ["| " + " | ".join([f"**{label('report_total')}**", str(len(tasks))]
                                  + counts(tasks) + [cost(tasks)]) + " |", ""]

    columns = [label("col_who"), "P", "ID", label("col_effort")]
    columns += [label("col_where")] if CFG.places else []
    columns.append(label("col_task"))
    shown = ()
    for path, rows in ordered:
        for depth, part in enumerate(path):
            if shown[:depth + 1] != path[:depth + 1]:
                last = depth == len(path) - 1
                chunk = rows if last else [x for other, more in ordered
                                           if other[:depth + 1] == path[:depth + 1] for x in more]
                out += [f"{'#' * (depth + 2)} {part[1]} — {len(chunk)}, {cost(chunk)}", ""]
        shown = path
        out += ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
        for x in sorted(rows, key=lambda x: report_order(x, sorts)):
            who = label("who_" + x.who) if x.who != "other" else \
                CFG.executors.get(x["executor"], {}).get("title", x["executor"])
            who += "*" if x.who == "together" and x["autonomous"] == "no" else ""
            title = x["title"].replace("|", "/")
            if x["due"]:
                title += f" ({label('due', date=x['due'])})"
            if waits_for(x):
                title += f" *({label('after', ids=', '.join(waits_for(x)))})*"
            if x["taken"]:
                title += f" *({label('taken', who=x['taken'])})*"
            cells = [who, x["priority"], x.id, x["effort"] or "?"]
            cells += [x["where"]] if CFG.places else []
            out.append("| " + " | ".join(cells + [title]) + " |")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def cmd_report(args):
    tasks, _ = load_tasks()
    areas, prios = parse_list(args.area or ""), parse_list(args.p or "")
    kinds, blocks = parse_list(args.who or ""), parse_list(args.block or "")
    groups = parse_list(args.group) if args.group is not None else \
        [key for key in ("area", "block") if key == "area" or CFG.blocks]
    sorts = parse_list(args.sort or "who,priority,effort")
    for values, allowed, name in ((areas, CFG.areas, "--area"), (prios, PRIORITIES, "--p"),
                                  (kinds, WHO, "--who"), (groups, REPORT_GROUPS, "--group"),
                                  (sorts, REPORT_SORTS, "--sort")):
        for value in values:
            if value not in allowed:
                return refuse(f"{name} is of {', '.join(allowed)}")
    if len(areas) == 1 and args.group is None:
        groups = [key for key in groups if key != "area"]
    tasks = [x for x in tasks if (x.area in areas if areas else x.area not in CFG.frozen)]
    if prios:
        tasks = [x for x in tasks if x["priority"] in prios]
    if kinds:
        tasks = [x for x in tasks if x.who in kinds]
    if blocks:
        tasks = [x for x in tasks if (x["block"] or "-") in blocks]
    if args.tag:
        tasks = [x for x in tasks if args.tag in x["tags"]]
    chosen = [", ".join(CFG.areas[a][1] for a in areas), ", ".join(prios),
              ", ".join(label("who_" + kind) for kind in kinds),
              ", ".join(CFG.blocks.get(b, label("no_block") if b == "-" else b) for b in blocks),
              f"`{args.tag}`" if args.tag else ""]
    print(build_report(tasks, groups, sorts, " · ".join(part for part in chosen if part)), end="")
    return 0


def next_id(area):
    prefix = CFG.areas[area][0]
    used = {x.id for x in load_tasks()[0]} | ledger_ids() | upstream_ids()
    numbers = [int(i.rpartition("-")[2]) for i in used if i.rpartition("-")[0] == prefix]
    return f"{prefix}-{max(numbers + [0]) + 1:03d}"


def template_body(owner):
    return label("body", owner=label("body_owner") if owner else "")


def create(area, title, **fields):
    task_id = next_id(area)
    folder = os.path.join(CFG.folder, area)
    os.makedirs(folder, exist_ok=True)
    agents = [name for name, value in CFG.executors.items() if value.get("role") == "agent"]
    values = {"id": task_id, "title": title, "priority": "P2",
              "executor": (agents or list(CFG.executors))[0], "autonomous": "", "effort": "",
              "where": "any" if "any" in CFG.where else CFG.where[0], "due": "", "tags": [],
              "block": "", "related": [], "created": today(), "from": ""}
    body = fields.pop("body", None)
    values.update({k: v for k, v in fields.items() if v not in (None, "", [])})
    agent = CFG.executors.get(values["executor"], {}).get("role") == "agent"
    # Only an agent works alone; a task for a person waits for that person.
    values["autonomous"] = values["autonomous"] or ("yes" if agent else "no")
    if body is None:
        body = template_body(not agent or values["autonomous"] != "yes")
    task = Task(os.path.join(folder, f"{task_id}.md"), values, body)
    write_task(task)
    return task


def refuse(text):
    print(text)
    return 1


def cmd_new(args):
    if args.area not in CFG.areas:
        return refuse(f"area is one of {', '.join(CFG.areas)}")
    if args.who and args.who not in CFG.executors:
        return refuse(f"--who is one of {', '.join(CFG.executors)}")
    if args.where and args.where not in CFG.where:
        return refuse(f"--where is one of {', '.join(CFG.where)}")
    if args.block and args.block not in CFG.blocks:
        return refuse("--block is one of " + (", ".join(CFG.blocks) or f"none: {CONFIG_NAME} "
                                                "names no blocks"))
    tasks, _ = load_tasks()
    related, after = parse_list(args.related or ""), parse_list(args.after or "")
    known = CFG.open_ids | ledger_ids()
    for other in related + after:
        if other not in known:
            return refuse(f"{other} is neither open nor closed")
    task = create(args.area, args.title.strip(), priority=args.p, executor=args.who,
                  autonomous=args.auto, effort=args.effort, where=args.where, due=args.due,
                  tags=parse_list(args.tags or ""), related=related, after=after,
                  block=args.block, **{"from": args.origin})
    for other in tasks:  # a link reads from both ends
        if other.id in related and task.id not in other["related"]:
            other.fields["related"] = other["related"] + [task.id]
            write_task(other)
    write_index()
    if args.area in CFG.frozen:
        print(f"note: area {args.area} is frozen")
    print(rel(task.path))
    return 0


def find_open(task_id):
    for x in load_tasks()[0]:
        if x.id == task_id:
            return x
    return None


def closed_title(task_id):
    for found, title in closed_entries():
        if found == task_id:
            return title
    return None


def cmd_port(args):
    if args.area not in CFG.areas:
        return refuse(f"area is one of {', '.join(CFG.areas)}")
    source = find_open(args.id)
    title = source["title"] if source else closed_title(args.id)
    if title is None:
        return refuse(f"{args.id} is neither open nor closed")
    if source and source.area == args.area:
        return refuse(f"{args.id} is already in {args.area}")
    body = label("port_body", area=CFG.areas[args.area][1], id=args.id, title=title)
    task = create(args.area, label("port_title", title=title)[:90], tags=["port"],
                  related=[args.id], effort=source["effort"] if source else "",
                  priority=source["priority"] if source else "", body=body,
                  block=source["block"] if source else "",
                  **{"from": label("port_from", id=args.id)})
    if source:
        source.fields["related"] = sorted(set(source["related"]) | {task.id})
        write_task(source)
    write_index()
    print(rel(task.path))
    return 0


def cmd_idea(args):
    exists = os.path.exists(CFG.inbox)
    with open(CFG.inbox, "a", encoding="utf-8", newline="\n") as handle:
        if not exists:
            handle.write(f"# {label('inbox_title')}\n\n{label('inbox_intro')}\n\n")
        handle.write(f"- {today()} · {' '.join(args.text.split())}\n")
    write_index()
    print(rel(CFG.inbox))
    return 0


def cmd_done(args):
    task = find_open(args.id)
    if task is None:
        return refuse(f"{args.id} is not open")
    stamp = today()
    os.makedirs(CFG.done, exist_ok=True)
    ledger = os.path.join(CFG.done, stamp[:7] + ".md")
    exists = os.path.exists(ledger)
    with open(ledger, "a", encoding="utf-8", newline="\n") as handle:
        if not exists:
            handle.write(f"# {label('ledger_title', month=stamp[:7])}\n\n"
                         f"{label('ledger_intro')}\n\n")
        comment = " " + " ".join(args.comment.split()) if args.comment.strip() else ""
        handle.write(f"- {stamp} · **{task.id}** {task['title']} — "
                     f"{label('result_' + args.result)}.{comment}\n")
    os.remove(task.path)
    tasks, _ = load_tasks()
    write_index(tasks)
    print(f"{task.id} -> {rel(ledger)}")
    freed = [x.id for x in tasks if task.id in x["after"] and not waits_for(x)]
    if freed:
        print(f"no longer waiting: {', '.join(freed)}")
    return 0


def cmd_take(args):
    task = find_open(args.id)
    if task is None:
        return refuse(f"{args.id} is not open")
    if task["taken"] and not args.force:
        return refuse(f"{args.id} is taken: {task['taken']}")
    who = " ".join((args.who or socket.gethostname()).split())
    task.fields["taken"] = f"{who}, {datetime.datetime.now():%Y-%m-%d %H:%M}"
    write_task(task)
    write_index()
    print(f"{task.id}: {task['taken']}")
    return 0


def cmd_release(args):
    task = find_open(args.id)
    if task is None:
        return refuse(f"{args.id} is not open")
    task.fields.pop("taken", None)
    write_task(task)
    write_index()
    print(f"{task.id}: released")
    return 0


def give_new_id(task, tasks, area, everywhere):
    """Move an open task to the next free ID of an area and follow the references to it.

    `everywhere` is for a task that changes its area: every mention of the old ID meant this
    task. After two sessions took one number the old ID also names the other session's task, so
    only the links this task made itself are followed, and the rest are listed for a human eye.
    """
    old, new = task.id, next_id(area)
    pattern = re.compile(r"\b" + re.escape(old) + r"\b")
    if not everywhere:
        for other in tasks:
            if other is not task and other.id in task["related"] and old in other["related"]:
                write_text(other.path, pattern.sub(new, read_text(other.path)))
    os.remove(task.path)
    task.fields["id"] = new
    os.makedirs(os.path.join(CFG.folder, area), exist_ok=True)
    task.path = os.path.join(CFG.folder, area, f"{new}.md")
    write_task(task)
    write_index()
    print(f"{old} -> {new}")
    for folder, _, names in os.walk(CFG.folder):
        for name in sorted(names):
            path = os.path.join(folder, name)
            if not name.endswith(".md") or path == os.path.join(CFG.folder, "README.md"):
                continue  # the README names IDs only as samples
            text = read_text(path)
            if not pattern.search(text):
                continue
            if everywhere:
                write_text(path, pattern.sub(new, text))
            else:
                print(f"  {rel(path)} still names {old}: change it by hand if it means this task")
    if everywhere:
        write_index()
    return 0


def cmd_reid(args):
    tasks, _ = load_tasks()
    task = next((x for x in tasks if x.id == args.id), None)
    if task is None:
        return refuse(f"{args.id} is not open")
    return give_new_id(task, tasks, task.area, everywhere=False)


def cmd_move(args):
    if args.area not in CFG.areas:
        return refuse(f"area is one of {', '.join(CFG.areas)}")
    tasks, _ = load_tasks()
    task = next((x for x in tasks if x.id == args.id), None)
    if task is None:
        return refuse(f"{args.id} is not open")
    if task.area == args.area:
        return refuse(f"{args.id} is already in {args.area}")
    return give_new_id(task, tasks, args.area, everywhere=True)


def cmd_renumber(args):
    tasks, problems = load_tasks()
    if problems:
        for problem in problems:
            print(problem)
        return 1
    if closed_entries():
        return refuse("the ledger already has closed tasks: dense numbers would repeat theirs")
    mapping = {}
    for area, (prefix, _) in CFG.areas.items():
        chosen = sorted((x for x in tasks if x.area == area),
                        key=lambda x: (x["priority"] or "P9", x.sort_key()[2:]))
        for number, x in enumerate(chosen, 1):
            mapping[x.id] = f"{prefix}-{number:03d}"
    if not mapping:
        return 0
    pattern = re.compile(r"\b(?:" + "|".join(
        re.escape(k) for k in sorted(mapping, key=len, reverse=True)) + r")\b")
    files = [os.path.abspath(path) for path in args.also or []]
    for folder, _, names in os.walk(CFG.folder):
        files += [os.path.join(folder, n) for n in names if n.endswith(".md")]
    for path in files:
        text = read_text(path)
        new = pattern.sub(lambda m: mapping[m.group(0)], text)
        if new != text:
            write_text(path, new)
    staged = []
    for x in tasks:
        temporary = x.path + ".renumber"
        os.replace(x.path, temporary)
        staged.append((temporary, os.path.join(os.path.dirname(x.path), mapping[x.id] + ".md")))
    for temporary, final in staged:
        os.replace(temporary, final)
    write_index()
    for old, new in sorted(mapping.items()):
        if old != new:
            print(f"{old} -> {new}")
    return 0


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dir", help="the backlog directory, when it is not backlog/ above")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("index").set_defaults(run=cmd_index)
    sub.add_parser("check").set_defaults(run=cmd_check)
    listing = sub.add_parser("list")
    listing.add_argument("--area")
    listing.add_argument("--tag")
    listing.add_argument("--owner", action="store_true")
    listing.add_argument("--quick", action="store_true")
    listing.add_argument("--night", action="store_true")
    listing.set_defaults(run=cmd_list)
    report = sub.add_parser("report", help="Markdown report: who, priority, block and cost")
    report.add_argument("--area", help="comma-separated areas; all but the frozen when left out")
    report.add_argument("--p", help="comma-separated priorities: P1,P2")
    report.add_argument("--who", help="comma-separated: " + ", ".join(WHO))
    report.add_argument("--block", help="comma-separated blocks; - for tasks without one")
    report.add_argument("--tag")
    report.add_argument("--group", help="headings, comma-separated: " + ", ".join(REPORT_GROUPS)
                        + "; area,block when left out; empty for one table")
    report.add_argument("--sort", help="rows, comma-separated: " + ", ".join(REPORT_SORTS)
                        + "; who,priority,effort when left out")
    report.set_defaults(run=cmd_report)
    new = sub.add_parser("new")
    new.add_argument("area")
    new.add_argument("title")
    new.add_argument("--p", choices=PRIORITIES, help="priority, P2 when left out")
    new.add_argument("--who", help="an executor of config.json; the first agent when left out")
    new.add_argument("--auto", choices=AUTONOMOUS,
                     help="yes for an agent and no for a person when left out; better said")
    new.add_argument("--effort", help="15m, 2h, 1d, 2-3d")
    new.add_argument("--where", help="a place of config.json; any when left out")
    new.add_argument("--due", help="YYYY-MM-DD")
    new.add_argument("--tags", help="comma-separated: check,bug")
    new.add_argument("--related", help="comma-separated IDs; open ones are linked back")
    new.add_argument("--after", help="comma-separated IDs that have to be closed first")
    new.add_argument("--block", help="a functional block of config.json")
    new.add_argument("--from", dest="origin", help="where the task came from")
    new.set_defaults(run=cmd_new)
    port = sub.add_parser("port")
    port.add_argument("id")
    port.add_argument("area")
    port.set_defaults(run=cmd_port)
    idea = sub.add_parser("idea")
    idea.add_argument("text")
    idea.set_defaults(run=cmd_idea)
    done = sub.add_parser("done")
    done.add_argument("id")
    done.add_argument("result", choices=RESULTS)
    done.add_argument("comment", nargs="?", default="")
    done.set_defaults(run=cmd_done)
    take = sub.add_parser("take")
    take.add_argument("id")
    take.add_argument("who", nargs="?", default="")
    take.add_argument("--force", action="store_true")
    take.set_defaults(run=cmd_take)
    release = sub.add_parser("release")
    release.add_argument("id")
    release.set_defaults(run=cmd_release)
    reid = sub.add_parser("reid")
    reid.add_argument("id")
    reid.set_defaults(run=cmd_reid)
    move = sub.add_parser("move")
    move.add_argument("id")
    move.add_argument("area")
    move.set_defaults(run=cmd_move)
    renumber = sub.add_parser("renumber")
    renumber.add_argument("--also", action="append", metavar="FILE",
                          help="one more file whose task IDs follow the new numbers")
    renumber.set_defaults(run=cmd_renumber)
    args = parser.parse_args()
    global CFG
    CFG = Config(find_backlog(args.dir))
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
