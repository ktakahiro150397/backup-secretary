# hermes-main Pixivデータ収集

Pixivデータ収集は、現行 `hermes-main` の非LLM cronジョブとして動かします。収集とチャート生成は分離し、このジョブはSQLite更新とCSV出力だけを担当します。

## 正本と呼び出し関係

```text
Hermes cron: pixiv-watcher-data
  -> /opt/data/scripts/pixiv-collect-data.sh
  -> /opt/data/repos/pixiv-watcher/scripts/collect.sh
  -> collector + exporter
```

実装の正本はPixivリポジトリ内の `scripts/collect.sh` です。cron側の `pixiv-collect-data.sh` は正本を `exec` するだけのラッパーとし、収集処理を重複させません。

## パスの意味

Hermesはcronの相対スクリプト名を `$HERMES_HOME/scripts/` から解決します。現行コンテナは `HOME=/opt/data`、`HERMES_HOME=/opt/data` なので、次はすべて同じ場所です。

```text
$HERMES_HOME/scripts
$HOME/scripts
~/scripts
~/./scripts
/opt/data/scripts
```

リポジトリ内に `pixiv-collect-data.sh` がないことは異常ではありません。ホスト側とコンテナ側の対応は次のとおりです。

```text
runtime/main/hermes-data/                     -> /opt/data
runtime/main/hermes-data/scripts/             -> /opt/data/scripts
runtime/main/hermes-data/repos/pixiv-watcher/ -> /opt/data/repos/pixiv-watcher
```

## 配置

cronラッパーはこのリポジトリの `scripts/pixiv-collect-data.sh` を配置します。

```bash
install -m 755 scripts/pixiv-collect-data.sh \
  runtime/main/hermes-data/scripts/pixiv-collect-data.sh
```

Pixiv認証情報は次に置き、Gitへ追加しません。権限は `600` にします。

```text
runtime/main/hermes-data/repos/pixiv-watcher/.env
```

## 現行cronジョブ

```text
name: pixiv-watcher-data
schedule: */30 * * * *
script: pixiv-collect-data.sh
mode: no-agent
workdir: /opt/data/repos/pixiv-watcher
deliver: local
```

確認:

```bash
docker compose exec hermes-main hermes cron list
docker compose exec hermes-main hermes cron status
```

手動でcron経由の動作を確認する場合は、一覧でIDを確認して実行します。

```bash
docker compose exec hermes-main hermes cron run <job-id>
```

成功時は次が更新されます。

```text
/opt/data/repos/pixiv-watcher/data/pixiv_stats.db
/opt/data/repos/pixiv-watcher/data/export/user_stats.csv
/opt/data/repos/pixiv-watcher/data/export/illust_stats.csv
```

## チャート

データ収集ジョブからチャート生成を呼びません。`scripts/gen_charts.py` などのチャート用コードは別cronから利用するため、Pixivリポジトリ内に残します。

次の2ファイルへチャート処理を追加しないでください。

```text
/opt/data/scripts/pixiv-collect-data.sh
/opt/data/repos/pixiv-watcher/scripts/collect.sh
```

## 障害確認

「スクリプトがない」と判断する前に、ホストではなく `hermes-main` コンテナ内で確認します。

```bash
docker compose exec hermes-main sh -lc \
  'printf "HOME=%s HERMES_HOME=%s\n" "$HOME" "$HERMES_HOME"; \
   readlink -f ~/./scripts; \
   ls -l /opt/data/scripts/pixiv-collect-data.sh \
         /opt/data/repos/pixiv-watcher/scripts/collect.sh'
```

収集だけを直接確認する場合:

```bash
docker compose exec hermes-main \
  bash /opt/data/repos/pixiv-watcher/scripts/collect.sh
```
