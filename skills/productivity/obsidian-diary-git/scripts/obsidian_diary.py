#!/usr/bin/env python3
"""Git-backed Obsidian diary writer for Hermes.

Writes diary entries to an Obsidian vault clone on a dedicated branch, then
commits and optionally pushes the change. Intended default location is the
persistent Hermes home, not a separate Docker bind mount.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

DEFAULT_VAULT = Path(os.environ.get("OBSIDIAN_VAULT_PATH", "/opt/data/obsidian/obsidian_git"))
DEFAULT_BRANCH = os.environ.get("OBSIDIAN_DIARY_BRANCH", "hermes")
DEFAULT_REPO = os.environ.get("OBSIDIAN_REPO_URL", "")
DEFAULT_DIARY_DIR = os.environ.get("OBSIDIAN_DIARY_DIR", "10_Diary")
JST = ZoneInfo("Asia/Tokyo")


class DiaryError(RuntimeError):
    pass


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def run_git(vault: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=vault,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and proc.returncode != 0:
        command = "git " + " ".join(args)
        detail = (proc.stderr or proc.stdout).strip()
        raise DiaryError(f"{command} failed: {detail}")
    return proc


def ensure_vault(vault: Path, repo: str | None = None) -> None:
    if (vault / ".git").is_dir():
        return
    if vault.exists() and any(vault.iterdir()):
        raise DiaryError(f"vault path exists but is not a git repo: {vault}")
    if not repo:
        raise DiaryError(f"vault is missing and no repo URL was provided: {vault}")
    vault.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["git", "clone", repo, str(vault)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise DiaryError(f"git clone failed: {detail}")


def current_branch(vault: Path) -> str:
    return run_git(vault, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def remote_branch_exists(vault: Path, branch: str) -> bool:
    proc = run_git(vault, "ls-remote", "--exit-code", "--heads", "origin", branch, check=False)
    return proc.returncode == 0


def ensure_branch(vault: Path, branch: str) -> None:
    if current_branch(vault) == branch:
        return
    local = run_git(vault, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False)
    if local.returncode == 0:
        run_git(vault, "checkout", branch)
    elif remote_branch_exists(vault, branch):
        run_git(vault, "checkout", "-b", branch, f"origin/{branch}")
    else:
        run_git(vault, "checkout", "-b", branch)


def sync_before_write(vault: Path, branch: str, *, skip_pull: bool) -> None:
    ensure_branch(vault, branch)
    if skip_pull:
        return
    run_git(vault, "fetch", "origin", "--prune")
    if remote_branch_exists(vault, branch):
        run_git(vault, "pull", "--rebase", "--autostash", "origin", branch)


def parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    tags: list[str] = []
    seen: set[str] = set()
    for part in raw.split(","):
        tag = part.strip().lstrip("#")
        if tag and tag not in seen:
            tags.append(tag)
            seen.add(tag)
    return tags


def unique_values(values: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            unique.append(value)
            seen.add(value)
    return unique


def yaml_list(values: list[str], indent: str = "  ") -> str:
    values = unique_values(values)
    if not values:
        return "[]"
    return "\n" + "\n".join(f"{indent}- {value}" for value in values)


def diary_path(vault: Path, diary_dir: str, day: datetime) -> Path:
    return vault / diary_dir / day.strftime("%Y") / day.strftime("%m") / f"{day:%Y-%m-%d}.md"


def create_entry_file(path: Path, day: datetime, now: datetime, source: str, tags: list[str]) -> None:
    weekday = day.strftime("%A")
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""---
type: diary
date: {day:%Y-%m-%d}
weekday: {weekday}
created: {now.isoformat(timespec="seconds")}
updated: {now.isoformat(timespec="seconds")}
tags:{yaml_list(["diary", *tags])}
people: []
topics: []
tasks: []
private: true
source: {source}
---

# {day:%Y-%m-%d} 日記

"""
    path.write_text(content, encoding="utf-8")


def update_frontmatter_timestamp(path: Path, now: datetime) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return
    end = text.find("\n---\n", 4)
    if end == -1:
        return
    front = text[:end]
    rest = text[end:]
    lines = front.splitlines()
    updated = False
    for idx, line in enumerate(lines):
        if line.startswith("updated:"):
            lines[idx] = f"updated: {now.isoformat(timespec='seconds')}"
            updated = True
            break
    if not updated:
        lines.append(f"updated: {now.isoformat(timespec='seconds')}")
    path.write_text("\n".join(lines) + rest, encoding="utf-8")


def append_entry(path: Path, body: str, now: datetime, source: str, tags: list[str]) -> None:
    tag_text = " ".join(f"#{tag}" for tag in tags)
    meta = f"source: {source}"
    if tag_text:
        meta += f" / {tag_text}"
    block = f"\n## {now.strftime('%H:%M')} Hermes\n\n<!-- {meta} -->\n\n{body.strip()}\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(block)


def has_changes(vault: Path) -> bool:
    proc = run_git(vault, "status", "--porcelain")
    return bool(proc.stdout.strip())


def commit_and_push(vault: Path, rel_path: str, date_text: str, branch: str, *, no_push: bool) -> dict[str, Any]:
    run_git(vault, "add", rel_path)
    if not has_changes(vault):
        return {"committed": False, "commit": None, "pushed": False}
    run_git(vault, "commit", "-m", f"diary: {date_text}")
    commit = run_git(vault, "rev-parse", "HEAD").stdout.strip()
    pushed = False
    if not no_push:
        run_git(vault, "push", "-u", "origin", branch)
        pushed = True
    return {"committed": True, "commit": commit, "pushed": pushed}


def save_diary_entry(
    vault: Path,
    repo: str | None,
    branch: str,
    diary_dir: str,
    body: str,
    date: str | None,
    source: str,
    tags: list[str],
    no_pull: bool,
    no_push: bool,
) -> dict[str, Any]:
    vault = vault.resolve()
    ensure_vault(vault, repo)
    sync_before_write(vault, branch, skip_pull=no_pull)

    now = datetime.now(JST)
    day = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=JST) if date else now
    path = diary_path(vault, diary_dir, day)
    if path.exists():
        update_frontmatter_timestamp(path, now)
    else:
        create_entry_file(path, day, now, source, tags)
    append_entry(path, body, now, source, tags)

    rel_path = path.relative_to(vault).as_posix()
    git_result = commit_and_push(vault, rel_path, day.strftime("%Y-%m-%d"), branch, no_push=no_push)
    return {
        "status": "saved",
        "vault": str(vault),
        "branch": branch,
        "path": rel_path,
        **git_result,
    }


def get_status(vault: Path, repo: str | None, branch: str) -> dict[str, Any]:
    vault = vault.resolve()
    ensure_vault(vault, repo)
    current = current_branch(vault)
    proc = run_git(vault, "status", "--porcelain")
    return {"status": "ok", "vault": str(vault), "branch": current, "dirty": bool(proc.stdout.strip())}


def save_diary(args: argparse.Namespace) -> dict[str, Any]:
    return save_diary_entry(
        vault=args.vault,
        repo=args.repo or None,
        branch=args.branch,
        diary_dir=args.diary_dir,
        body=args.body,
        date=args.date,
        source=args.source,
        tags=parse_tags(args.tags),
        no_pull=args.no_pull,
        no_push=args.no_push,
    )


def status(args: argparse.Namespace) -> dict[str, Any]:
    return get_status(vault=args.vault, repo=args.repo or None, branch=args.branch)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Save diary entries to a Git-backed Obsidian vault")
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT, help=f"Vault clone path (default: {DEFAULT_VAULT})")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="Repo URL used when --vault is not cloned yet")
    parser.add_argument("--branch", default=DEFAULT_BRANCH, help=f"Diary branch (default: {DEFAULT_BRANCH})")
    parser.add_argument("--diary-dir", default=DEFAULT_DIARY_DIR, help=f"Diary root directory in vault (default: {DEFAULT_DIARY_DIR})")
    sub = parser.add_subparsers(dest="command", required=True)

    save = sub.add_parser("save", help="Append a diary entry and commit it")
    save.add_argument("body", help="Diary body markdown")
    save.add_argument("--date", help="Diary date YYYY-MM-DD; defaults to today in JST")
    save.add_argument("--source", default="hermes-discord", help="Source label")
    save.add_argument("--tags", default="", help="Comma-separated tags, without or with #")
    save.add_argument("--no-pull", action="store_true", help="Skip fetch/pull before writing")
    save.add_argument("--no-push", action="store_true", help="Commit locally but do not push")

    stat = sub.add_parser("status", help="Show vault status")
    stat.set_defaults(func=status)
    save.set_defaults(func=save_diary)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        emit(args.func(args))
    except (DiaryError, OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
