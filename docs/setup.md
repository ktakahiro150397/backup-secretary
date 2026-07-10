# セットアップ

このブランチは、Hermes 2インスタンスと OpenViking だけを扱います。

## 構成

- `hermes-main`: 個人用
- `hermes-owashota`: 身内向け
- `openviking`: 長期 memory サーバー

SearXNG、Redis、skills、knowledge、既存memory移行、Obsidian連携はこのreworkのスコープ外です。

## envファイルの考え方

このブランチでは `.env` を2種類に分けます。

```text
.env                                  # Docker Compose用。repo rootに置く。
runtime/main/hermes-data/.env          # hermes-main用。Git管理しない。
runtime/owashota/hermes-data/.env      # hermes-owashota用。Git管理しない。
```

root `.env` には秘密情報を置きません。  
Discord token、LLM API key、OpenViking API key、OpenViking namespace は各Hermesインスタンス直下の `.env` に置きます。

詳細は `docs/env.md` を参照してください。

## 初期化

```bash
cp .env.example .env
cp runtime/main/hermes-data/.env.example runtime/main/hermes-data/.env
cp runtime/owashota/hermes-data/.env.example runtime/owashota/hermes-data/.env
mkdir -p runtime/openviking workspace
```

その後、以下を編集します。

```text
.env
runtime/main/hermes-data/.env
runtime/owashota/hermes-data/.env
```

最低限、`runtime/main/hermes-data/.env` と `runtime/owashota/hermes-data/.env` で以下を別値にしてください。

```text
OPENVIKING_ACCOUNT
OPENVIKING_USER
OPENVIKING_AGENT
OPENVIKING_API_KEY
```

## OpenViking

OpenVikingは公式Docker imageを使います。

```text
ghcr.io/volcengine/openviking:latest
```

永続化先は以下です。

```text
runtime/openviking -> /app/.openviking
```

初期化します。

```bash
make ov-init
make ov-doctor
```

Docker版OpenVikingはコンテナ内で `0.0.0.0:1933` をbindするため、OpenViking側の `ov.conf` には `root_api_key` を設定してください。

## Hermes

Hermesは2つの別コンテナとして起動します。

```bash
make up
```

必要ならsetupを個別に実行します。

```bash
make setup-main
make setup-owashota
```

各インスタンスの秘密情報は、Git管理しないruntime側に置きます。

```text
runtime/main/hermes-data/.env
runtime/owashota/hermes-data/.env
```

## memory分離

OpenViking接続情報は、各インスタンス直下の `.env` で分けます。

```text
runtime/main/hermes-data/.env
  OPENVIKING_ACCOUNT=personal
  OPENVIKING_USER=yanelmo
  OPENVIKING_AGENT=hermes-main
  OPENVIKING_API_KEY=...

runtime/owashota/hermes-data/.env
  OPENVIKING_ACCOUNT=owashota
  OPENVIKING_USER=owashota
  OPENVIKING_AGENT=hermes-owashota
  OPENVIKING_API_KEY=...
```

最低限、`account` / `user` / `agent` はインスタンスごとに分けます。  
API keyも別にできる場合は必ず別にします。

このブランチでは「記憶が混ざらないこと」の検証を優先し、既存memoryやskillsの初期投入は行いません。
