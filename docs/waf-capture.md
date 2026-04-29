# Write-And-Forget capture MVP

Issue #10 の Phase 1 実装メモ。

## 目的

雑に投げた断片を、標準 memory へ直接混ぜずにローカルの retrievable inbox へ保存する。

- 保存先: SQLite database
- 検索: SQLite FTS5
- 外部副作用: なし
- Google Tasks / Calendar / GitHub / Obsidian への書き出し: Phase 1 ではしない

## CLI

```bash
# capture
python3 tools/waf.py capture "HermesのメインLLM候補を比較する" --source discord --tags hermes,llm

# search
python3 tools/waf.py search "Hermes"

# terminal states are hidden by default; include them explicitly
python3 tools/waf.py search "Hermes" --include-closed

# update status
python3 tools/waf.py status 1 closed
```

デフォルトDBパスは `/opt/data/waf/waf.db`。
テストやローカル検証では `--db` または `WAF_DB` を使う。

```bash
python3 tools/waf.py --db /tmp/waf.db capture "あとで読む"
WAF_DB=/tmp/waf.db python3 tools/waf.py search "あとで"
```

## JSON output

`capture`:

```json
{
  "status": "captured",
  "note": {
    "id": 1,
    "body": "...",
    "source": "discord",
    "status": "open",
    "created_at": "...",
    "updated_at": "...",
    "tags": ["hermes", "llm"]
  }
}
```

`search`:

```json
{
  "status": "ok",
  "results": [
    {
      "id": 1,
      "body": "...",
      "source": "discord",
      "status": "open",
      "created_at": "...",
      "updated_at": "...",
      "tags": ["hermes", "llm"]
    }
  ]
}
```

## Status model

`notes.status` は次の5種類。

- `open`: 未処理
- `suggested`: 整理・外部書き出し候補あり
- `actioned`: 承認済みの外部アクション実行済み
- `dismissed`: 明示的に不要扱い
- `closed`: 完了/アーカイブ扱い

`search` はデフォルトで `open` / `suggested` のみ返す。
`actioned` / `dismissed` / `closed` は `--include-closed` 指定時のみ返す。

## Design notes

- FTS5 tokenizer は `trigram` を使う。日本語・英語混在の短文検索で `unicode61` より取りこぼしにくいため。
- tags は `tags_json` にJSON配列として保存する。検索用にはFTSにもスペース区切りで投入する。
- `suggestions` table はPhase 2用の下地。Phase 1では外部書き込みは実行しない。
- SQLはparameterized queryのみを使う。

## Tests

```bash
uv run --with pytest python -m pytest tests/test_waf.py -q
```
