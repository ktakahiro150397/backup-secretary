# Discord Codex Usage Presence

Hermesの既存Discord adapterを継承し、Discord BotのCustom ActivityへCodex利用量を表示するuser pluginです。

```text
Codex残量 73%｜次回リセット 07/30 18:00
```

`discord.CustomActivity`（Gateway activity type 4）を使うため、`Playing`等の接頭辞は付きません。

## 現在の導入状態

このdirectoryが存在するだけではpluginは動きません。Hermes user pluginはopt-in方式です。

```text
Plugin files: installed for development
plugins.enabled: not changed
Discord presence config: not changed
Gateway restart: not performed
Live Discord update: not performed
```

`hermes plugins list`では`discord-presence / not enabled`と表示されるのが、導入前の正常状態です。

## 安全設計

- Hermes本体 `/opt/hermes` を編集しません。
- 既存Discord adapterをsubclass化し、元の登録metadataと機能を再利用します。
- `discord-auto-thread-recovery` pluginが先に適用されていても、そのclassを継承して両機能を維持します。
- Codex app-serverの読み取り専用methodだけを呼びます。
  - `account/rateLimits/read`
  - `account/usage/read`
- reset creditの消費、認証変更、thread作成等は行いません。
- credential、account ID、plan、balance、raw responseを表示・log出力しません。
- 更新間隔は最低60秒、default 300秒です。
- 同じ文言はDiscordへ再送しません。
- Codex取得失敗時もDiscord chat機能を停止しません。
- 一時失敗時は前回値を維持し、default 15分後にfallback表示へ移行します。
- disconnect/reconnect時はCodex app-serverをterminateし、待機中JSON-RPC queueを起床してworker終了まで待ちます。
- Presence停止と既存Discord adapterのcleanupは並行開始し、Gatewayの5秒disconnect budgetを妨げません。

## ファイル

```text
discord-presence/
├── plugin.yaml
├── __init__.py
├── plugin_entry.py
├── adapter.py
├── collector.py
├── presence_config.py
├── renderer.py
├── README.md
└── tests/
```

## 設定

初回導入時に、`/opt/data/config.yaml`へ次を追加します。**現在はまだ追加しません。**

```yaml
discord:
  presence:
    enabled: true
    mode: rate_limit
    template: "Codex残量 {remaining_percent}%｜次回リセット {reset_time_jst}"
    bucket_id: codex
    refresh_seconds: 300
    stale_after_seconds: 900
    fallback_text: "Codex利用量 取得待ち"
    timezone: Asia/Tokyo
    max_length: 120
```

さらにpluginをenableします。

```bash
/opt/hermes/.venv/bin/hermes plugins enable discord-presence
```

このcommandは`config.yaml`を変更するため、承認済みのメンテナンス時だけ実行します。

### mode

| mode | 内容 |
|---|---|
| `rate_limit` | Codex rate limitの使用率・残量・reset時刻 |
| `daily_tokens` | account usageの最新daily bucket |
| `combined` | templateで利用率とdaily tokensを併記 |
| `static` | Codex APIを呼ばず`static_text`を表示 |

### template placeholders

```text
{remaining_percent}
{used_percent}
{reset_time_jst}
{window_minutes}
{latest_date}
{latest_tokens}
{latest_tokens_short}
```

`{reset_time_jst}`は`MM/DD HH:MM`形式です。週次枠のresetが翌日以降でも、
日付を落とさず表示します。

上記以外のplaceholder、attribute access、format conversionは拒否されます。

例:

```yaml
# 残量だけ
template: "Codex残量 {remaining_percent}%"

# 最新daily tokenも表示
mode: combined
template: "Codex {remaining_percent}%｜{latest_date} {latest_tokens_short} tok"

# API切り分け用
mode: static
static_text: "Hermes ready"
```

### Hot reload

controllerは各更新周期でconfigを読み直します。以下はGateway再起動なしで次tickに反映されます。

- `enabled`
- `mode`
- `template`
- `bucket_id`
- `refresh_seconds`
- `stale_after_seconds`
- `fallback_text`
- `timezone`
- `max_length`
- `static_text`

Python code、plugin enable/disable、plugin追加・削除にはGateway再起動が必要です。

## 開発テスト

外部package追加なしで、HermesのPythonから全unit testsを実行できます。

```bash
cd /opt/data/plugins/discord-presence
/opt/hermes/.venv/bin/python3 -m unittest discover -s tests -v
```

検証範囲:

- config default・clamp・hot reload
- rate limit bucket選択
- percentage境界値
- daily bucket選択
- error messageのsecret非露出
- JST変換
- token短縮
- template allowlist
- Custom Activity type 4 payload
- 文字数上限
- 重複更新抑止
- stale fallback
- Discord update再試行
- enable/disable
- task start/stop/reconnect
- 進行中Codex取得のcancel、worker join、子process終了
- Hermes v0.18.2の`connect(is_reconnect=...)`契約
- 既存adapterとの継承合成
- plugin registration idempotency

## 導入前preflight

設定変更・再起動前に以下をすべて通します。

```bash
# 1. Unit tests
cd /opt/data/plugins/discord-presence
/opt/hermes/.venv/bin/python3 -m unittest discover -s tests -v

# 2. Syntax/import check
/opt/hermes/.venv/bin/python3 -m compileall -q .

# 3. Manifest discovery（まだnot enabledであること）
/opt/hermes/.venv/bin/hermes plugins list

# 4. Gateway status
/command/s6-svstat /run/service/gateway-default
```

Codex live smokeは読み取り専用methodだけで実施します。現在の利用率値自体はlogへ出さず、範囲・render・activity typeだけを検証します。

## 初回導入手順

この節は、設定変更と夜間再起動の明示承認後だけ実行します。

1. 現在のGateway PIDとstatusを保存。
2. `/opt/data/config.yaml`をmode 600でtimestamp付きbackup。
3. 上記`discord.presence` blockを追加。
4. `hermes plugins enable discord-presence`を実行。
5. `hermes plugins list`でenabledを確認。
6. 全unit tests、syntax、registration、Codex read smokeを再実行。
7. config差分を確認し、token・secretが出力されないようにする。
8. 再起動直前にもう一度承認を得る。
9. Gatewayを一回だけrestart。

現在のs6環境でのrestart候補:

```bash
/command/s6-svc -r /run/service/gateway-default
```

実行時にはservice pathを再確認し、環境が変わっていたら盲目的に使いません。

## 再起動後のacceptance test

1. `/command/s6-svstat /run/service/gateway-default`が`up`。
2. Gateway PIDが新しくなっている。
3. logにplugin import error、task exception、Discord connection errorがない。
4. Discord Botが通常メッセージへ応答する。
5. Bot profile/member listに`Playing`なしのプレーンテキストが出る。
6. 5分後もpresence taskが1本で、同一文言を無駄に再送しない。
7. `template`を一時変更し、再起動なしで次tickに反映される。
8. 本番templateへ戻し、再反映を確認する。

Discordクライアント側の表示はGateway payloadだけでは完全保証できないため、最終acceptanceには目視確認を含めます。

## Troubleshooting

### `Codex利用量 取得待ち`

- Codex OAuth状態を確認。
- `codex` CLIがGatewayのPATHで実行可能か確認。
- read method schemaが現在のCodex CLIに存在するか確認。
- raw credentialやraw responseをlogへ貼らない。

### presenceが表示されない

- `hermes plugins list`でplugin enabledを確認。
- `discord.presence.enabled: true`を確認。
- Gateway restart後のimport errorを確認。
- `mode: static`でDiscord update経路だけを切り分ける。

### 通常のDiscord応答に影響がある

presenceよりBot chatを優先し、直ちにrollbackします。

## Rollback

まずhot reloadでpresenceだけ停止できます。

```yaml
discord:
  presence:
    enabled: false
```

通常応答に影響がある場合:

1. `hermes plugins disable discord-presence`
2. backupした`config.yaml`を復元
3. 夜間枠内でGatewayを一回restart
4. Discord接続・通常応答を確認

plugin directoryは原因調査が終わるまで削除しません。

## Hermes/Codex update後の互換性確認

- bundled Discord adapterにasync `connect()` / `disconnect()`と`_client`がある。
- `upstream.DiscordAdapter`のsubclass化が可能。
- discord.pyに`CustomActivity`がある。
- Codex app-serverに2つのread methodがある。
- 全unit testsとreal registration smokeが通る。

一つでも失敗した場合はpluginをdisabledのままにし、Gatewayを再起動しません。
