# Kanban Multi-Profile Setup

JUMPERZ 式の「Coordinator + Worker」構成を導入するための設定変更。

## Architecture

```
Discord (#inbox-from-chrome, #hermes-dev, etc.)
        ↓
Coordinator (kimi-k2.6) — routes, decomposes, tracks Kanban
        ↓ kanban_create
    ┌───┴───┐
researcher  technical
(Gemma 31B) (deepseek-v4-flash)
```

- **Coordinator**：Discord に常時接続。依頼を受けてタスク分解 → Kanban タスク化 → 適切な Worker にアサイン。自分では作業しない。
- **Researcher**：web / browser / file で情報収集・調査。Discord 非接続。
- **Technical**：terminal / file / code_execution でコード・システム作業。Discord 非接続。

## 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `compose.yaml` | `hermes` サービスの command を `gateway run -p coordinator` に変更 |
| `.gitignore` | `profiles/coordinator/researcher/technical/config.yaml` をトラッキング許可 |
| `scripts/init-kanban-profiles.py` | プロファイル生成・設定スクリプト（新規） |
| `docs/kanban-profiles.md` | この手順書（新規） |

## セットアップ手順

### 1. ブランチを checkout してコンテナに反映

```bash
cd /workspace/backup-secretary
docker compose up -d --force-recreate hermes
```

### 2. プロファイルを初期化

`cli` サービスや直接コンテナ内で実行：

```bash
docker compose run --rm cli python3 /workspace/backup-secretary/scripts/init-kanban-profiles.py
```

または `hermes` コンテナ内で：

```bash
docker compose exec hermes python3 /workspace/backup-secretary/scripts/init-kanban-profiles.py
```

### 3. 確認

```bash
docker compose exec hermes hermes profile list
```

`coordinator`, `researcher`, `technical` の 3 つが表示されるはず。

### 4. Gateway 再起動

```bash
docker compose up -d --force-recreate hermes
```

## 環境変数の準備

| プロファイル | 必要な環境変数 | 備考 |
|-------------|---------------|------|
| `coordinator` | `OPENCODE_GO_API_KEY` | 既存のまま |
| `researcher` | `OPENROUTER_API_KEY` | OpenRouter で Gemma 31B を使うため新規設定が必要 |
| `technical` | `OPENCODE_GO_API_KEY` | coordinator と同じキーを流用可 |

`.env` やコンテナの `environment:` に追加しておく。

## 次のステップ

1. **動作確認**：Discord で適当な調査依頼を投げ、Coordinator が `kanban_create` でタスク化し、Dispatcher が researcher/technical を起動することを確認する。
2. **Cron 移行（任意）**：長期・複数ステップの cron job（例：`research-vault-daily-refresh`）を Kanban タスク化して追跡性を上げる。
3. **Dashboard 確認**：`docker compose --profile dashboard up -d` で Kanban ボードを見ながらタスクの流れを確認する。

## Coordinator の振り分け判断基準

Coordinator は以下のルールで「その場で返答」か「Kanban タスク化」かを判断する：

| 類型 | 動作 | 例 |
|------|------|-----|
| **雑談・軽い相談・知ってる情報の返答** | その場で返答 | 「今日の天気どう？」「そのキーボードどう思う？」「ちょっと慶して」 |
| **調査・コード書き・ドキュメント作成・分析** | `kanban_create` で Worker へ | 「この URL を調べて」「その関数を修正して」「レポート書いて」 |
| **迷ったら** | ユーザーに確認 | 「これちょっと調べる？」と聞く |

これは `coordinator` プロファイルの `SOUL.md` に書かれており、スクリプト実行時に自動生成される。

### channel_prompts は必見？

**必見ではない。あった方が堅牢。**

Coordinator の `SOUL.md` がメインの振り分けルールである。しかし、チャンネルごとに用途が固定されているなら `channel_prompts` で補強すると迷いが減る：

- `#ask-hermes` → 「軽い雑談がメイン。作業依頼は kanban_create せず、その場で答えてから hermes-dev に導く」
- `#hermes-dev` → 「技術調査・コード作成は kanban_create する。純粋な質問はその場で」
- `#inbox-from-chrome` → 「URL が飛んでくる。概要だけ詰めて必要なら kanban_create する」

これらは `runtime/hermes-data/config.yaml` の `discord.channel_prompts` に手動で追記する。（init スクリプトでは変更しない）

## 注意

- `hermes-owashota` は変更しない。別 Bot として独立して運用する。
- Worker プロファイル（researcher/technical）は Discord に繋がないため、`send_message` 等は使わない。結果は Kanban → Coordinator がまとめて Discord に通知する形にする。
