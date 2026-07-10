# セットアップ

このブランチは、Hermes 2インスタンスと OpenViking だけを扱います。

## 構成

- `hermes-main`: 個人用
- `hermes-owashota`: 身内向け
- `openviking`: 長期 memory サーバー

SearXNG、Redis、skills、knowledge、既存memory移行、Obsidian連携はこのreworkのスコープ外です。

## 初期化

```bash
cp .env.example .env
mkdir -p runtime/main/hermes-data runtime/owashota/hermes-data runtime/openviking workspace
```

Linux / WSL では `.env` の UID/GID をホストユーザーに合わせます。

```bash
sed -i "s/^HERMES_UID=.*/HERMES_UID=$(id -u)/" .env
sed -i "s/^HERMES_GID=.*/HERMES_GID=$(id -g)/" .env
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

OpenViking接続情報は `.env` で分けます。

```text
OPENVIKING_MAIN_ACCOUNT
OPENVIKING_MAIN_USER
OPENVIKING_MAIN_AGENT
OPENVIKING_MAIN_API_KEY

OPENVIKING_OWASHOTA_ACCOUNT
OPENVIKING_OWASHOTA_USER
OPENVIKING_OWASHOTA_AGENT
OPENVIKING_OWASHOTA_API_KEY
```

最低限、`account` / `user` / `agent` はインスタンスごとに分けます。
API keyも別にできる場合は必ず別にします。

このブランチでは「記憶が混ざらないこと」の検証を優先し、既存memoryやskillsの初期投入は行いません。
