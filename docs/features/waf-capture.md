# Write-And-Forget capture MVP

Issue #10 の Phase 1 実装メモ。

実体は repo-managed Hermes skill として管理する。

```text
skills/productivity/write-and-forget-capture/
  SKILL.md
  scripts/waf.py
```

詳しい使い方・安全ルールは `skills/productivity/write-and-forget-capture/SKILL.md` を参照。

## 概要

雑に投げた断片を、標準 memory へ直接混ぜずにローカルの retrievable inbox へ保存する。

- 保存先: SQLite database
- 検索: SQLite FTS5
- 外部副作用: なし
- Google Tasks / Calendar / GitHub / Obsidian への書き出し: Phase 1 ではしない

デフォルトDBパスは `/opt/data/waf/waf.db`。

## Tests

```bash
uv run --with pytest python -m pytest tests/test_waf.py -q
```
