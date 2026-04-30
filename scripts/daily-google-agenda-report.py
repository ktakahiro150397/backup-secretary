#!/opt/hermes/.venv/bin/python
"""Daily Google Calendar + Tasks agenda report for Hermes cron."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/opt/data"))
PYTHON = "/opt/hermes/.venv/bin/python"
GAPI = HERMES_HOME / "skills/productivity/google-workspace/scripts/google_api.py"


def run_json(args: list[str]) -> object:
    proc = subprocess.run(
        [PYTHON, str(GAPI), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"google_api failed: {' '.join(args)}\nSTDERR:\n{proc.stderr}\nSTDOUT:\n{proc.stdout}")
    try:
        return json.loads(proc.stdout or "null")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"google_api returned non-JSON for {' '.join(args)}: {e}\n{proc.stdout[:1000]}") from e


def parse_event_dt(value: str) -> tuple[datetime | None, bool]:
    if not value:
        return None, False
    if "T" not in value:
        return datetime.combine(date.fromisoformat(value[:10]), time.min, tzinfo=JST), True
    v = value.replace("Z", "+00:00")
    return datetime.fromisoformat(v).astimezone(JST), False


def parse_task_due(value: str) -> date | None:
    if not value:
        return None
    # Google Tasks API exposes due dates as midnight UTC; treat the YYYY-MM-DD part as date-only.
    return date.fromisoformat(value[:10])


def day_label(d: date, today: date) -> str:
    diff = (d - today).days
    names = ["月", "火", "水", "木", "金", "土", "日"]
    base = f"{d.month}/{d.day}({names[d.weekday()]})"
    if diff == 0:
        return f"今日 {base}"
    if diff == 1:
        return f"明日 {base}"
    if diff == 2:
        return f"明後日 {base}"
    if diff == 3:
        return f"3日後 {base}"
    if diff < 0:
        return f"期限切れ {base}"
    return base


def fmt_event(ev: dict) -> tuple[date, str]:
    start, all_day = parse_event_dt(ev.get("start", ""))
    end, _ = parse_event_dt(ev.get("end", ""))
    title = ev.get("summary") or "(無題)"
    cal = ev.get("calendar") or "calendar"
    loc = ev.get("location") or ""
    if start is None:
        sort_day = date.today()
        when = "時刻不明"
    elif all_day:
        sort_day = start.date()
        when = "終日"
    else:
        sort_day = start.date()
        if end and end.date() == start.date():
            when = f"{start:%H:%M}-{end:%H:%M}"
        else:
            when = f"{start:%H:%M}〜"
    extra = f" @ {loc}" if loc else ""
    return sort_day, f"- {when} {title} [{cal}]{extra}"


def fmt_task(task: dict, list_title: str, today: date) -> tuple[date, str] | None:
    if task.get("status") == "completed":
        return None
    due = parse_task_due(task.get("due", ""))
    if due is None:
        return None
    title = task.get("title") or "(無題タスク)"
    overdue = " ⚠️期限切れ" if due < today else ""
    return due, f"- {title} [{list_title}]{overdue}"


def main() -> int:
    now = datetime.now(JST)
    today = now.date()
    last_day = today + timedelta(days=3)
    start = datetime.combine(today, time.min, JST).isoformat()
    end = datetime.combine(last_day + timedelta(days=1), time.min, JST).isoformat()

    events = run_json(["calendar", "list", "--calendar", "all", "--start", start, "--end", end])
    if not isinstance(events, list):
        events = []

    events_by_day: dict[date, list[str]] = defaultdict(list)
    for ev in events:
        if not isinstance(ev, dict):
            continue
        d, line = fmt_event(ev)
        if today <= d <= last_day:
            events_by_day[d].append(line)

    tasks_by_day: dict[date, list[str]] = defaultdict(list)
    task_lists = run_json(["tasks", "lists", "--max", "50"])
    if isinstance(task_lists, list):
        for tl in task_lists:
            if not isinstance(tl, dict):
                continue
            tasklist_id = tl.get("id") or "@default"
            list_title = tl.get("title") or "Tasks"
            tasks = run_json(["tasks", "list", "--tasklist", tasklist_id, "--max", "100"])
            if not isinstance(tasks, list):
                continue
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                item = fmt_task(task, list_title, today)
                if not item:
                    continue
                due, line = item
                if due <= last_day:  # include overdue, because forgotten tasks are the point.
                    tasks_by_day[due].append(line)

    lines: list[str] = []
    lines.append(f"☀️ 朝の予定・タスク確認（{today:%Y-%m-%d} 07:00 JST想定）")
    lines.append(f"対象: 今日〜3日後（{today:%-m/%-d}〜{last_day:%-m/%-d}）")

    any_items = False
    for i in range(4):
        d = today + timedelta(days=i)
        evs = sorted(events_by_day.get(d, []))
        tks = sorted(tasks_by_day.get(d, []))
        lines.append("")
        lines.append(f"## {day_label(d, today)}")
        if evs:
            any_items = True
            lines.append("予定:")
            lines.extend(evs)
        else:
            lines.append("予定: なし")
        if tks:
            any_items = True
            lines.append("タスク:")
            lines.extend(tks)
        else:
            lines.append("タスク: なし")

    overdue_days = sorted(d for d in tasks_by_day if d < today)
    if overdue_days:
        any_items = True
        lines.append("")
        lines.append("## 期限切れタスク")
        for d in overdue_days:
            lines.append(day_label(d, today))
            lines.extend(sorted(tasks_by_day[d]))

    if not any_items:
        lines.append("")
        lines.append("今朝見る範囲では予定・期限付きタスクはありません。平和、逆にこわい。")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"Google予定・タスク通知の生成に失敗しました: {e}", file=sys.stderr)
        raise
