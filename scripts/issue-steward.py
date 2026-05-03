#!/usr/bin/env python3
"""
Issue Steward — backup-secretary の open issue を巡回して、
Steward 未対応・確認待ちの issue を検出する。
"""
import json, os, urllib.request, datetime

REPO = "ktakahiro150397/backup-secretary"
NOW = datetime.datetime.now(datetime.timezone.utc)
STEWARD_MARKERS = ("🔍 Issue Steward", "⚡ Issue Steward", "🏷️ Issue Steward")


def fetch(url: str):
    req = urllib.request.Request(url)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fmt_date(iso: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))


def get_comments(issue_number: int):
    """指定 issue のコメント一覧を取得（古い順）"""
    return fetch(
        f"https://api.github.com/repos/{REPO}/issues/{issue_number}/comments?per_page=100"
    )


def classify_issue(issue):
    """issue を分類してタプル (needs_action, waiting_review, unlabeled) を返す """
    is_pr = "pull_request" in issue
    labels = [l["name"] for l in issue.get("labels", [])]
    number = issue["number"]

    # ラベル未設定チェック
    has_category = any(l.startswith(("area:", "kind:", "priority:")) for l in labels)
    is_unlabeled = not has_category and not is_pr

    comments = get_comments(number)
    if not comments:
        # コメントゼロ = Steward 未対応
        return (True, False, is_unlabeled)

    # 最後のコメントが誰のものか
    last = comments[-1]
    last_body = last.get("body", "")
    last_user = last.get("user", {}).get("login", "")
    is_steward_last = last_body.startswith(STEWARD_MARKERS)
    is_bot = last_user in ("github-actions[bot]", "dependabot[bot]")

    # 確認待ち: 最後が Steward で、その後ユーザーが返信していない
    waiting_review = is_steward_last and not is_bot

    # 対応要: Steward コメントが一切ない
    has_steward = any(
        c.get("body", "").startswith(STEWARD_MARKERS) for c in comments
    )
    needs_action = not has_steward

    return (needs_action, waiting_review, is_unlabeled)


def main():
    issues = fetch(
        f"https://api.github.com/repos/{REPO}/issues?state=open&sort=updated&direction=desc&per_page=50"
    )

    needs_action = []      # Steward 未対応（調査対象）
    waiting_review = []    # Steward コメント済み、ユーザー確認待ち
    unlabeled = []         # ラベル未設定

    for i in issues:
        if "pull_request" in i:
            continue  # PR は Steward 対象外

        na, wr, ul = classify_issue(i)
        if na:
            needs_action.append(i)
        if wr:
            waiting_review.append(i)
        if ul:
            unlabeled.append(i)

    # ===== レポート出力 =====
    print(f"### Issue Steward ダイジェスト（{NOW.strftime('%Y-%m-%d %H:%M UTC')}）\n")
    print(f"📊 **Open Issues**: {len([i for i in issues if 'pull_request' not in i])}件\n")

    if needs_action:
        print(f"**🔍 Steward 未対応（{len(needs_action)}件）**")
        for i in needs_action:
            labels = ", ".join(l["name"] for l in i.get("labels", [])) or "(ラベルなし)"
            print(f"- #{i['number']}: {i['title']} [{labels}]")
        print()

    if waiting_review:
        print(f"**⏳ 確認待ち（{len(waiting_review)}件）**")
        for i in waiting_review:
            labels = ", ".join(l["name"] for l in i.get("labels", [])) or "(ラベルなし)"
            print(f"- #{i['number']}: {i['title']} [{labels}]")
        print()

    if unlabeled:
        print(f"**🏷️ ラベル未設定（{len(unlabeled)}件）**")
        for i in unlabeled:
            print(f"- #{i['number']}: {i['title']}")
        print()

    # JSON 形式でも出力（後続プロセス用）
    result = {
        "needs_action": [{"number": i["number"], "title": i["title"], "labels": [l["name"] for l in i.get("labels", [])]} for i in needs_action],
        "waiting_review": [{"number": i["number"], "title": i["title"], "labels": [l["name"] for l in i.get("labels", [])]} for i in waiting_review],
        "unlabeled": [{"number": i["number"], "title": i["title"]} for i in unlabeled],
    }
    print("---JSON---")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
