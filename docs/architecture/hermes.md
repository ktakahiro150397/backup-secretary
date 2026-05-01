# 個人用AI秘書 構成方針（Hermes Agentを使うパターン）

## 1. 目的

Hermes Agentの既成機能を活用して、**短期間でAI秘書の実用検証（PoC）**まで進める。

- Messaging Gateway（Discord含む）
- Memory / Skills / Cron / MCP などの統合機能を利用
- 本番採用はPoC評価後に判断

## 2. 一次情報ベースの前提

Hermes公式ドキュメント/公式GitHubで、以下が明示されている。

- 複数メッセージング連携（Discord含む）
- 組み込みcron
- Memory/Skillsシステム
- MCP統合
- 複数プロバイダ対応
- 複数Terminal Backend（local / Docker / SSH など）

> 参考URL（一次情報）
>
> - https://hermes-agent.nousresearch.com/docs/
> - https://hermes-agent.nousresearch.com/docs/user-guide/messaging
> - https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord/
> - https://hermes-agent.nousresearch.com/docs/user-guide/configuration/
> - https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp/
> - https://github.com/NousResearch/hermes-agent

## 3. 推奨アーキテクチャ（PoC優先）

```text
Discord
  ↓
Hermes Messaging Gateway
  ↓
Hermes Core
  ├─ Memory
  ├─ Skills
  ├─ Cron
  ├─ MCP
  └─ Model Provider Routing
  ↓
Execution Backend
  ├─ Docker（推奨）
  └─ local（PoCでも原則非推奨）
```

## 4. 設計方針

### 4.1 最初からDocker Backendを使う

- local backendはホスト権限に近くなりやすい
- PoC段階でもDocker backendに固定し、作業ディレクトリを制限

### 4.2 ツール公開を最小化

- MCP tool filtering（include/exclude）を使い、必要最小限のみ公開
- 書き込み系・外部送信系は初期状態で無効

### 4.3 まずは「秘書ユースケースの核」だけ検証

- Discord会話
- 定時通知（cron）
- 記憶参照
- モデル切替

## 5. 1週間PoCの受け入れ基準

1. Discordで安定応答（DM or private channel）
2. 定時通知が想定時刻で届く
3. 記憶の確認/削除/保存抑止が運用できる
4. Docker backendで実行隔離できる
5. MCPを1つ接続し、必要ツールだけ露出できる

> 1〜5を満たしたら本命候補。満たさない場合はWindmill案を本命継続。

## 6. リスクと対策

### リスク

- 変化の速いプロジェクトに依存する
- 統合度が高く障害切り分けが難しい
- 自動学習/自動スキルで挙動が読みにくい場合がある

### 対策

- バージョン固定（PoC期間中）
- 監査ログ有効化
- 管理コマンド（記憶参照・削除）を先に整備
- 重要処理は明示承認フローに限定

## 7. この構成が向くケース

- とにかく早く使えるAI秘書を立ち上げたい
- ある程度のブラックボックスを受け入れられる
- 本番前提ではなく、まず実利用PoCを回して判断したい
