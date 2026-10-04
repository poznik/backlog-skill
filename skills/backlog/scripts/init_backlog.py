#!/usr/bin/env python3
"""Install the backlog into a project, or bring its tool up to date.

    python init_backlog.py --root <project> --lang ru \\
        --area core:CORE:"Ядро" --area web:WEB:"Сайт" [--where pc,mac] [--tool tools/backlog.py]
    python init_backlog.py --root <project> --upgrade

Installing writes ``backlog/config.json``, ``README.md``, ``inbox.md`` and ``done/``, copies
``backlog.py`` to the tool path, builds the index and prints the rule to put into the project's
``CLAUDE.md`` or ``AGENTS.md``. Nothing outside ``backlog/`` and the tool path is touched.

    --area dir:PREFIX:Title      an area: its folder, the prefix of its task IDs, its heading;
                                 repeat per area, the default is one area main:TASK
    --executor key:Title:M:role  one more executor: key in task files, heading, one-letter mark
                                 of its own, role agent | owner | human; the defaults are claude
                                 and owner
    --where pc,mac               the places a task can be bound to, when there is more than one
    --night-where pc             the places the overnight list takes tasks from
    --tag name:description       one more tag besides check, decision, port, bug, debt, idea,
                                 research
    --python python3             how the project calls Python in its documents

Python 3.8+, standard library only.
"""

import argparse
import datetime
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True  # the tool is imported below; leave no cache in the skill

HERE =os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "backlog.py")
ASSETS = os.path.join(os.path.dirname(HERE), "assets")
ROLES = ("agent", "owner", "human")
RESERVED = ("done", "index", "readme", "inbox", "config")

DEFAULTS = {
    "en": {
        "area": ("main", "TASK", "Tasks"),
        "executors": {
            "claude": {"title": "Claude", "mark": "C", "role": "agent"},
            "owner": {"title": "owner", "mark": "O", "role": "owner"},
        },
        "tags": {
            "check": "verify by hand or by eye",
            "decision": "the owner's decision",
            "port": "work done in one area, brought to another",
            "bug": "a defect",
            "debt": "debt and cleanup",
            "idea": "a wish without a plan",
            "research": "needs finding out before doing",
        },
    },
    "ru": {
        "area": ("main", "TASK", "Задачи"),
        "executors": {
            "claude": {"title": "Claude", "mark": "C", "role": "agent"},
            "owner": {"title": "владелец", "mark": "В", "role": "owner"},
        },
        "tags": {
            "check": "проверить руками или глазами",
            "decision": "решение владельца",
            "port": "перенос сделанного из другой области",
            "bug": "дефект",
            "debt": "долг и чистка",
            "idea": "хотелка без плана",
            "research": "сначала выяснить, потом делать",
        },
    },
}


def fail(text):
    raise SystemExit(text)


def parse_area(spec):
    parts = [part.strip() for part in spec.split(":", 2)]
    name = parts[0]
    prefix = parts[1] if len(parts) > 1 and parts[1] else re.sub(r"[^A-Z0-9]", "", name.upper())[:4]
    title = parts[2] if len(parts) > 2 and parts[2] else name
    if not re.match(r"^[a-z0-9][a-z0-9_-]*$", name) or name in RESERVED:
        fail(f"--area {spec}: the folder is lower-case letters, digits, - and _, and not one of "
             f"{', '.join(RESERVED)}")
    if not re.match(r"^[A-Z][A-Z0-9]{1,7}$", prefix):
        fail(f"--area {spec}: the prefix is 2-8 capital letters or digits, like WEB")
    return name, prefix, title


def parse_executor(spec):
    parts = [part.strip() for part in spec.split(":")]
    if len(parts) != 4 or parts[3] not in ROLES:
        fail(f"--executor {spec}: key:Title:Mark:role, role is one of {', '.join(ROLES)}")
    return parts[0], {"title": parts[1], "mark": parts[2], "role": parts[3]}


def version_of(path):
    with open(path, encoding="utf-8") as handle:
        match = re.search(r'^__version__ = "([^"]+)"', handle.read(), re.M)
    return match.group(1) if match else "?"


def run_tool(tool, *args):
    done = subprocess.run([sys.executable, tool] + list(args), capture_output=True,
                          encoding="utf-8", errors="replace")
    sys.stdout.write(done.stdout)
    sys.stderr.write(done.stderr)
    return done.returncode


def upgrade(root, backlog, tool_arg):
    config_path = os.path.join(backlog, "config.json")
    if not os.path.isfile(config_path):
        fail(f"{config_path}: no backlog here, install it first")
    with open(config_path, encoding="utf-8-sig") as handle:
        command = json.load(handle).get("command") or "python tools/backlog.py"
    tool = os.path.join(root, tool_arg or command.split()[-1])
    old = version_of(tool) if os.path.isfile(tool) else "none"
    shutil.copyfile(TOOL, tool)
    print(f"{os.path.relpath(tool, root).replace(os.sep, '/')}: {old} -> {version_of(tool)}")
    run_tool(tool, "index")
    return run_tool(tool, "check")


def fill(text, values):
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    left = re.findall(r"\{\{[A-Z_0-9]+\}\}", text)
    if left:
        fail(f"template placeholders left: {', '.join(sorted(set(left)))}")
    # The sample task keeps its notes in one column whatever the names put in were.
    return re.sub(r"^([a-z]+:(?: \S+)*) {2,}# ", lambda m: f"{m.group(1):<40}# ", text, flags=re.M)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", default=os.getcwd(), help="the project; backlog/ goes into it")
    parser.add_argument("--lang", default="en", help="en or ru: the language of generated files")
    parser.add_argument("--area", action="append", default=[], metavar="dir:PREFIX:Title")
    parser.add_argument("--executor", action="append", default=[], metavar="key:Title:M:role")
    parser.add_argument("--where", default="", metavar="pc,mac")
    parser.add_argument("--night-where", default="", metavar="pc")
    parser.add_argument("--tag", action="append", default=[], metavar="name:description")
    parser.add_argument("--tool", default="", help="where the tool goes, default tools/backlog.py")
    parser.add_argument("--python", default="python" if os.name == "nt" else "python3")
    parser.add_argument("--upgrade", action="store_true", help="only replace the tool by this one")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    backlog = os.path.join(root, "backlog")
    if args.upgrade:
        return upgrade(root, backlog, args.tool)
    if not os.path.isdir(root):
        fail(f"{root}: no such directory")
    if os.path.exists(os.path.join(backlog, "config.json")):
        fail(f"{backlog}: the backlog is already installed; --upgrade replaces the tool")
    if os.path.isdir(backlog) and os.listdir(backlog):
        fail(f"{backlog}: exists and is not empty — move what is there aside first")
    lang = args.lang if args.lang in DEFAULTS else "en"
    base = DEFAULTS[lang]

    areas = [parse_area(spec) for spec in args.area] or [base["area"]]
    if len({name for name, _, _ in areas}) < len(areas):
        fail("two areas share a folder")
    if len({prefix for _, prefix, _ in areas}) < len(areas):
        fail("two areas share a prefix")
    executors = dict(base["executors"])
    executors.update(parse_executor(spec) for spec in args.executor)
    marks = {}
    for key, value in executors.items():
        if value["mark"] in marks:
            fail(f"--executor {key}: the mark {value['mark']} is taken by {marks[value['mark']]}, "
                 "and the tables tell executors apart by it")
        marks[value["mark"]] = key
    places = [p.strip() for p in args.where.split(",") if p.strip() and p.strip() != "any"]
    where = places + ["any"]
    night_where = [p.strip() for p in args.night_where.split(",") if p.strip()]
    for place in night_where:
        if place not in where:
            fail(f"--night-where {place}: not among {', '.join(where)}")
    tags = dict(base["tags"])
    for spec in args.tag:
        name, _, about = spec.partition(":")
        tags[name.strip()] = about.strip()
    tool_rel = (args.tool or "tools/backlog.py").replace("\\", "/")
    command = f"{args.python} {tool_rel}"

    config = {
        "lang": args.lang,
        "command": command,
        "areas": {name: {"prefix": prefix, "title": title} for name, prefix, title in areas},
        "frozen": {},
        "executors": executors,
        "where": where,
        "night_where": night_where,
        "tags": tags,
        "quick_minutes": 60,
    }
    write(os.path.join(backlog, "config.json"),
          json.dumps(config, ensure_ascii=False, indent=2) + "\n")

    first, second = areas[0], areas[1 if len(areas) > 1 else 0]
    roles = {"agent": [], "owner": [], "human": []}
    for key, value in executors.items():
        roles[value["role"]].append(key)
    values = {
        "COMMAND": command,
        "DATE": datetime.date.today().isoformat(),
        "AREA_TABLES": ", ".join(f"[{name}.md]({name}.md)" for name, _, _ in areas),
        "AREA_DIRS": ", ".join(f"`{name}/`" for name, _, _ in areas),
        "AREAS": "\n".join(f"- `{name}` ({prefix}) — {title}" for name, prefix, title in areas),
        "ID_EXAMPLES": ", ".join(f"`{prefix}-001`" for _, prefix, _ in areas),
        "EXAMPLE_ID": f"{first[1]}-012",
        "EXAMPLE_AREA": first[0],
        "EXAMPLE_ID_2": f"{second[1]}-004",
        "EXAMPLE_AREA_2": second[0],
        "AGENT": (roles["agent"] or list(executors))[0],
        "OWNER": (roles["owner"] or list(executors))[0],
        "EXECUTORS": " · ".join(
            key if value["title"].lower() == key else f"{key} ({value['title']})"
            for key, value in executors.items()),
        "WHERE": " · ".join(where),
        "TAGS": "\n".join(f"- `{name}` — {about}" if about else f"- `{name}`"
                          for name, about in tags.items()),
    }
    for name in ("README", "rule"):
        if not os.path.isfile(os.path.join(ASSETS, f"{name}.{lang}.md")):
            fail(f"{ASSETS}: no {name}.{lang}.md")
    with open(os.path.join(ASSETS, f"README.{lang}.md"), encoding="utf-8") as handle:
        write(os.path.join(backlog, "README.md"), fill(handle.read(), values))
    write(os.path.join(backlog, "done", ".gitkeep"), "")

    tool = os.path.join(root, tool_rel)
    if os.path.exists(tool):
        fail(f"{tool}: exists — pass another --tool, or --upgrade to replace it")
    os.makedirs(os.path.dirname(tool), exist_ok=True)
    shutil.copyfile(TOOL, tool)
    # The inbox starts empty, under the heading the tool itself would give it.
    spec = importlib.util.spec_from_file_location("backlog_tool", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    table = dict(module.LABELS["en"])
    table.update(module.LABELS.get(args.lang, {}))
    write(os.path.join(backlog, "inbox.md"),
          f"# {table['inbox_title']}\n\n{table['inbox_intro']}\n\n")
    code = run_tool(tool, "index") or run_tool(tool, "check")

    print()
    print(f"installed: backlog/ with areas {', '.join(name for name, _, _ in areas)}; "
          f"{tool_rel} {version_of(tool)}")
    if args.lang not in DEFAULTS:
        print(f"lang {args.lang}: README.md and the rule are in English and the index uses English "
              "labels — translate README.md and add \"labels\" to config.json "
              "(references/config.md)")
    print("--- the rule for CLAUDE.md / AGENTS.md, in the project's own words if it has them ---")
    with open(os.path.join(ASSETS, f"rule.{lang}.md"), encoding="utf-8") as handle:
        print(fill(handle.read(), values).rstrip())
    return code


if __name__ == "__main__":
    sys.exit(main())
