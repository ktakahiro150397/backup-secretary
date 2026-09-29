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
