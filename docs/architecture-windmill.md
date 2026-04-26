# 個人用AI秘書 構成方針（Windmillで構成するパターン）

## 1. 目的

Discordから自然言語で使える個人用AI秘書を、**運用制御しやすい構成**で段階的に構築する。

- Phase 1では「安全な最小構成（MVP）」に限定
- 長期記憶（Mem0）、MCP、ローカルLLMは後段で追加
- 危険操作は常に承認付きで実行

## 2. 一次情報ベースの前提

- Windmillはスクリプト/フローをWebhook・Scheduleで実行できる（公式 docs: Webhooks / Scheduling / Jobs）。
- Windmillの実行はジョブキューとワーカーで処理される（公式 docs: Jobs）。
- Discord Interactionsは初回応答3秒以内、トークン有効15分（公式 docs: Receiving and Responding to Interactions）。
- DiscordのMessage ContentはPrivileged Intent（公式 docs: Message Resource / Gateway）。

> 参考URL（一次情報）
>
> - https://www.windmill.dev/docs/core_concepts/webhooks
> - https://www.windmill.dev/docs/core_concepts/scheduling
> - https://www.windmill.dev/docs/core_concepts/jobs
> - https://docs.discord.com/developers/interactions/receiving-and-responding
> - https://docs.discord.com/developers/resources/message
> - https://docs.discord.com/developers/events/gateway

## 3. 推奨アーキテクチャ（段階導入）

```text
Discord
  ↓
Windmill Ingress (Webhook / HTTP Route)
  ├─ Allowlistチェック
  ├─ Rate Limitチェック
  ├─ (Interactionsなら) 3秒以内にACK
  └─ Background Job投入
      ↓
LLM Adapter（Cloud LLM）
  ├─ OpenAI / Anthropic / Gemini 切替可能
  └─ 出力制限（max tokens等）
      ↓
Reply Adapter（Discord返答）
      ↓
Logging（監査ログ）

[将来拡張]
- Mem0（長期記憶）
- pgvector
- MCP
- Ollama/Gemma
- Sandbox実行
```

## 4. コンポーネント方針

### Discord

- 初期はDMまたは専用private channel運用
- 許可ユーザー/許可チャンネルのみ受け付け
- BotにAdministrator権限は付与しない

### Windmill

- Orchestrationを一本化（Ingress / Route / Job / Schedule）
- 「同期応答」と「重い処理」を分離
- 失敗時の再実行方針（idempotentな範囲のみ）を明示

### Cloud LLM

- Phase 1はメイン推論のみ
- ツール呼び出しは最小（返信生成中心）
- コスト制御：デフォルト軽量モデル + 上限トークン

### 永続層

- Phase 1はPostgreSQL中心（ログ・設定・将来拡張用メタ）
- 記憶そのものはPhase 3以降にMem0で導入

## 5. 実装フェーズ

## Phase 1（必須）

- Discord連携（GatewayまたはInteractions）
- Windmill ingress
- Allowlist / Rate Limit
- Cloud LLM adapter
- Discord reply
- 監査ログ

**非対象**: Mem0 / MCP / Ollama / Gemma / Sandbox / ファイル操作 / メール送信

## Phase 2

- ACK + 非同期バックグラウンド化
- 失敗時リトライ・エラーハンドリング強化

## Phase 3

- Mem0導入（検索は必要時のみ）
- 記憶保存は返信後に非同期で実施

## 6. セキュリティ方針（最小）

1. LLM実行前に Allowlist / Rate Limit を必ず通す
2. DiscordトークンやAPIキーは`.env`/Secret Manager管理（リポジトリにコミットしない）
3. Windmill管理UIは公開しない（VPN/Tailscale/Access等）
4. ログは「必要十分」だけ保存（秘密情報はマスク）
5. 危険操作は未実装のまま開始（Phase 1でやらない）

## 7. この構成が向くケース

- 長期運用での**透明性・可観測性・制御性**を重視
- 障害切り分けをしやすくしたい
- 機能を段階導入し、失敗時に戻しやすくしたい
