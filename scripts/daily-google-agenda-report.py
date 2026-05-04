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

HIGH_SIGNAL_KEYWORDS = (
    "支払", "支払い", "期限", "振込", "解約", "予約", "病院", "耳鼻", "歯科",
    "カウンセリング", "面談", "締切", "提出", "実家", "保育", "学校",
)


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


def contains_high_signal(text: str) -> bool:
    return any(k in text for k in HIGH_SIGNAL_KEYWORDS)


def event_priority_item(ev: dict, today: date, last_day: date) -> tuple[int, str] | None:
    start, all_day = parse_event_dt(ev.get("start", ""))
    end, _ = parse_event_dt(ev.get("end", ""))
    if start is None:
        return None
    d = start.date()
    if not (today <= d <= last_day):
        return None

    title = ev.get("summary") or "(無題)"
    cal = ev.get("calendar") or "calendar"
    signal = contains_high_signal(title)
    diff = (d - today).days

    if all_day:
        return None

    if end and end.date() == d:
        when = f"{start:%H:%M}-{end:%H:%M}"
    else:
        when = f"{start:%H:%M}〜"

    if diff == 0:
        if "支払" in title or "支払い" in title or "期限" in title or "振込" in title:
            return 1, f"【最優先】{title} を午前中に処理する。"
        return 3, f"【固定予定】{when} {title} [{cal}] 。開始30分前に準備する。"

    if signal:
        if "予約" in title:
            action = "予約・持ち物・移動時間を前日までに確認する"
        elif "病院" in title or "耳鼻" in title or "歯科" in title or "カウンセリング" in title:
            action = "保険証と診察券を準備する"
        elif "実家" in title:
            action = "持ち物と出発時間を決める"
        else:
            action = "前倒しで準備する"
        return 20 + diff, f"【先回り】{day_label(d, today)} {when} {title} — {action}。"

    return None


def task_priority_item(task: dict, list_title: str, today: date, last_day: date) -> tuple[int, str] | None:
    if task.get("status") == "completed":
        return None
    due = parse_task_due(task.get("due", ""))
    if due is None or due > last_day:
        return None
    title = task.get("title") or "(無題タスク)"
    if due < today:
        return 0, f"【期限切れ】{title} [{list_title}] を完了または延期する。"
    diff = (due - today).days
    if diff == 0:
        return 2, f"【今日のタスク】{title} [{list_title}] を午前中に着手する。"
    return None


def build_priority_lines(priority_items: list[tuple[int, str]]) -> list[str]:
    if not priority_items:
        return [
            "## 今日の優先アクション",
            "特に急ぎのアクションはなし。ゆっくり始める。",
        ]

    lines = ["## 今日の優先アクション"]
    seen: set[str] = set()
    rank = 1
    for _, text in sorted(priority_items, key=lambda x: x[0]):
        if text in seen:
            continue
        seen.add(text)
        lines.append(f"{rank}. {text}")
        rank += 1
        if rank > 5:
            break
    return lines


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
    priority_items: list[tuple[int, str]] = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        d, line = fmt_event(ev)
        if today <= d <= last_day:
            events_by_day[d].append(line)
        priority = event_priority_item(ev, today, last_day)
        if priority:
            priority_items.append(priority)

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
                priority = task_priority_item(task, list_title, today, last_day)
                if priority:
                    priority_items.append(priority)

    lines: list[str] = []
    lines.append(f"☀️ 朝の予定・タスク確認（{today:%Y-%m-%d} 07:00 JST想定）")
    lines.append(f"対象: 今日〜3日後（{today:%-m/%-d}〜{last_day:%-m/%-d}）")
    lines.append("")
    lines.extend(build_priority_lines(priority_items))

    any_items = False
    for i in range(4):
        d = today + timedelta(days=i)
        evs = sorted(events_by_day.get(d, []))
        tks = sorted(tasks_by_day.get(d, []))
        if not evs and not tks:
            continue
        any_items = True
        lines.append("")
        lines.append(f"## {day_label(d, today)}")
        if evs:
            lines.append("予定:")
            lines.extend(evs)
        if tks:
            lines.append("タスク:")
            lines.extend(tks)

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

