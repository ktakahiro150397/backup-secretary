# Skill Execution Policy（Skill実行方針）

## 結論

カスタム Skill から外部サービスやデータストアにアクセスする際、**Hermes 組み込みツール / MCP ツールを最優先** する。`terminal` 経由の CLI 直打ちは最終手段とし、必要な場合はユーザー確認を介す。

---

## 背景：なぜ CLI 直打ちを避けるか

Hermes の `terminal` ツールには、コマンド実行前のセキュリティスキャン（Tirith / dangerous-pattern detection）がある。次のようなシェル文字列がフラグされると、**Command Approval Required** プロンプトが出て自動実行が止まる。

- `python -c "..."` （`-e/-c flag`でのスクリプト実行）
- `cmd | python -c "..."` （pipe-to-interpreter）
- 長い日本語文字列、改行、埋め込み引用符を含むコマンド
- Heredoc、複数行の shell スクリプト

これは **Hermes 標準 Skill でも発生する**。`terminal` 経由で shell 文字列を投げるときに、内容がスキャナに刺さるかどうかで決まる。

> - ❌「Hermes 標準 Skill なら承認プロンプトは出ない」
> - ❌「CLI だから必ず承認プロンプトが出る」
> - ✅「`terminal` 経由で shell command 文字列を投げ、内容が Tirith / dangerous pattern に刺さると出る」
> - ✅「標準 Skill でも `terminal` で CLI wrapper を叩けば出る」
> - ✅「`web_search` / `web_extract` / native tool / MCP tool / structured tool call なら、基本この terminal pre-exec approval 経路を踏まない」

---

## 置き換えの優先順位

| 優先度 | 方法 | 理由 |
|---|---|---|
| 1 | **Hermes 組み込みツール / MCP ツール** | shell 文字列を経由さない。structured arguments の HTTP/JSON 呼び出し。 |
| 2 | **MCP サーバー化 / Hermes native tool 化** | 自前で実装し、Hermes に登録する。内部で CLI を使っても、Hermes 側からは tool call で見える。 |
| 3 | **短期 CLI ワークアラウンド** | 避けられないときは `shell=False`、stdin/JSON 入力、timeout、non-interactive を徹底する。 |
| 4 | 生の CLI 直打ち | **基本禁止**。`| interpreter`、`python -c`、heredoc は絶対に使わない。 |

---

## MCP 採用時の前提条件

- 信頼できるソース（公式または自前構築）
- Structured arguments のみ（shell 文字列の組み立てなし）
- 内部 CLI 使用時: `shell=False`、引数配列、stdin/JSON、timeout、non-interactive
- 読み取り専用と更新専用のツールを明確に区別
- シークレット、OAuth token、セッション記録をログに出さない

---

## 新規 Skill 作成時のチェックリスト

- [ ] 外部サービスへのアクセスが必要か？
- [ ] Hermes 組み込みツール / MCP ツールで覆えるか？
- [ ] ない場合、MCP サーバー / native tool として実装できるか？
- [ ] CLI が必要なら、`shell=False` + stdin/JSON + timeout + non-interactive の使用を検討
- [ ] 日本語・改行・引用符を含む入力で動作確認を実施
- [ ] Skill の `SKILL.md` に本ポリシーへの参照を記載

---

## 現行 Skill に対する適用

本リポジトリ管理下のカスタム Skill は、それぞれ以下の方針で置き換えを進める。

| Skill | 現状 | 方針 |
|---|---|---|
| `web-research-agents` | `subprocess.run(["hermes", "chat", ...])` で直打ち | MCP ツール化または `delegate_task` に置き換え |
| `write-and-forget-capture` | `python3 scripts/waf.py capture "..."` の argparse CLI | Hermes native tool 化（SQLiteを直接操作する tool を作成） |
| `obsidian-diary-git` | `python3 scripts/obsidian_diary.py save "..."` の argparse CLI | Hermes native tool 化（`save_diary`/`status` tool として登録） |

Hermes 標準 Skill は本ポリシーの対象外。リポジトリ管理下の追加 Skill のみがターゲットとする。
