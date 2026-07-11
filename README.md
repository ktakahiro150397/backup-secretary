# backup-secretary

Hermes Agent と OpenViking だけで構成する、最小スコープの rework ブランチです。

## スコープ

- `hermes-main`: 個人用 Hermes インスタンス
- `hermes-owashota`: 身内向け Hermes インスタンス
- `openviking`: Hermes から参照する長期 memory サーバー

このブランチでは、SearXNG、Redis、skills、knowledge、既存 memory、Obsidian 連携などは扱いません。

## 目的

1. Hermes の2インスタンスが、別々の runtime data dir で分離して動くこと。
2. 2つのHermesがOpenVikingへ接続できること。
3. OpenViking上で account / user / agent / API key を分け、インスタンス間で記憶が混ざらない構成にすること。

## envファイル

このブランチでは `.env` を2種類に分けます。

```text
.env                                  # Docker Compose用。秘密情報は置かない。
runtime/main/hermes-data/.env          # hermes-main用。Git管理しない。
runtime/owashota/hermes-data/.env      # hermes-owashota用。Git管理しない。
```

詳細は `docs/env.md` を参照してください。サーバーへの初回構築、既存記憶の投入、起動、分離確認は `docs/server-runbook.md` にまとめています。

## 使い方

```bash
cp .env.example .env
cp runtime/main/hermes-data/.env.example runtime/main/hermes-data/.env
cp runtime/owashota/hermes-data/.env.example runtime/owashota/hermes-data/.env
make up
```

OpenVikingの初期化は以下です。

```bash
make ov-init
make ov-doctor
```

既存accountにuserを追加し、専用API keyを発行する場合:

```bash
make ov-provision-user ACCOUNT=hermes-main NAME=coder
```

表示されたkeyは再表示できないため、その場で対象HermesプロファイルのGit管理外 `.env` に保存します。詳細は `docs/setup.md` を参照してください。

OpenViking CLIとTUIはMakeターゲットから起動できます。

```bash
make ov ARGS="health"
make ov-config
make ov-tui
```

Hermesの対話CLIはインスタンス別に起動します。

```bash
make hermes-main
make hermes-owashota
```

OpenVikingではHermesごとにaccount、user、agent、API keyを分離します。CLI/TUIで各Hermesのデータを見る場合も、対象userのAPI keyを持つCLI configへ切り替えます。

設定変更後の反映は以下です。

```bash
make restart
```

詳細は `docs/setup.md`、`docs/env.md`、`docs/architecture.md` を参照してください。
