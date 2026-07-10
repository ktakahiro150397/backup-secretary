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

## 使い方

```bash
cp .env.example .env
make up
```

OpenVikingの初期化は以下です。

```bash
make ov-init
make ov-doctor
```

設定変更後の反映は以下です。

```bash
make restart
```

詳細は `docs/setup.md` と `docs/architecture.md` を参照してください。
