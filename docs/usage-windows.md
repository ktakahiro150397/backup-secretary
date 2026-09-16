# Discord別usageをWindowsへ送る

2026-09-16のWindows集約・非公開方針用のopt-in計装。既存のhermes-otel 0.11.0（`0180c5e63b9d035ee0754d9a0d75c3499a8def26`）とprivacy/sender patchを拡張する。代替pluginの全面新作ではない。旧shared/root集計とは経路と正本が異なり、今回の新データを旧routerへfan-outしない。

## 何を数えるか

- `pre_llm_call` のnative turn IDでgateway ContextVarsをsnapshotする。process-wide `os.environ`、prompt内の申告、session作成者、再利用agentの古いsenderを参照しない。
- Discord user/channel/thread、Hermes session/turn/requestを別属性で保持する。Discord adapterがthread channel IDをchat_idに入れる場合、chat_type=threadからthreadを識別する。通常channel/DMはthreadなし。
- request開始時にsnapshotを固定し、retryも同じ発起人へ帰属。native `api_request_id` で上流pluginのtask-key衝突を避け、各attemptのspan IDをdedup単位にする。
- delegate開始時の親snapshotをchild sessionへ引き継ぐ。親sessionの次の発言者で上書きしない。未知はunattributed、自律cron/self-improvementはsystem。
- 送信するのは `gen_ai.request` / `usage.contract=hermes.request.v1` だけ。root/turn/session累計は送信しない。子requestは子自身のusageだけを数える。
- inputはCanonicalUsageのprompt_tokens（cacheを含む）、outputはreasoningを含む。total=input+output、内数を再加算しない。未知は欠如、既知0は0。失敗にusageがあれば保持し、なければmissing。

実機Hermes 0.20.5、source `fcbd1076a93841fa88855acce810e342a5b78101` のgatewayはContextVarsを `copy_context()` でworker threadへ渡す。main/owashotaの主モデル経路は `openai-codex` providerの直接呼出し。両profileで非機密の実requestをWindowsまで確認済み。外部 `codex exec` はインストールされているが日常利用の有無は未確定。terminalからの外部CLIやhookを通らない補助LLMのusageを取得済みとは扱わない。現在の対応をその経路へ推測で拡張しない。

## Privacyと停止耐性

`HERMES_OTEL_USAGE_ONLY=true` でhook adapterとUsageProcessorを有効にする。BatchSpanProcessorより前に、新しいReadableSpanをallowlistから作る。本文、response、history、tool引数/結果、raw error、events、links、parent、trace state、不要なresource/scopeはqueueへ渡さない。model/providerは必要metadataとして保持する。実ID・alias表・telemetryはGit管理しない。

設定はmain/owashota-windows.yaml。tracesのみ、logs/metrics無効、SDK queue256、batch64、1秒間隔、HTTP timeout3秒。session-end同期flushはしない。Windows停止時はpeerのforwarderが永続queueへ保留する。SDK queue/forwarderの容量超過、disk故障、7日retry期限、producerがspanを完了する前の終了について無欠測は保証しない。

session-rootの既存10分sweepで長いAPI spanが先に終了してusageを失う問題を避け、requestをroot寿命から分離する。未完了requestは4,096件/24時間を上限とし、unknown/missingとして終了させる。遅い終端hookで同じattemptを再加算しない。turn/child/retiredのsnapshotも有界。上限を超えた長期処理は正確なtoken数を保証せず、品質を不明にする。

## Imageと適用

mainのDockerfileにはbuild-time installerを追加した。新しい実機Hermesを古いmain imageへ戻さないため、現行imageに薄いlayerを重ねる `docker/hermes/Dockerfile.usage` も用意する。実機のimage ID、code version、既存dirty configを確認し、固定local tagとIDの一致を検証してからbuildする。raw local image IDはDockerのFROMに使えない。

```sh
docker build -f docker/hermes/Dockerfile.usage \
  --build-arg HERMES_RUNTIME_IMAGE=VERIFIED_FIXED_LOCAL_BASE_TAG \
  -t backup-secretary/hermes-agent:usage-REVIEWED docker/hermes
bash scripts/test-hermes-usage-image.sh TESTED_IMAGE_ID
```

installerはreview済みanchorを検査し、違うplugin treeでは失敗する。稼働container内にplugin codeをインストールしない。pinやsource互換性を変えたらimage testを再実施する。

peerのforwarderは同じHermes Docker networkで `usage-forwarder` として解決する。host firewallに穴を追加せず、Windows ownerのSSH Unix socket経由で送る。

```sh
python3 scripts/prepare-usage-runtime.py \
  --compose /PRIVATE/RUNTIME/compose.yaml \
  --image TESTED_IMMUTABLE_IMAGE_ID \
  --output /PRIVATE/ai-usage/hermes --apply
```

実機main service名の既定はhermes-main（main branchでは `--main-service hermes`）。既存Composeをメモリ内で比較し、image、usage環境変数、plugin config mount以外の差分を拒否する。config/SOULのhashも照合する。別private overlayに記録し、元Compose・model/provider・認証・data mountsを変更しない。active_agentsが0でないgatewayは止めずに失敗する。独立したidle側だけを適用するには `--only hermes-main` を使い、残りはidle後に適用する。

起動後はimage ID、health、gateway state、private endpoint、Windowsへの到達を確認する。通常のcontainer再起動はoverlay設定を保持するが、base Composeだけの `up` は旧image/configへ戻し得るため、以後の運用でこのoverlayを必ず含める。

安全な切戻しはpluginの専用runtime configで `enabled: false` として旧imageを指定し、同じdata mountsで再作成する。旧router/sharedへ送る旧configを無条件に復元しない。base imageとdataは保持し、DBや会話履歴は削除しない。

## 検証結果と本人確認

- 実機imageのplugin loaderと9試験: 2人×2thread・同sessionの並行turn、親の次turn後のdelegate、retry/失敗/未取得、resume/channel/system、環境変数の誤継承防止、2時間request、早期error・報告usage、state上限、trace-state canary除去。
- Windows側の実Collector/PG試験: 303/707 tokenで合計1,010、replay/逆順、root除外、NULL、秘密文字列がexport/queue/DB/診断/UI queryへ残らないこと、満杯拒否、backup/restore。
- 両profileの非機密provider requestがreportedとして到達。CLI検証はunattributed、実際のcron requestはsystemになった。Discordユーザーを捏造して試験しない。
- 実SSH断中もprovider requestが完了し、server queueに保留。forwarderを再起動してqueueを保持し、SSH復旧後にdrainを確認。Windows stackのstop/start後もledgerを保持した。

残る本人操作は、利用者へのmetadata計測の周知、2人×2threadの非機密Discord試行、画面での帰属確認。依頼文例は「使用量計測の確認です。短くOKと返してください」。同じthreadへ別人からも1回ずつ送り、owner画面でuser/threadを絞る。実IDや本文をPR・チャットへ報告せず、期待どおりかと試行時刻だけ返す。現在のowner試行未確認を合成試験で代用して完了にはしない。
