---
name: github-issues
description: Create, manage, triage, and close GitHub issues. Search existing issues, add labels, assign people, and link to PRs. Works with gh CLI or falls back to git + GitHub REST API via curl.
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [GitHub, Issues, Project-Management, Bug-Tracking, Triage]
    related_skills: [github-auth, github-pr-workflow]
---

# GitHub Issues Management

Create, search, triage, and manage GitHub issues. Each section shows `gh` first, then the `curl` fallback.

## Prerequisites

- Authenticated with GitHub (see `github-auth` skill)
- Inside a git repo with a GitHub remote, or specify the repo explicitly

### Setup

```bash
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  if [ -z "$GITHUB_TOKEN" ]; then
    if [ -f ~/.hermes/.env ] && grep -q "^GITHUB_TOKEN=" ~/.hermes/.env; then
      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2 | tr -d '\n\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
    fi
  fi
fi

REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
```

---

## 1. Viewing Issues

**With gh:**

```bash
gh issue list
gh issue list --state open --label "bug"
gh issue list --assignee @me
gh issue list --search "authentication error" --state all
gh issue view 42
```

If `gh issue view` fails with a GraphQL Projects/classic-projects deprecation error such as `repository.issue.projectCards`, avoid the `gh issue view` code path and read the issue via REST instead:

```bash
gh api repos/OWNER/REPO/issues/42 --jq '{number,title,state,body,labels:[.labels[].name],html_url}'
gh api repos/OWNER/REPO/issues/42/comments --paginate \
  --jq '.[] | "COMMENT by \(.user.login) at \(.created_at):\n\(.body)\n---"'
```

This is common in repos that still have legacy Projects metadata attached; `gh issue comment`, REST reads, and normal issue state updates may still work.

**With curl:**

```bash
# List open issues
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/issues?state=open&per_page=20" \
  | python3 -c "
import sys, json
for i in json.load(sys.stdin):
    if 'pull_request' not in i:  # GitHub API returns PRs in /issues too
        labels = ', '.join(l['name'] for l in i['labels'])
        print(f\"#{i['number']:5}  {i['state']:6}  {labels:30}  {i['title']}\")"

# Filter by label
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/issues?state=open&labels=bug&per_page=20" \
  | python3 -c "
import sys, json
for i in json.load(sys.stdin):
    if 'pull_request' not in i:
        print(f\"#{i['number']}  {i['title']}\")"

# View a specific issue
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues/42 \
  | python3 -c "
import sys, json
i = json.load(sys.stdin)
labels = ', '.join(l['name'] for l in i['labels'])
assignees = ', '.join(a['login'] for a in i['assignees'])
print(f\"#{i['number']}: {i['title']}\")
print(f\"State: {i['state']}  Labels: {labels}  Assignees: {assignees}\")
print(f\"Author: {i['user']['login']}  Created: {i['created_at']}\")
print(f\"\n{i['body']}\")"

# Search issues
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/search/issues?q=authentication+error+repo:$OWNER/$REPO" \
  | python3 -c "
import sys, json
for i in json.load(sys.stdin)['items']:
    print(f\"#{i['number']}  {i['state']:6}  {i['title']}\")"
```

## 2. Creating Issues

**With gh:**

```bash
gh issue create \
  --title "Login redirect ignores ?next= parameter" \
  --body "## Description
After logging in, users always land on /dashboard.

## Steps to Reproduce
1. Navigate to /settings while logged out
2. Get redirected to /login?next=/settings
3. Log in
4. Actual: redirected to /dashboard (should go to /settings)

## Expected Behavior
Respect the ?next= query parameter." \
  --label "bug,backend" \
  --assignee "username"
```

**With curl:**

```bash
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues \
  -d '{
    "title": "Login redirect ignores ?next= parameter",
    "body": "## Description\nAfter logging in, users always land on /dashboard.\n\n## Steps to Reproduce\n1. Navigate to /settings while logged out\n2. Get redirected to /login?next=/settings\n3. Log in\n4. Actual: redirected to /dashboard\n\n## Expected Behavior\nRespect the ?next= query parameter.",
    "labels": ["bug", "backend"],
    "assignees": ["username"]
  }'
```

### Bug Report Template

```
## Bug Description
<What's happening>

## Steps to Reproduce
1. <step>
2. <step>

## Expected Behavior
<What should happen>

## Actual Behavior
<What actually happens>

## Environment
- OS: <os>
- Version: <version>
```

### Feature Request Template

```
## Feature Description
<What you want>

## Motivation
<Why this would be useful>

## Proposed Solution
<How it could work>

## Alternatives Considered
<Other approaches>
```

## 3. Managing Issues

### Add/Remove Labels

For project backlogs, prefer a small orthogonal taxonomy instead of one-off labels:

- `area:*` — product/system area, e.g. `area:gateway`, `area:memory`, `area:google`, `area:security`, `area:delegation`.
- `kind:*` — work type, e.g. `kind:integration`, `kind:infra`, `kind:ux`, `kind:research`.
- `priority:*` — execution priority: `priority:high`, `priority:medium`, `priority:low`.

Create or update labels idempotently before applying them:

```bash
gh label create "area:gateway" --repo "$OWNER_REPO" --color 1D76DB --description "Messaging Gateway / delivery" --force
gh label create "kind:infra" --repo "$OWNER_REPO" --color 0052CC --description "基盤・運用・設定" --force
gh label create "priority:high" --repo "$OWNER_REPO" --color B60205 --description "優先度高め" --force
```

**With gh:**

```bash
gh issue edit 42 --add-label "priority:high,bug"
gh issue edit 42 --remove-label "needs-triage"
```

**With curl:**

```bash
# Add labels
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues/42/labels \
  -d '{"labels": ["priority:high", "bug"]}'

# Remove a label
curl -s -X DELETE \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues/42/labels/needs-triage

# List available labels in the repo
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/labels \
  | python3 -c "
import sys, json
for l in json.load(sys.stdin):
    print(f\"  {l['name']:30}  {l.get('description', '')}\")"
```

### Assignment

**With gh:**

```bash
gh issue edit 42 --add-assignee username
gh issue edit 42 --add-assignee @me
```

**With curl:**

```bash
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues/42/assignees \
  -d '{"assignees": ["username"]}'
```

### Commenting

**With gh:**

```bash
gh issue comment 42 --body "Investigated — root cause is in auth middleware. Working on a fix."
```

**With curl:**

```bash
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues/42/comments \
  -d '{"body": "Investigated — root cause is in auth middleware. Working on a fix."}'
```

### Closing and Reopening

Before closing an issue, leave a resolution comment unless the issue is an obvious duplicate/spam/clerical cleanup. This preserves the decision trail for future agents and humans.

Recommended closing comment shape:

```markdown
## 解決方針
<What approach was chosen and why>

## 実施した流れ
1. <Step performed>
2. <Step performed>

## 結果
<Concrete verification result, links, commands, or observed behavior>

## 現時点の設定 / 状態
<Final config/state if relevant>

## 補足
<Pitfalls, naming differences, follow-up notes>

## クローズ理由
<Why this is complete or not planned>
```

Use a body file for multiline comments, then close:

```bash
gh issue comment 42 --body-file /tmp/issue-42-resolution.md
gh issue close 42 --reason completed
```

**With gh:**

```bash
gh issue close 42
gh issue close 42 --reason "not planned"
gh issue reopen 42
```

**With curl:**

```bash
# Close
curl -s -X PATCH \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues/42 \
  -d '{"state": "closed", "state_reason": "completed"}'

# Reopen
curl -s -X PATCH \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues/42 \
  -d '{"state": "open"}'
```

### Linking Issues to PRs

Issues are automatically closed when a PR merges with the right keywords in the body:

```
Closes #42
Fixes #42
Resolves #42
```

To create a branch from an issue:

**With gh:**

```bash
gh issue develop 42 --checkout
```

**With git (manual equivalent):**

```bash
git checkout main && git pull origin main
git checkout -b fix/issue-42-login-redirect
```

## 4. Issue Triage Workflow

When asked to triage issues:

1. **List untriaged issues:**

```bash
# With gh
gh issue list --label "needs-triage" --state open

# With curl
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/issues?labels=needs-triage&state=open" \
  | python3 -c "
import sys, json
for i in json.load(sys.stdin):
    if 'pull_request' not in i:
        print(f\"#{i['number']}  {i['title']}\")"
```

2. **Read and categorize** each issue (view details, understand the bug/feature)

3. **Apply labels and priority** (see Managing Issues above)

4. **Assign** if the owner is clear

5. **Comment with triage notes** if needed

## 5. Bulk Operations

For batch operations, combine API calls with shell scripting.

### Creating issues from an external source URL

Use this when the user drops a URL, post, article, release note, or screenshot and says they want it captured as an issue (e.g. “これissueに”, “これやりたい”, “あとで検証”).

Workflow:

1. Retrieve enough source content to understand the idea. For X/Twitter, prefer `xurl` when installed/authenticated; otherwise use safe public metadata mirrors such as `api.fxtwitter.com/<user>/status/<id>` or `api.vxtwitter.com/<user>/status/<id>` for read-only extraction. Do not read `~/.xurl` or expose tokens.
2. Summarize the source in the issue body instead of pasting a raw dump. Include the original URL under `Source:`.
3. Search existing open/all issues for the feature/tool name plus generic terms before creating, and skip/merge duplicates.
4. Preserve the user's preferred language for the issue title/body. If the source is English but the user works in Japanese, write the issue in Japanese unless asked otherwise.
5. Convert hype into concrete investigation/implementation work: background, goal, risks, acceptance criteria, and security/privacy checks where relevant.
6. Use `--body-file` for multiline issue bodies.
7. Apply orthogonal labels (`area:*`, `kind:*`, `priority:*`) and create missing labels idempotently only when the area is likely reusable.
8. Verify the created issue with `gh issue view` and return the URL.

Security note: observability, agent tracing, browser/session recording, or plugin issues should explicitly include secret-redaction/read-only checks before any production install. Agent trace tooling is useful, but secret leaks are how you turn “nice dashboard” into a small house fire.

### Bulk creation from a backlog

Use this when a user asks to turn a saved backlog, planning document, TODO list, or issue candidates into GitHub issues.

Checklist before creating:

1. Read the backlog/source document completely enough to understand scope.
2. Confirm explicit user approval for actual GitHub issue creation. If the user only says something ambiguous like "issueね", ask whether they want drafts or real GitHub issues.
3. List existing issues first and skip duplicates or already-resolved items.
4. Preserve the user's preferred language in both titles and bodies. If the backlog is English but the user normally works in Japanese, create/update issues in Japanese unless they asked otherwise.
5. Use `--body-file` with temp Markdown files for multiline bodies; avoid fragile shell quoting.
6. Add a source note in each issue body, e.g. `Source: path/to/backlog.md`.
7. Verify created/updated issues with `gh issue list` or `gh issue view`.
8. If the source backlog is durable, update it with the created issue numbers/URLs so the same backlog is not re-filed later.

**With gh:**

```bash
# Close all issues with a specific label
gh issue list --label "wontfix" --json number --jq '.[].number' | \
  xargs -I {} gh issue close {} --reason "not planned"
```

**With curl:**

```bash
# List issue numbers with a label, then close each
curl -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/issues?labels=wontfix&state=open" \
  | python3 -c "import sys,json; [print(i['number']) for i in json.load(sys.stdin)]" \
  | while read num; do
    curl -s -X PATCH \
      -H "Authorization: token $GITHUB_TOKEN" \
      https://api.github.com/repos/$OWNER/$REPO/issues/$num \
      -d '{"state": "closed", "state_reason": "not_planned"}'
    echo "Closed #$num"
  done
```

## Quick Reference Table

| Action | gh | curl endpoint |
|--------|-----|--------------|
| List issues | `gh issue list` | `GET /repos/{o}/{r}/issues` |
| View issue | `gh issue view N` | `GET /repos/{o}/{r}/issues/N` |
| Create issue | `gh issue create ...` | `POST /repos/{o}/{r}/issues` |
| Add labels | `gh issue edit N --add-label ...` | `POST /repos/{o}/{r}/issues/N/labels` |
| Assign | `gh issue edit N --add-assignee ...` | `POST /repos/{o}/{r}/issues/N/assignees` |
| Comment | `gh issue comment N --body ...` | `POST /repos/{o}/{r}/issues/N/comments` |
| Close | `gh issue close N` | `PATCH /repos/{o}/{r}/issues/N` |
| Search | `gh issue list --search "..."` | `GET /search/issues?q=...` |
