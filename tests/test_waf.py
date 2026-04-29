import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "waf.py"


def run_waf(tmp_path, *args):
    db_path = tmp_path / "waf.db"
    proc = subprocess.run(
        [sys.executable, str(CLI), "--db", str(db_path), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip(), db_path


def test_capture_creates_sqlite_database_with_fts_index(tmp_path):
    out, db_path = run_waf(
        tmp_path,
        "capture",
        "HermesのWrite-And-Forget captureをSQLite FTS5で作る",
        "--source",
        "discord",
        "--tags",
        "hermes,waf",
    )

    payload = json.loads(out)
    assert payload["status"] == "captured"
    assert payload["note"]["id"] == 1
    assert payload["note"]["status"] == "open"
    assert payload["note"]["source"] == "discord"
    assert payload["note"]["tags"] == ["hermes", "waf"]

    con = sqlite3.connect(db_path)
    try:
        stored = con.execute(
            "select body, source, status, tags_json from notes where id = ?",
            (payload["note"]["id"],),
        ).fetchone()
        assert stored == (
            "HermesのWrite-And-Forget captureをSQLite FTS5で作る",
            "discord",
            "open",
            '["hermes", "waf"]',
        )
        fts_rows = con.execute(
            "select rowid from notes_fts where notes_fts match ?",
            ("Write",),
        ).fetchall()
        assert fts_rows == [(1,)]
    finally:
        con.close()


def test_search_returns_matching_open_notes_by_default(tmp_path):
    run_waf(tmp_path, "capture", "メインLLM候補をOpenRouterで比較する", "--tags", "llm")
    run_waf(tmp_path, "capture", "保育園の持ち物を確認する", "--tags", "family")

    out, _ = run_waf(tmp_path, "search", "OpenRouter")

    payload = json.loads(out)
    assert payload["status"] == "ok"
    assert [item["body"] for item in payload["results"]] == [
        "メインLLM候補をOpenRouterで比較する"
    ]
    assert payload["results"][0]["tags"] == ["llm"]


def test_status_update_hides_closed_notes_unless_requested(tmp_path):
    out, _ = run_waf(tmp_path, "capture", "あとでGitHub issueにする")
    note_id = json.loads(out)["note"]["id"]

    update_out, _ = run_waf(tmp_path, "status", str(note_id), "closed")
    assert json.loads(update_out)["note"]["status"] == "closed"

    search_out, _ = run_waf(tmp_path, "search", "GitHub")
    assert json.loads(search_out)["results"] == []

    all_out, _ = run_waf(tmp_path, "search", "GitHub", "--include-closed")
    results = json.loads(all_out)["results"]
    assert len(results) == 1
    assert results[0]["status"] == "closed"


def test_capture_rejects_empty_body(tmp_path):
    db_path = tmp_path / "waf.db"
    proc = subprocess.run(
        [sys.executable, str(CLI), "--db", str(db_path), "capture", "   "],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert proc.returncode == 2
    assert "body must not be empty" in proc.stderr
