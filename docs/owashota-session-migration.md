# owashota旧セッション移行

`scripts/migrate_hermes_sessions_to_ov.py`は、旧Hermesのuser/assistantメッセージを
memoryへ変換せずOpenVikingの生sessionへコピーします。既定はdry-runです。

2026年5月1日から7日（JST）の最初の1 sessionを確認します。

```bash
python3 scripts/migrate_hermes_sessions_to_ov.py \
  --db "$HOME/repo/backup-secretary-data/owashota/hermes-data/state.db" \
  --limit 1
```

DBの実パスが異なる場合は、退避ディレクトリ内のowashota用`state.db`を指定します。
確認後、owashota用OpenViking環境変数を読み込んだシェルで`--apply`を追加します。

```bash
set -a
. runtime/owashota/hermes-data/.env
set +a
python3 scripts/migrate_hermes_sessions_to_ov.py \
  --db "$HOME/repo/backup-secretary-data/owashota/hermes-data/state.db" \
  --limit 1 \
  --apply
```

この処理は`commit`を呼ばないためmemory抽出は行いません。manifestは
`runtime/migrations/`へ出力され、既存の`runtime/**`規則でGit管理外です。
