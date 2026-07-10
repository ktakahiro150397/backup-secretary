# Rework チェックリスト

このチェックリストは `rework/runtime-openviking` ブランチの受け入れ確認用です。

## 1. リポジトリ構成

- [ ] `compose.yaml` に `hermes-main` / `hermes-owashota` / `openviking` だけが定義されている
- [ ] SearXNG / Redis / skills / knowledge / Obsidian / 既存memory関連が含まれていない
- [ ] ドキュメントが日本語で整理されている
- [ ] root `.env` と各Hermes直下 `.env` の役割が分離されている

## 2. envファイル

- [ ] `.env` を `.env.example` から作成した
- [ ] `runtime/main/hermes-data/.env` を `.env.example` から作成した
- [ ] `runtime/owashota/hermes-data/.env` を `.env.example` から作成した
- [ ] root `.env` に秘密情報が入っていない
- [ ] `hermes-main` と `hermes-owashota` で OpenViking の account / user / agent / API key が分かれている

## 3. Docker起動

- [ ] `docker compose config` が成功する
- [ ] `openviking` が起動する
- [ ] `hermes-main` が起動する
- [ ] `hermes-owashota` が起動する
- [ ] 3コンテナが同一Docker network上で名前解決できる

## 4. OpenViking

- [ ] `openviking-server init` が完了する
- [ ] `openviking-server doctor` が成功する
- [ ] `http://127.0.0.1:1933/health` が成功する
- [ ] `ov.conf` に `server.root_api_key` が設定されている
- [ ] `runtime/openviking` にデータが永続化される

## 5. Hermes初期設定

### hermes-main

- [ ] `make setup-main` が完了する
- [ ] `runtime/main/hermes-data/config.yaml` が読み込まれる
- [ ] `runtime/main/hermes-data/SOUL.md` が読み込まれる
- [ ] Discord / LLM provider の設定が有効になる
- [ ] OpenVikingへ接続できる

### hermes-owashota

- [ ] `make setup-owashota` が完了する
- [ ] `runtime/owashota/hermes-data/config.yaml` が読み込まれる
- [ ] `runtime/owashota/hermes-data/SOUL.md` が読み込まれる
- [ ] Discord / LLM provider の設定が有効になる
- [ ] OpenVikingへ接続できる

## 6. CLI認証の永続化

### hermes-main

- [ ] コンテナ内で必要なCLI認証を実行する
- [ ] OpenCode認証が必要な場合、コンテナ内でloginを完了する
- [ ] 認証情報が `runtime/main/hermes-data` 配下に保存される
- [ ] `docker compose restart hermes-main` 後も認証が維持される
- [ ] `docker compose down` → `up` 後も認証が維持される

### hermes-owashota

- [ ] コンテナ内で必要なCLI認証を実行する
- [ ] OpenCode認証が必要な場合、コンテナ内でloginを完了する
- [ ] 認証情報が `runtime/owashota/hermes-data` 配下に保存される
- [ ] `docker compose restart hermes-owashota` 後も認証が維持される
- [ ] `docker compose down` → `up` 後も認証が維持される

## 7. インスタンス分離

- [ ] `hermes-main` と `hermes-owashota` の runtime data dir が別である
- [ ] 片方の `config.yaml` 変更がもう片方に影響しない
- [ ] 片方の `SOUL.md` 変更がもう片方に影響しない
- [ ] 片方のCLI認証情報がもう片方から見えない
- [ ] 片方のDiscord tokenがもう片方から見えない

## 8. OpenViking memory分離

- [ ] `hermes-main` からテスト記憶を保存できる
- [ ] `hermes-main` からその記憶を検索できる
- [ ] `hermes-owashota` から `hermes-main` のテスト記憶を取得できない
- [ ] `hermes-owashota` から別のテスト記憶を保存できる
- [ ] `hermes-main` から `hermes-owashota` のテスト記憶を取得できない
- [ ] API keyを入れ替えた場合にアクセスが拒否される、または想定外namespaceへアクセスできない

## 9. Git管理対象

Gitで管理するもの:

- [ ] `compose.yaml`
- [ ] `.env.example`
- [ ] `runtime/main/hermes-data/.env.example`
- [ ] `runtime/owashota/hermes-data/.env.example`
- [ ] 各インスタンスの `config.yaml`
- [ ] 各インスタンスの `SOUL.md`
- [ ] `docs/`

Gitで管理しないもの:

- [ ] 実際の `.env`
- [ ] `auth.json` などの認証情報
- [ ] `state.db*`
- [ ] `sessions/`
- [ ] `logs/`
- [ ] `memories/`
- [ ] `runtime/openviking` の実データ

## 10. メインPC確認

リポジトリの実装スコープ外だが、最終確認として実施する。

- [ ] メインPCでHermesをローカル起動できる
- [ ] メインPCのHermesから自宅サーバーのOpenVikingへ接続できる
- [ ] `hermes-main` と同じnamespaceで長期コンテキストを参照できる
- [ ] メインPCから追加した記憶を `hermes-main` から参照できる

## 11. 完了条件

- [ ] Hermesの2インスタンスが同時に安定稼働する
- [ ] runtime / 認証 / 設定がインスタンスごとに分離されている
- [ ] 両方のHermesがOpenVikingへ接続できる
- [ ] OpenViking上の記憶がインスタンス間で混ざらない
- [ ] 再起動・再作成後も必要な認証とデータが維持される
- [ ] envファイルの役割をドキュメントだけで判断できる

## 今回のスコープ外

今回は実施しない。

- [ ] SearXNGの導入
- [ ] 検索プロバイダの追加
- [ ] skillsの移行
- [ ] knowledgeの移行
- [ ] 既存memoryのOpenVikingへの投入
- [ ] OpenVikingの検索・抽出チューニング
- [ ] メインPC用起動スクリプトの整備
- [ ] CI/CD
- [ ] 自動デプロイ
