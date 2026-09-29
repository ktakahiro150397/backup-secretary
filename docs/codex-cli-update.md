# HermesコンテナのCodex CLIだけを更新する

通常buildは`docker/hermes/Dockerfile`の`CODEX_VERSION`でversionを固定する。
既存の観測用patchを含む実行imageへCLI更新だけを重ねる場合は、
`Dockerfile.codex`へimage IDを照合済みのlocal tagを明示する。稼働containerを
`docker commit`せず、秘密を含まない元imageからbuildする。

```bash
docker build -f docker/hermes/Dockerfile.codex \
  --build-arg HERMES_RUNTIME_IMAGE=<verified-local-image-tag> \
  --build-arg CODEX_VERSION=0.159.0 \
  -t backup-secretary/hermes-agent:codex-0.159.0 docker/hermes
docker run --rm --entrypoint codex backup-secretary/hermes-agent:codex-0.159.0 --version
```

実行中containerのCompose labelsから実際の設定file列を取得する。
追加overrideがimage IDを固定している場合は、そのfileをprivateな場所へ退避し、
対象Hermes servicesのimageだけを新image IDへ変更する。
`docker compose config --quiet`、新imageのCLI versionとHermes importを確認し、
同じCompose file列で対象serviceだけ`up -d --no-deps --no-build`する。
他service、認証、モデル、利用量計測設定はそのまま維持する。

更新後は両containerの`codex --version`、image ID、health、gatewayの
Discord接続と新規errorを確認する。問題があれば退避したoverrideを戻し、
同じ対象serviceだけ再作成する。元imageは復旧完了まで保持する。

Discord presence pluginはHermesの`agent.account_usage`を使用し、
Codex CLIを起動しない。CLI更新だけで残量表示が変わるとは限らない。
`remaining_percent`は残量であり、使用率100%なら表示は0%になる。
`primary_window`が週単位の場合もあるため、Sessionという内部labelだけで
5時間枠と判断せず、APIの`limit_window_seconds`も照合する。
診断時は割合・reset・モデル利用可否だけを抽出し、認証値やaccount識別子を出力しない。

2026-09-30のCLI更新は既存`usage-20260916` imageを基準に実施する。
このtagが指すimage IDと実行中containerの`.Image`をbuild前に照合する。
DockerfileのFROMへ裸の`sha256:<image-id>`を渡すとregistry名として解釈されるため、
local tagまたは`repository@sha256:<manifest-digest>`を使用する。

## Codex残量がアプリと一致しない場合

Hermes v0.20.5 (`fcbd1076`) のusage resolverはpool token利用時に
`ChatGPT-Account-Id`を省略していた。2026-09-30の比較では同じtoken・URLで
headerだけを追加すると使用率100%から52%、Astra利用不可から利用可能へ変化し、
Codexアプリと一致した。headerなしのHTTP 200だけでquota枯渇と判断しない。

`hermes-codex-usage-account.patch`は使用中tokenのaccount claimを読み、
明示token・native resolver・pool fallbackすべてで同じaccount headerを付ける。
別credentialのsingleton accountを混用せず、refresh失敗時の挙動は保持する。
tokenの真正性検証は引き続きbackendが行う。秘密や実account IDはpatchへ含めない。

Dockerfile2種ともpatchの適用可否と6件の回帰testをbuild時に確認する。
基準は未patchのHermes v0.20.5 image。将来のHermes更新で適用不可なら、
patchを強制適用せずupstream実装とtestを照合する。復旧は前述の旧imageへの切戻し。
実機確認は両profileのusage API、presence collector、gateway接続で行い、
Discord外部UIの確認と区別する。
