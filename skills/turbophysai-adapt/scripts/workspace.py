#!/usr/bin/env python3
"""Manage a turbophysai-adapt workspace (stdlib only, Python 3.8+).

Subcommands:
  init            create a workspace with state.json and report drafts
  status          print stage, gate status, open items and consistency problems
  delivery-table  print the Group/OPT table for the delivery report (--write updates the draft)
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from pathlib import Path

SCHEMA = "turbophysai-adapt/state/v1"
SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_DIR / "templates"
STAGES = (
    "00-kickoff",
    "01-environment",
    "02-adaptation",
    "03-baseline",
    "04-optimize",
    "05-validation",
    "06-delivery",
    "07-retrospect",
)
GATE_STATUSES = {"open", "passed", "waived"}
OPT_STATUSES = {"proposed", "implementing", "validated", "delivered", "rejected"}
BOT_STATUSES = {"open", "addressed", "deferred"}
TABLE_BEGIN = "<!-- delivery-table:begin -->"
TABLE_END = "<!-- delivery-table:end -->"


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def _load_state(workspace: Path) -> dict:
    path = workspace / "state.json"
    if not path.is_file():
        raise SystemExit(f"error: {path} not found; run 'init' first")
    with path.open(encoding="utf-8") as stream:
        state = json.load(stream)
    if state.get("schema") != SCHEMA:
        raise SystemExit(f"error: {path} schema is {state.get('schema')!r}, expected {SCHEMA!r}")
    return state


def _render_template(name: str, model: str) -> str:
    text = (TEMPLATES / name).read_text(encoding="utf-8")
    return text.replace("{模型名称}", model).replace("｛模型名称｝", model)


def cmd_init(args: argparse.Namespace) -> int:
    model = args.model.strip()
    if not model:
        return _fail("--model must not be empty")
    workspace = Path(
        os.path.expanduser(args.workspace or f"~/turbophysai-adapt/{model}")
    ).resolve()
    if workspace.exists():
        return _fail(f"{workspace} already exists; use 'status' to resume")
    for sub in ("reports", "traces", "logs", "env", "notes"):
        (workspace / sub).mkdir(parents=True)
    state = {
        "schema": SCHEMA,
        "created": _dt.date.today().isoformat(),
        "model": {
            "name": model,
            "category": args.category or "",
            "task": "训练",
            "upstream": args.upstream or "",
            "baseline_commit": args.commit or "",
            "repo_path": args.repo_path or "",
        },
        "stage": STAGES[0],
        "gates": {stage: {"status": "open", "evidence": [], "note": ""} for stage in STAGES},
        "bottlenecks": [],
        "optimizations": [],
        "issues": [],
        "decisions": [],
    }
    (workspace / "state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for name in ("optimization-report.md", "delivery-report.md"):
        (workspace / "reports" / name).write_text(_render_template(name, model), encoding="utf-8")
    print(f"created {workspace}")
    print(f"next: read stages/{STAGES[0]}.md")
    return 0


def _problems(state: dict) -> list:
    problems = []
    if state.get("stage") not in STAGES:
        problems.append(f"unknown stage {state.get('stage')!r}")
    gates = state.get("gates", {})
    for stage in STAGES:
        gate = gates.get(stage)
        if gate is None:
            problems.append(f"gate {stage} missing")
            continue
        if gate.get("status") not in GATE_STATUSES:
            problems.append(f"gate {stage} has status {gate.get('status')!r}")
        if gate.get("status") == "waived" and not gate.get("note"):
            problems.append(f"gate {stage} is waived without a note")
    current = STAGES.index(state["stage"]) if state.get("stage") in STAGES else 0
    for stage in STAGES[:current]:
        if gates.get(stage, {}).get("status") == "open":
            problems.append(f"stage {state['stage']} reached while gate {stage} is still open")

    def unique(items, label):
        seen = set()
        for item in items:
            item_id = item.get("id")
            if not item_id:
                problems.append(f"{label} entry without id")
            elif item_id in seen:
                problems.append(f"duplicate {label} id {item_id}")
            seen.add(item_id)
        return seen

    bots = unique(state.get("bottlenecks", []), "bottleneck")
    opts = unique(state.get("optimizations", []), "optimization")
    unique(state.get("issues", []), "issue")
    for bot in state.get("bottlenecks", []):
        if bot.get("status") not in BOT_STATUSES:
            problems.append(f"{bot.get('id')} has status {bot.get('status')!r}")
        for ref in bot.get("opts", []):
            if ref not in opts:
                problems.append(f"{bot.get('id')} refers to unknown {ref}")
        if bot.get("status") == "deferred" and not bot.get("note"):
            problems.append(f"{bot.get('id')} is deferred without a note")
    for opt in state.get("optimizations", []):
        status = opt.get("status")
        if status not in OPT_STATUSES:
            problems.append(f"{opt.get('id')} has status {status!r}")
        for ref in opt.get("bots", []):
            if ref not in bots:
                problems.append(f"{opt.get('id')} refers to unknown {ref}")
        if status in {"validated", "delivered"}:
            if not opt.get("groups"):
                problems.append(f"{opt.get('id')} is {status} but lists no groups")
            if opt.get("accuracy") not in {"unchanged", "verified", "accuracy_only"}:
                problems.append(f"{opt.get('id')} is {status} without an accuracy conclusion")
        if status == "delivered" and current >= STAGES.index("07-retrospect") and not opt.get("reuse"):
            problems.append(f"{opt.get('id')} has no reuse conclusion")
    return problems


def cmd_status(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    state = _load_state(workspace)
    model = state["model"]
    print(f"model: {model.get('name')}  baseline: {model.get('baseline_commit') or '-'}")
    print(f"stage: {state['stage']}  (stages/{state['stage']}.md)")
    print("gates:")
    for stage in STAGES:
        gate = state["gates"].get(stage, {})
        marker = "->" if stage == state["stage"] else "  "
        note = f"  ({gate.get('note')})" if gate.get("note") else ""
        print(f"  {marker} {stage:<15} {gate.get('status', '?')}{note}")
    open_bots = [b for b in state.get("bottlenecks", []) if b.get("status") == "open"]
    active = [o for o in state.get("optimizations", []) if o.get("status") in {"proposed", "implementing"}]
    open_issues = [i for i in state.get("issues", []) if i.get("status") not in {"done", "closed", "完成"}]
    if open_bots:
        print("open bottlenecks:")
        for bot in open_bots:
            print(f"  {bot['id']}: {bot.get('summary', '')}")
    if active:
        print("optimizations in progress:")
        for opt in active:
            print(f"  {opt['id']} [{opt['status']}]: {opt.get('name', '')}")
    if open_issues:
        print("open issues:")
        for issue in open_issues:
            print(f"  {issue['id']}: {issue.get('summary', '')}")
    problems = _problems(state)
    if problems:
        print("problems:")
        for problem in problems:
            print(f"  - {problem}")
        return 2
    return 0


def _delivery_table(state: dict) -> str:
    rows = {}
    for opt in state.get("optimizations", []):
        if opt.get("status") not in {"validated", "delivered"}:
            continue
        for group_id in opt.get("groups", []):
            rows.setdefault(group_id, []).append(opt["id"])
    lines = [
        "| Group ID | 具体替换（有多个时注明） | 对应优化项 | 生效证据 |",
        "|---|---|---|---|",
    ]
    for group_id in sorted(rows):
        lines.append(f"| `{group_id}` | {{填写}} | {', '.join(rows[group_id])} | {{填写}} |")
    if len(lines) == 2:
        lines.append("| | | | |")
    return "\n".join(lines)


def cmd_delivery_table(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    state = _load_state(workspace)
    table = _delivery_table(state)
    if not args.write:
        print(table)
        return 0
    report = workspace / "reports" / "delivery-report.md"
    text = report.read_text(encoding="utf-8")
    begin, end = text.find(TABLE_BEGIN), text.find(TABLE_END)
    if begin < 0 or end < begin:
        return _fail(f"{report} has no {TABLE_BEGIN} / {TABLE_END} markers")
    updated = text[: begin + len(TABLE_BEGIN)] + "\n" + table + "\n" + text[end:]
    report.write_text(updated, encoding="utf-8")
    print(f"updated {report}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="create a workspace")
    init.add_argument("--model", required=True)
    init.add_argument("--workspace", help="default: ~/turbophysai-adapt/<model>")
    init.add_argument("--category")
    init.add_argument("--upstream", help="upstream git URL")
    init.add_argument("--commit", help="baseline commit")
    init.add_argument("--repo-path", help="local model repository path")
    init.set_defaults(func=cmd_init)

    status = commands.add_parser("status", help="show progress and consistency problems")
    status.add_argument("workspace")
    status.set_defaults(func=cmd_status)

    table = commands.add_parser("delivery-table", help="Group/OPT table for the delivery report")
    table.add_argument("workspace")
    table.add_argument("--write", action="store_true", help="update reports/delivery-report.md in place")
    table.set_defaults(func=cmd_delivery_table)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
