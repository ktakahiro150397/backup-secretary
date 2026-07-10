# Architecture

このブランチ (`rework/runtime-openviking`) の構成図です。

- 個人用常駐インスタンス: `hermes-main`
- 身内向け常駐インスタンス: `hermes-owashota`
- 個人用長期コンテキスト共有: `OpenViking`
- Git同期: 設定・skills・knowledge・運用スクリプト
- 非同期: `state.db` / `sessions/` / `logs/` / `memories/` / secrets

## 全体構成

```mermaid
flowchart LR
    GH[GitHub / backup-secretary repo]

    subgraph SERVER[自宅サーバーPC]
        RepoS[backup-secretary clone]
        subgraph Docker[Docker Compose]
            HM[hermes-main<br/>個人用 Discord gateway]
            HO[hermes-owashota<br/>身内向け Discord gateway]
            OV[OpenViking<br/>長期memory]
            SX[SearXNG]
            RD[Redis]
        end

        RTS[runtime/main/hermes-data]
        RTO[runtime/owashota/hermes-data]
        ROV[runtime/openviking]
    end

    subgraph MAINPC[メインPC / WSL]
        RepoW[backup-secretary clone]
        HC[scripts/hcoder<br/>Hermes CLI起動]
        PCD[backup-secretary-data/pc/coder/hermes-data]
    end

    GH <--> RepoS
    GH <--> RepoW

    RepoS --> HM
    RepoS --> HO
    RepoS --> SX

    RTS <--> HM
    RTO <--> HO
    ROV <--> OV

    HM <--> OV
    HC <--> OV

    RepoW --> HC
    PCD <--> HC

    HM --> SX
    HO --> SX
    SX --> RD
```

## 同期モデル

```mermaid
flowchart TD
    A[Gitで同期するもの] --> A1[SOUL.md]
    A --> A2[config.yaml]
    A --> A3[skills/]
    A --> A4[knowledge/]
    A --> A5[compose.yaml]
    A --> A6[scripts/]
    A --> A7[docs/]

    B[OpenVikingで共有するもの] --> B1[個人用の長期コンテキスト]
    B --> B2[過去会話から抽出された記憶]
    B --> B3[main と coder 間で共有したい文脈]

    C[同期しないもの] --> C1[.env]
    C --> C2[state.db]
    C --> C3[sessions/]
    C --> C4[logs/]
    C --> C5[memories/]
    C --> C6[auth.json]
```

## WSL から使うときの流れ

```mermaid
sequenceDiagram
    participant U as User
    participant W as WSL / scripts/hcoder
    participant G as GitHub
    participant O as OpenViking

    U->>W: hcoder 実行
    W->>G: git pull --ff-only
    W->>W: skills/ をローカル runtime に同期
    W->>O: OpenViking接続
    W->>W: hermes chat 起動
```

## サーバー反映フロー

```mermaid
sequenceDiagram
    participant U as User
    participant W as メインPC / WSL
    participant G as GitHub
    participant S as 自宅サーバー
    participant H as Hermes containers

    U->>W: 設定やskillsを変更
    W->>W: git commit
    W->>G: git push

    U->>S: hupdate または hdeploy
    S->>G: git pull --ff-only
    S->>S: skills-sync
    alt skills / knowledge だけ変更
        S-->>H: 再起動なし
    else config / SOUL / compose 変更あり
        S->>H: restart
    end
```

## 補足

- `hermes-main` は `OpenViking` を使って、サーバーPCとメインPCの間で長期コンテキストを共有する。
- `hermes-owashota` は個人用コンテキストと混ぜない。必要なら別の account / user / agent で完全分離する。
- 直近のチャットセッションそのものは同期しない。共有するのは長期コンテキストだけ。
