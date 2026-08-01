# Discord Presence Deployment Runbook — server-side Codex用

この文書は、稼働中のDiscord Hermes自身ではなく、**サーバー側のCodex CLI**が実行するための手順です。
Gateway再起動でDiscord Hermesが応答不能になっても、Codex CLIのshell sessionは維持し、そこで検証・rollbackまで完結させます。

## 0. 絶対条件

- 対象Hermes: `/opt/hermes` v0.18.2
- config: `/opt/data/config.yaml`
- plugin: `/opt/data/plugins/discord-presence`
- service: `/run/service/gateway-default`
- log: `/opt/data/logs/gateways/default/current`
- Hermes本体 `/opt/hermes` は編集しない。
- plugin production codeもdeployment中には編集しない。
- Codexはread-onlyの以下だけを使用する。
  - `account/rateLimits/read`
  - `account/usage/read`
- Codexの手動reset、reset credit消費、認証変更を行わない。
- configやlogの生内容、token、credential、raw Codex responseをchatへ貼らない。
- Gateway restartは本番反映で1回、rollback時に必要なら追加1回まで。
- preflightが1つでも失敗したらrestartしない。
- すべてのshell blockは`bash`で実行する。`sh`では実行しない（`source`と`printf %q`を使用するため）。

## 1. どこで死ぬか

| ポイント | 想定障害 | Discord Hermesへの影響 | Codexの対応 |
|---|---|---|---|
| config編集 | YAML破損・既存key上書き | **次回restart後にGatewayが起動不能**。編集直後は旧processが動く | restartせずbackupへ復元 |
| plugin enable | configへのenabled登録失敗 | restart前は影響なし | backupへ復元、終了 |
| plugin import/register | import error・Hermes API差異 | Gatewayは起動してもDiscord adapterが登録されない可能性 | 新規logを検査し即rollback |
| Discord adapter connect | `connect(is_reconnect)`等の互換性不良 | **GatewayはupでもDiscord Botだけoffline**になり得る | stable PIDだけで成功扱いせずlog検査、失敗ならrollback |
| disconnect/restart | cleanup timeout・子process残存 | restart timeoutまたは一時offline | s6 statusをpoll。30秒以内に安定しなければrollback |
| Codex usage取得 | OAuth切れ・CLI不在・API変更 | 原則Bot chatは生存し、`Codex利用量 取得待ち`へfallback | chatが正常なら非致命。後で原因調査 |
| Discord presence送信 | Discord API拒否・CustomActivity非表示 | 原則Bot chatは生存。presenceのみ失敗 | chat優先。繰り返しerrorならrollback |
| rollback | backup不正・復元後も起動不能 | **Discord Hermesがoffline継続** | server-side Codexがs6/logを追跡し、backupを保持して停止。盲目的な再restart loopは禁止 |

plugin側ではcancel時のCodex子process終了・待機queue起床・worker終了待ちを実装し単体/実process smoke済みだが、deployment時にも新規logとPID安定性を再確認する。

**本当に致命的なのは、config破損、plugin登録失敗、Discord adapter接続失敗、rollback失敗です。**
Codex取得失敗とpresence表示失敗は、設計上はBot chatを殺さないfailureです。

## 2. Codexへ渡す指示

```text
/opt/data/plugins/discord-presence/DEPLOYMENT-RUNBOOK.md を最初から最後まで読み、記載順に実行してください。
Hermes本体は変更禁止。configは必ずbackup後に変更。preflight失敗時はrestart禁止。
Gateway restart後にDiscord Hermesが応答不能でも、あなたのserver shellからs6 status・新規logを確認し、条件に該当すれば自律rollbackしてください。
秘密値・config全文・raw Codex responseは出力しないでください。
完了報告には、旧新PID、テスト件数、plugin status、rollback有無、server-side acceptance結果だけを書いてください。
```

## 3. Phase A — 現状固定とbackup

Codexの各terminal callは環境変数を引き継ぐとは限らない。Phase Aで非秘密のdeployment stateを保存し、**Phase B以降は各terminal callの先頭で必ずsourceする**。

```bash
set -euo pipefail

HERMES=/opt/hermes/.venv/bin/hermes
PY=/opt/hermes/.venv/bin/python3
CONFIG=/opt/data/config.yaml
PLUGIN=/opt/data/plugins/discord-presence
SERVICE=/run/service/gateway-default
LOG=/opt/data/logs/gateways/default/current
STATE=/opt/data/backups/discord-presence-current.env
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP=/opt/data/backups/discord-presence-$STAMP

mkdir -p -m 700 "$BACKUP"
cp -a "$CONFIG" "$BACKUP/config.yaml"
sha256sum "$CONFIG" > "$BACKUP/config.sha256"
stat -c '%a %U:%G' "$CONFIG" > "$BACKUP/config.metadata"
/command/s6-svstat "$SERVICE" > "$BACKUP/gateway-before.txt"
OLD_PID=$(/command/s6-svstat "$SERVICE" | sed -n 's/.*pid \([0-9][0-9]*\).*/\1/p')
test -n "$OLD_PID"
LOG_OFFSET=$(stat -c %s "$LOG")
printf '%s\n' "$LOG_OFFSET" > "$BACKUP/log-offset"
printf '%s\n' "$OLD_PID" > "$BACKUP/old-pid"

umask 077
{
  printf 'HERMES=%q\n' "$HERMES"
  printf 'PY=%q\n' "$PY"
  printf 'CONFIG=%q\n' "$CONFIG"
  printf 'PLUGIN=%q\n' "$PLUGIN"
  printf 'SERVICE=%q\n' "$SERVICE"
  printf 'LOG=%q\n' "$LOG"
  printf 'BACKUP=%q\n' "$BACKUP"
  printf 'OLD_PID=%q\n' "$OLD_PID"
  printf 'LOG_OFFSET=%q\n' "$LOG_OFFSET"
} > "$STATE"
```

backupにconfigの秘密値が含まれるので、`$BACKUP`のpathやchecksumは報告してよいが、内容は表示しない。
現在のconfig mode/ownerをそのまま保持する。2026-07-30時点では`0640 hermes:hermes`だが、固定値に決め打ちせずbackup metadataを正とする。

## 4. Phase B — restart前preflight

```bash
set -euo pipefail
source /opt/data/backups/discord-presence-current.env
cd "$PLUGIN"
"$PY" -m compileall -q .
"$PY" -m unittest discover -s tests -v
"$HERMES" plugins list | grep 'discord-presence'
/command/s6-svstat "$SERVICE"
```

期待値:

- unit tests: 30件以上、全件`OK`
- `discord-presence`: `not enabled`
- Gateway: `up`
- plugin sourceの本番Pythonに禁止語がない

```bash
set -euo pipefail
source /opt/data/backups/discord-presence-current.env
if grep -R -nE 'rateLimitResetCredit|discord\.Game|ActivityType\.playing|shell=True|os\.system\(|pickle\.load' \
  --include='*.py' "$PLUGIN"; then
  echo 'STOP: forbidden production pattern found' >&2
  exit 1
fi
```

実Codex read-only smoke。利用率値やraw responseは出力しない。

```bash
set -euo pipefail
source /opt/data/backups/discord-presence-current.env
cd /opt/hermes
"$PY" - <<'PY'
import importlib.util, sys, time
from pathlib import Path
sys.path.insert(0, '/opt/hermes')
r = Path('/opt/data/plugins/discord-presence')
s = importlib.util.spec_from_file_location(
    'deploy_smoke', r / '__init__.py', submodule_search_locations=[str(r)]
)
m = importlib.util.module_from_spec(s)
sys.modules[s.name] = m
s.loader.exec_module(m)
from deploy_smoke.collector import fetch_codex_snapshot
from deploy_smoke.presence_config import PresenceConfig
from deploy_smoke.renderer import render_presence, build_custom_activity
x = fetch_codex_snapshot(timeout=15)
text = render_presence(x, PresenceConfig(enabled=True))
payload = build_custom_activity(text).to_dict()
assert x.remaining_percent is None or 0 <= x.remaining_percent <= 100
assert payload['type'] == 4
assert len(text) <= 120
print('codex_read=ok custom_activity=type4 secret_output=none')
PY
```

ここまでで失敗したら、**configを変更せず終了**する。

## 5. Phase C — plugin enableとpresence config追加

まず公式CLIでpluginをenableする。tool override権限は与えない。

```bash
set -euo pipefail
source /opt/data/backups/discord-presence-current.env
"$HERMES" plugins enable --no-allow-tool-override discord-presence
```

次にpresence blockをatomicに追加する。既にtop-level `discord`が存在した場合は自動上書きせずSTOPする。

```bash
set -euo pipefail
source /opt/data/backups/discord-presence-current.env
CONFIG="$CONFIG" "$PY" - <<'PY'
import os
from pathlib import Path
import yaml

p = Path(os.environ['CONFIG'])
raw = p.read_text(encoding='utf-8')
cfg = yaml.safe_load(raw)
if not isinstance(cfg, dict):
    raise SystemExit('STOP: config root is not a mapping')
if 'discord' in cfg:
    raise SystemExit('STOP: top-level discord already exists; do not overwrite automatically')

block = '''

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
'''

st = p.stat()
tmp = p.with_name(p.name + '.discord-presence.tmp')
tmp.write_text(raw.rstrip() + block, encoding='utf-8')
yaml.safe_load(tmp.read_text(encoding='utf-8'))
os.chmod(tmp, st.st_mode & 0o7777)
os.chown(tmp, st.st_uid, st.st_gid)
os.replace(tmp, p)
PY
```

secretを表示せず、必要な状態だけ検証する。

```bash
set -euo pipefail
source /opt/data/backups/discord-presence-current.env
CONFIG="$CONFIG" "$PY" - <<'PY'
import os, yaml
with open(os.environ['CONFIG'], encoding='utf-8') as f:
    c = yaml.safe_load(f)
p = c.get('plugins', {})
assert 'discord-presence' in p.get('enabled', [])
assert p.get('entries', {}).get('discord-presence', {}).get('allow_tool_override') is False
d = c.get('discord', {}).get('presence', {})
assert d.get('enabled') is True
assert d.get('mode') == 'rate_limit'
assert d.get('timezone') == 'Asia/Tokyo'
print('config_semantics=ok plugin_enabled=true presence_enabled=true secrets_printed=false')
PY

"$HERMES" config check
"$HERMES" plugins list | grep 'discord-presence'
stat -c '%a %U:%G' "$CONFIG"
```

期待値:

- `discord-presence`: enabled
- config check: exit 0
- config mode/owner: backup前と同じ

このPhaseで失敗した場合、restartせずPhase Hの「restart前rollback」を実行する。

## 6. Phase D — restart直前の最終gate

```bash
set -euo pipefail
source /opt/data/backups/discord-presence-current.env
cd "$PLUGIN"
"$PY" -m compileall -q .
"$PY" -m unittest discover -s tests -v
/command/s6-svstat "$SERVICE"
```

以下が1つでも真ならSTOPしてrestart前rollback:

- tests失敗
- Gatewayが既にdown
- pluginがenabledでない
- config check失敗
- config owner/modeが変化
- backupが読めない

## 7. Phase E — Gatewayを1回だけrestart

```bash
set -euo pipefail
source /opt/data/backups/discord-presence-current.env
/command/s6-svc -r "$SERVICE"
```

30秒以内に、旧PIDと異なる`up`状態を確認する。

```bash
set -euo pipefail
source /opt/data/backups/discord-presence-current.env
NEW_PID=''
for _ in $(seq 1 30); do
  STATUS=$(/command/s6-svstat "$SERVICE" || true)
  PID=$(printf '%s\n' "$STATUS" | sed -n 's/.*pid \([0-9][0-9]*\).*/\1/p')
  if printf '%s' "$STATUS" | grep -q '^up ' && [ -n "$PID" ] && [ "$PID" != "$OLD_PID" ]; then
    NEW_PID=$PID
    break
  fi
  sleep 1
done

test -n "$NEW_PID" || { echo 'FAIL: gateway did not return with a new PID'; false; }
sleep 10
STABLE_PID=$(/command/s6-svstat "$SERVICE" | sed -n 's/.*pid \([0-9][0-9]*\).*/\1/p')
test "$STABLE_PID" = "$NEW_PID" || { echo 'FAIL: gateway PID is not stable'; false; }
printf '%s\n' "$NEW_PID" > "$BACKUP/new-pid"
```

このshellが失敗したら即Phase Hの「restart後rollback」へ進む。Discord Hermesへ質問してはいけない。offlineの可能性がある。

## 8. Phase F — 新規logだけ検査

restart前のbyte offset以降だけを抽出する。log rotationでfileが短くなった場合はcurrent全体を対象にする。

```bash
set -euo pipefail
source /opt/data/backups/discord-presence-current.env
LOG="$LOG" OFFSET="$LOG_OFFSET" OUT="$BACKUP/post-restart.log" "$PY" - <<'PY'
import os
from pathlib import Path
p = Path(os.environ['LOG'])
data = p.read_bytes()
offset = int(os.environ['OFFSET'])
new = data[offset:] if len(data) >= offset else data
Path(os.environ['OUT']).write_bytes(new)
print(f'post_restart_log_bytes={len(new)}')
PY
```

`post-restart.log`は秘密を含む可能性があるため、全文をchatへ貼らない。ローカルでのみ検索する。

```bash
set -euo pipefail
source /opt/data/backups/discord-presence-current.env
if grep -Eiq \
  'Failed to load plugin.*discord-presence|Traceback|ModuleNotFoundError|ImportError|unexpected keyword argument.*is_reconnect|Task exception was never retrieved|discord.*connect.*(fail|error)|presence.*(fail|error)' \
  "$BACKUP/post-restart.log"; then
  echo 'FAIL: fatal pattern in new gateway log' >&2
  false
fi

/command/s6-svstat "$SERVICE"
"$HERMES" plugins list | grep 'discord-presence'
```

grep結果にもcredentialらしき値があれば外部へ貼らず`[REDACTED]`にする。

## 9. Phase G — acceptance

server-side Codexが確認できるもの:

- Gatewayが新PIDで10秒以上stable
- pluginがenabled
- 新規logにimport/connect/task/presence errorなし
- read-only Codex smoke成功
- unit tests成功
- config ownership/mode保持

Discord外部クライアントなしでは完全確認できないもの:

- メンバー一覧で本当に`Playing`なしのCustom Statusとして見えるか
- Discord上の通常メッセージにBotが応答するか

Gatewayの`change_presence()`には表示反映のACKがないため、server-side検証だけでUI反映を捏造してはいけない。上記2点は「server側異常なし・外部UI確認待ち」と明記する。

## 10. Phase H — rollback

### restart前rollback

Gatewayは旧processのままなのでrestartしない。backup configをatomicに戻す。

```bash
set -euo pipefail
source /opt/data/backups/discord-presence-current.env
cp -a "$BACKUP/config.yaml" "$CONFIG.rollback"
mv -f "$CONFIG.rollback" "$CONFIG"
sha256sum -c "$BACKUP/config.sha256"
/command/s6-svstat "$SERVICE"
```

### restart後rollback

configが壊れているとHermes CLI自身が使えない可能性があるため、`hermes plugins disable`には依存しない。backupファイルを直接atomic restoreする。

```bash
set -euo pipefail
source /opt/data/backups/discord-presence-current.env
cp -a "$BACKUP/config.yaml" "$CONFIG.rollback"
mv -f "$CONFIG.rollback" "$CONFIG"
sha256sum -c "$BACKUP/config.sha256"
/command/s6-svc -r "$SERVICE"

ROLLBACK_PID=''
for _ in $(seq 1 30); do
  STATUS=$(/command/s6-svstat "$SERVICE" || true)
  PID=$(printf '%s\n' "$STATUS" | sed -n 's/.*pid \([0-9][0-9]*\).*/\1/p')
  if printf '%s' "$STATUS" | grep -q '^up ' && [ -n "$PID" ]; then
    ROLLBACK_PID=$PID
    break
  fi
  sleep 1
done

test -n "$ROLLBACK_PID"
sleep 10
test "$ROLLBACK_PID" = "$(/command/s6-svstat "$SERVICE" | sed -n 's/.*pid \([0-9][0-9]*\).*/\1/p')"
```

rollback後も起動しない場合:

- 追加restartを繰り返さない。
- backup、post-restart log、s6 statusを保持。
- config全文やsecretを表示せず、server管理者へ`Gateway rollback failed`と報告。
- plugin directoryは削除しない。backup configではpluginがenabledでないためロードされない。

## 11. 最終報告format

```text
Deployment: SUCCESS / ROLLED BACK / BLOCKED BEFORE RESTART
Old PID: <pid>
New PID: <pid or none>
Gateway stable: yes/no
Unit tests: <N> passed
Plugin status: enabled/not enabled
Codex read smoke: ok/failed
New fatal log patterns: none/found
Config metadata preserved: yes/no
Rollback performed: yes/no
Discord UI/chat: externally verified / external verification unavailable
Secrets printed: no
```
