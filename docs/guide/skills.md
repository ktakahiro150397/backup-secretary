# リポジトリ管理の Hermes Skills

このリポジトリでは、カスタム Hermes skill を管理し、Hermes のランタイム skills ディレクトリへ同期できる。

## 構成

```text
skills/
  productivity/
    write-and-forget-capture/
      SKILL.md
      scripts/
        waf.py
```

ランタイムの同期先：

```text
/opt/data/skills/
```

Docker Compose 構成では、ホストの `runtime/hermes-data` がコンテナ内の `/opt/data` にマップされている。

## 同期方法

専用の Compose profile を使う：

```bash
docker compose --profile skills-sync run --rm --build skills-sync
```

これはリポジトリ管理の skills を `/managed-skills/` から `/opt/data/skills/` へ `rsync -a` でコピーする。
既存の skills ディレクトリを上書きするのではなく、マージする。

## なぜ `/opt/data/skills` へのバインドマウントは避けるか

`./skills` を直接 `/opt/data/skills` にマウントしないでください。
そうすると、Hermes 既存の skills やインストール/生成済みの skills が見えなくなります。

安全なパターン：

1. リポジトリ管理の skills を `/managed-skills` に読み取り専用でマウントする
2. `/opt/data/skills` へコピー/マージする

## 安全上の注意

- skill に secret を含めない
- ランタイム DB は Git 管理しない
- skill のソースとドキュメントだけを追跡し、個人データは管理しない
- skill の変更を commit する前に secret スキャンを実施する

## 実行ポリシー

このリポジトリのカスタム skill は、`guide/skill-execution-policy.md` の **Skill 実行方針** に従う：

> **Hermes 組み込みツール / MCP ツールを最優先。CLI 直打ちは最終手段。**

skill が外部サービスにアクセスする場合、Hermes の組み込みツールや MCP サーバーを優先して使う。日本語文字、改行、引用符を CLI 引数として渡す `terminal` ベースの shell wrapper は避ける。Hermes の実行前セキュリティスキャナに引っかかり、承認プロンプトが出て自動実行が止まるからだ。

カスタム skill を作成またはリファクタリングする前に、完全なポリシーを一度読んでおくこと。
