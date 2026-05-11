# OpenCLI Integration

Hermes から [OpenCLI](https://github.com/jackwener/OpenCLI) を使い、CDP（Chrome DevTools Protocol）経由でブラウザを操作できるようにする。

## 概要

- **OpenCLI**: Webサイトや Electron アプリを CLI 化するツール。AI エージェントが `opencli browser` コマンドでページ操作・情報抽出できる。
- **Chrome コンテナ**: CDP ポート 9222 を公開する headless Chromium を常時起動。ログイン状態はプロファイルボリュームで永続化。
- **接続**: Hermes コンテナ内から `OPENCLI_CDP_ENDPOINT=http://chrome:9222` でアクセス。

## 初回セットアップ

### 1. イメージのビルド

```bash
docker compose build chrome hermes
```

### 2. Chrome コンテナを起動

```bash
docker compose up -d chrome
```

起動後、以下で CDP が応答することを確認：

```bash
curl http://127.0.0.1:9222/json/version
```

### 3. 読み取り専用アカウントでログイン

Chrome のプロファイルは `./runtime/chrome-profile` に永続化される。ログイン状態を注入するには、一時的に Chrome を GUI モードで起動するか、手動で cookies / localStorage を配置する。

**最もシンプルな方法**: Chrome コンテナに `exec` して `chromium` を `--no-headless` で立ち上げ（サーバー上で `DISPLAY` が必要）、各サイトに読み取り専用のサブアカウントでログインする。

```bash
# 一時的に GUI ありで起動（サーバーに X11 転送が必要な場合）
docker compose exec chrome bash
chromium --user-data-dir=/data/chrome-profile --no-sandbox
```

もしくは、ローカル PC の Chrome で同じ `--user-data-dir` 相当のプロファイルを作成し、そのディレクトリを `runtime/chrome-profile` にコピーする。

### 4. Hermes から接続確認

```bash
docker compose run --rm cli bash
opencli doctor
opencli list
```

## 運用フロー

### 定期的な情報取得（cronjob 連携例）

```bash
# Hermes コンテナ内で実行
OPENCLI_CDP_ENDPOINT=http://chrome:9222 opencli x tweets --user <handle> --limit 10
```

取得結果は JSON またはテキストでパースし、Discord 等に通知できる。

### エージェント経由のブラウザ操作

Hermes スキルや `terminal` から以下のようなコマンドを実行可能：

```bash
# サイトアダプタ経由
opencli bilibili hot --limit 5
opencli hackernews top --limit 5

# 生のブラウザ操作（AI エージェント向け）
opencli browser navigate "https://x.com/<user>"
opencli browser extract --selector "article"
```

## セキュリティ・注意事項

| 項目 | 内容 |
|---|---|
| **読み取り専用アカウント** | メインアカウントとは切り分け、BAN リスクを最小化する。 |
| `--no-sandbox` | Docker コンテナ内での実行に必要だが、悪意あるページは回避。 |
| `--remote-allow-origins='*'` | CDP 接続を許可するために必要。ローカルネットワーク内（hermes-net）に閉じているため、外部に露出しないよう `CHROME_CDP_BIND=127.0.0.1` を維持すること。 |
| **ToS 遵守** | Discord / WeChat / X 等の利用規約に自動化ツールの使用制限がある場合がある。各自の責任で運用すること。 |
| **リソース** | Chrome は 1GB〜消費する。`CHROME_MEMORY_LIMIT` で適切に制限する。 |

## トラブルシューティング

### `opencli doctor` が失敗する

1. Chrome コンテナが起動しているか確認：
   ```bash
   docker compose ps chrome
   ```
2. CDP エンドポイントに到達できるか確認：
   ```bash
   docker compose exec hermes curl -s http://chrome:9222/json/version
   ```

### サイトがヘッドレスを検出してブロックする

Chrome コンテナの `CMD` に追加のフラグを渡すか、`docker compose exec` で手動起動する。ステルス性が必要な場合は [browserless/chromium](https://github.com/browserless/browserless) 等の置き換えを検討。

### 日本語フォントが豆腐になる

`docker/chrome/Dockerfile` に `fonts-noto-cjk` を含めている。サイトによって追加フォントが必要な場合は Dockerfile に追記し再ビルド。
