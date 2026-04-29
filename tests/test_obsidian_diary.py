import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills" / "productivity" / "obsidian-diary-git" / "scripts" / "obsidian_diary.py"


def git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def init_repo(path: Path) -> None:
    path.mkdir(parents=True)
    git(path, "init", "-b", "main")
    git(path, "config", "user.email", "test@example.com")
    git(path, "config", "user.name", "Test User")
    (path / "README.md").write_text("# vault\n", encoding="utf-8")
    git(path, "add", "README.md")
    git(path, "commit", "-m", "init")


def run_diary(vault: Path, *args: str):
    proc = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--vault",
            str(vault),
            "--branch",
            "hermes",
            *args,
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_save_creates_dated_markdown_on_hermes_branch(tmp_path):
    vault = tmp_path / "vault"
    init_repo(vault)

    payload = run_diary(
        vault,
        "save",
        "今日はHermesの日記保存を試した",
        "--date",
        "2026-04-29",
        "--source",
        "hermes-discord",
        "--tags",
        "hermes,diary",
        "--no-pull",
        "--no-push",
    )

    assert payload["status"] == "saved"
    assert payload["branch"] == "hermes"
    assert payload["path"] == "10_Diary/2026/04/2026-04-29.md"
    assert payload["committed"] is True
    assert payload["pushed"] is False
    assert git(vault, "rev-parse", "--abbrev-ref", "HEAD") == "hermes"

    diary = vault / payload["path"]
    text = diary.read_text(encoding="utf-8")
    assert "type: diary" in text
    assert "date: 2026-04-29" in text
    assert "source: hermes-discord" in text
    assert text.count("  - diary") == 1
    assert "- hermes" in text
    assert "今日はHermesの日記保存を試した" in text


def test_save_appends_to_existing_day_and_updates_timestamp(tmp_path):
    vault = tmp_path / "vault"
    init_repo(vault)

    first = run_diary(vault, "save", "一回目", "--date", "2026-04-29", "--no-pull", "--no-push")
    second = run_diary(vault, "save", "二回目", "--date", "2026-04-29", "--no-pull", "--no-push")

    assert first["path"] == second["path"]
    text = (vault / second["path"]).read_text(encoding="utf-8")
    assert text.count("## ") >= 2
    assert "一回目" in text
    assert "二回目" in text
    assert "updated:" in text


def test_status_reports_branch_and_dirty_state(tmp_path):
    vault = tmp_path / "vault"
    init_repo(vault)
    git(vault, "checkout", "-b", "hermes")

    payload = run_diary(vault, "status")

    assert payload == {
        "status": "ok",
        "vault": str(vault.resolve()),
        "branch": "hermes",
        "dirty": False,
    }


def test_rejects_missing_vault_without_repo(tmp_path):
    vault = tmp_path / "missing"
    proc = subprocess.run(
        [sys.executable, str(CLI), "--vault", str(vault), "save", "本文", "--no-pull", "--no-push"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert proc.returncode == 2
    assert "vault is missing and no repo URL was provided" in proc.stderr
