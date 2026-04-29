---
name: google-workspace
description: Gmail, Calendar, Tasks, Drive, Contacts, Sheets, and Docs integration for Hermes. Uses Hermes-managed OAuth2 setup, prefers the Google Workspace CLI (`gws`) when available, and falls back to the Python client libraries otherwise.
version: 1.0.0
author: Nous Research
license: MIT
metadata:
  hermes:
    tags: [Google, Gmail, Calendar, Tasks, Drive, Sheets, Docs, Contacts, Email, OAuth]
    homepage: https://github.com/NousResearch/hermes-agent
    related_skills: [himalaya]
---

# Google Workspace

Gmail, Calendar, Drive, Contacts, Sheets, and Docs — through Hermes-managed OAuth and a thin CLI wrapper. When `gws` is installed, the skill uses it as the execution backend for broader Google Workspace coverage; otherwise it falls back to the bundled Python client implementation.

## References

- `references/gmail-search-syntax.md` — Gmail search operators (is:unread, from:, newer_than:, etc.)

## Scripts

- `scripts/setup.py` — OAuth2 setup (run once to authorize)
- `scripts/google_api.py` — compatibility wrapper CLI. It prefers `gws` for operations when available, while preserving Hermes' existing JSON output contract.

## First-Time Setup

The setup is fully non-interactive — you drive it step by step so it works
on CLI, Telegram, Discord, or any platform.

Define a shorthand first:

```bash
GSETUP="python ${HERMES_HOME:-$HOME/.hermes}/skills/productivity/google-workspace/scripts/setup.py"
```

### Step 0: Check if already set up

```bash
$GSETUP --check
```

If it prints `AUTHENTICATED`, skip to Usage — setup is already done.

### Step 1: Triage — ask the user what they need

Before starting OAuth setup, ask the user TWO questions:

**Question 1: "What Google services do you need? Just email, or also
Calendar/Drive/Sheets/Docs?"**

- **Email only** → They don't need this skill at all. Use the `himalaya` skill
  instead — it works with a Gmail App Password (Settings → Security → App
  Passwords) and takes 2 minutes to set up. No Google Cloud project needed.
  Load the himalaya skill and follow its setup instructions.

- **Email + Calendar** → Continue with this skill, but use
  `--services email,calendar` during auth so the consent screen only asks for
  the scopes they actually need.

- **Calendar/Drive/Sheets/Docs only** → Continue with this skill and use a
  narrower `--services` set like `calendar,drive,sheets,docs`.

- **Full Workspace access** → Continue with this skill and use the default
  `all` service set.

**Question 2: "Does your Google account use Advanced Protection (hardware
security keys required to sign in)? If you're not sure, you probably don't
— it's something you would have explicitly enrolled in."**

- **No / Not sure** → Normal setup. Continue below.
- **Yes** → Their Workspace admin must add the OAuth client ID to the org's
  allowed apps list before Step 4 will work. Let them know upfront.

### Step 2: Create OAuth credentials (one-time, ~5 minutes)

Tell the user:

> You need a Google Cloud OAuth client. This is a one-time setup:
>
> 1. Create or select a project:
>    https://console.cloud.google.com/projectselector2/home/dashboard
> 2. Enable the required APIs from the API Library:
>    https://console.cloud.google.com/apis/library
    Enable: Gmail API, Google Calendar API, Google Tasks API, Google Drive API,
    Google Sheets API, Google Docs API, People API
> 3. Create the OAuth client here:
>    https://console.cloud.google.com/apis/credentials
>    Credentials → Create Credentials → OAuth 2.0 Client ID
> 4. Application type: "Desktop app" → Create
> 5. If the app is still in Testing, add the user's Google account as a test user here:
>    https://console.cloud.google.com/auth/audience
>    Audience → Test users → Add users
> 6. Download the JSON file and tell me the file path
>
> Important Hermes CLI note: if the file path starts with `/`, do NOT send only the bare path as its own message in the CLI, because it can be mistaken for a slash command. Send it in a sentence instead, like:
> `The JSON file path is: /home/user/Downloads/client_secret_....json`

Once they provide the path:

```bash
$GSETUP --client-secret /path/to/client_secret.json
```

If they paste the raw client ID / client secret values instead of a file path,
write a valid Desktop OAuth JSON file for them yourself, save it somewhere
explicit (for example `~/Downloads/hermes-google-client-secret.json`), then run
`--client-secret` against that file.

### Step 3: Get authorization URL

Current bundled `setup.py` does **not** accept `--services` or `--format`; it prints a plain URL and requests the full `SCOPES` list in the script. If the user wants narrower access, have them deselect unwanted scopes on the Google consent screen (or update the script first to support service sets).

```bash
$GSETUP --auth-url
```

This prints the authorization URL directly and stores a pending PKCE OAuth session at
`~/.hermes/google_oauth_pending.json`.

Agent rules for this step:
- Send the printed URL to the user as a single line.
- Tell the user that the browser will likely fail on `http://localhost:1` after approval, and that this is expected.
- Tell them to copy the ENTIRE redirected URL from the browser address bar, including `state`, `code`, and `scope` parameters.
- If the user gets `Error 403: access_denied`, send them directly to `https://console.cloud.google.com/auth/audience` to add themselves as a test user.

### Step 4: Exchange the code

The user will paste back either a URL like `http://localhost:1/?code=4/0A...&scope=...`
or just the code string. Either works. The `--auth-url` step stores a temporary
pending OAuth session locally so `--auth-code` can complete the PKCE exchange
later, even on headless systems:

```bash
$GSETUP --auth-code "THE_URL_OR_CODE_THE_USER_PASTED"
```

If the user intentionally removed write scopes on the consent screen, `--auth-code` may warn about missing scopes but still save a usable partial token. Treat `AUTHENTICATED (partial)` as success for the granted services, then smoke-test only those services.

### Step 5: Verify

```bash
$GSETUP --check
```

Should print `AUTHENTICATED`. Setup is complete — token refreshes automatically from now on.

### Notes

- Token is stored at `~/.hermes/google_token.json` and auto-refreshes.
- Pending OAuth session state/verifier are stored temporarily at `~/.hermes/google_oauth_pending.json` until exchange completes.
- If `gws` is installed, `google_api.py` points it at the same `~/.hermes/google_token.json` credentials file. Users do not need to run a separate `gws auth login` flow.
- To revoke: `$GSETUP --revoke`

## Usage

All commands go through the API script. Set `GAPI` as a shorthand:

```bash
GAPI="python ${HERMES_HOME:-$HOME/.hermes}/skills/productivity/google-workspace/scripts/google_api.py"
```

### Gmail

```bash
# Search (returns JSON array with id, from, subject, date, snippet)
$GAPI gmail search "is:unread" --max 10
$GAPI gmail search "from:boss@company.com newer_than:1d"
$GAPI gmail search "has:attachment filename:pdf newer_than:7d"

# Read full message (returns JSON with body text)
$GAPI gmail get MESSAGE_ID

# Send
$GAPI gmail send --to user@example.com --subject "Hello" --body "Message text"
$GAPI gmail send --to user@example.com --subject "Report" --body "<h1>Q4</h1><p>Details...</p>" --html
$GAPI gmail send --to user@example.com --subject "Hello" --from '"Research Agent" <user@example.com>' --body "Message text"

# Reply (automatically threads and sets In-Reply-To)
$GAPI gmail reply MESSAGE_ID --body "Thanks, that works for me."
$GAPI gmail reply MESSAGE_ID --from '"Support Bot" <user@example.com>' --body "Thanks"

# Labels
$GAPI gmail labels
$GAPI gmail modify MESSAGE_ID --add-labels LABEL_ID
$GAPI gmail modify MESSAGE_ID --remove-labels UNREAD
```

### Calendar

```bash
# List events (defaults to next 7 days)
$GAPI calendar list
$GAPI calendar list --start 2026-03-01T00:00:00Z --end 2026-03-07T23:59:59Z

# Create event (ISO 8601 with timezone required)
$GAPI calendar create --summary "Team Standup" --start 2026-03-01T10:00:00-06:00 --end 2026-03-01T10:30:00-06:00
$GAPI calendar create --summary "Lunch" --start 2026-03-01T12:00:00Z --end 2026-03-01T13:00:00Z --location "Cafe"
$GAPI calendar create --summary "Review" --start 2026-03-01T14:00:00Z --end 2026-03-01T15:00:00Z --attendees "alice@co.com,bob@co.com"
$GAPI calendar create --summary "Focus block" --start 2026-03-01T16:00:00+09:00 --end 2026-03-01T17:00:00+09:00 --description "Created by Hermes"

# Delete event
$GAPI calendar delete EVENT_ID
```

### Google Tasks

Requires both the Google Tasks API enabled in the OAuth client's Cloud project and an OAuth token granted this scope:

```text
https://www.googleapis.com/auth/tasks
```

If `tasks.googleapis.com` returns `Request had insufficient authentication scopes`, the API is reachable but the saved token lacks the Tasks scope. Add the scope to `setup.py`'s `SCOPES`, revoke/reauth if needed, and complete the OAuth flow again before testing task operations. `Access Not Configured` means the Cloud project API switch is still off.

```bash
# List task lists
$GAPI tasks lists --max 20

# List tasks from the default task list
$GAPI tasks list --tasklist @default --max 20
$GAPI tasks list --show-completed --show-hidden

# Create / complete / delete tasks
$GAPI tasks create --title "Buy milk" --notes "low fat" --due 2026-04-30
$GAPI tasks complete TASK_ID --tasklist @default
$GAPI tasks delete TASK_ID --tasklist @default
```

Notes:
- Use `tasks lists` first if the user has multiple task lists and did not specify which one.
- `--due` accepts `YYYY-MM-DD` or RFC3339 datetime, but Google Tasks API v1 returns `due` as a date-like midnight UTC value (for example `2026-04-30T00:00:00.000Z`). Even when the Google Tasks app lets the user set a reminder time like 12:05, `tasks().get()` and `tasks().list()` do not expose that time in the public API response. Treat task due times as not reliably readable/writable via this API; use Calendar/reminders if exact time matters.

### Drive

```bash
$GAPI drive search "quarterly report" --max 10
$GAPI drive search "mimeType='application/pdf'" --raw-query --max 5
```

### Contacts

```bash
$GAPI contacts list --max 20
```

### Sheets

```bash
# Read
$GAPI sheets get SHEET_ID "Sheet1!A1:D10"

# Write
$GAPI sheets update SHEET_ID "Sheet1!A1:B2" --values '[["Name","Score"],["Alice","95"]]'

# Append rows
$GAPI sheets append SHEET_ID "Sheet1!A:C" --values '[["new","row","data"]]'
```

### Docs

```bash
$GAPI docs get DOC_ID
```

## Output Format

All commands return JSON. Parse with `jq` or read directly. Key fields:

- **Gmail search**: `[{id, threadId, from, to, subject, date, snippet, labels}]`
- **Gmail get**: `{id, threadId, from, to, subject, date, labels, body}`
- **Gmail send/reply**: `{status: "sent", id, threadId}`
- **Calendar list**: `[{id, summary, start, end, location, description, htmlLink}]`
- **Calendar create**: `{status: "created", id, summary, htmlLink}`
- **Tasks lists**: `[{id, title, updated}]`
- **Tasks list**: `[{id, title, notes, status, due, completed, updated, parent, position}]`
- **Tasks create**: `{status: "created", id, title, notes, due, ...}`
- **Tasks complete**: `{status: "completed", id, title, completed, ...}`
- **Tasks delete**: `{status: "deleted", taskId}`
- **Drive search**: `[{id, name, mimeType, modifiedTime, webViewLink}]`
- **Contacts list**: `[{name, emails: [...], phones: [...]}]`
- **Sheets get**: `[[cell, cell, ...], ...]`

## Rules

1. **Never send email or create/delete events without confirming with the user first.** Show the draft content and ask for approval.
2. **Check auth before first use** — run `setup.py --check`. If it fails, guide the user through setup.
3. **Use the Gmail search syntax reference** for complex queries — load it with `skill_view("google-workspace", file_path="references/gmail-search-syntax.md")`.
4. **Calendar times must include timezone** — always use ISO 8601 with offset (e.g., `2026-03-01T10:00:00-06:00`) or UTC (`Z`).
5. **For automated Calendar entries, use `--description` for provenance/context when appropriate** — e.g. `Created by Hermes` or a short note explaining why the event was added. This helps users distinguish assistant-created blocks from manually-created events.
6. **Respect rate limits** — avoid rapid-fire sequential API calls. Batch reads when possible.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `NOT_AUTHENTICATED` | Run setup Steps 2-5 above |
| `REFRESH_FAILED` | Token revoked or expired — redo Steps 3-5 |
| `HttpError 403: Insufficient Permission` | Missing API scope — `$GSETUP --revoke` then redo Steps 3-5. For Google Tasks specifically, confirm the token includes `https://www.googleapis.com/auth/tasks`. |
| `HttpError 403: Access Not Configured` | API not enabled in the OAuth client's Google Cloud project. Open the API Library for that project and enable the relevant APIs (for example Gmail API, Google Calendar API, Google Drive API, Google Docs API, Google Sheets API), then wait a few minutes and retry. This is different from OAuth scope failure: auth can be valid while the project API switch is still off. |
| `ModuleNotFoundError` | Run `$GSETUP --install-deps`. If the environment has no `pip`/`ensurepip` but has `uv`, install deps into a target dir and set `PYTHONPATH`: `uv pip install --target ${HERMES_HOME:-$HOME/.hermes}/.local/google-workspace-deps google-api-python-client google-auth-oauthlib google-auth-httplib2`, then run commands as `PYTHONPATH=${HERMES_HOME:-$HOME/.hermes}/.local/google-workspace-deps $GSETUP --check`. |
| `TOKEN_CORRUPT: Authorized user info was not in the expected format, missing fields refresh_token, client_secret, client_id` | Inspect `google_token.json` without printing secrets. If top-level keys are `installed` or `web`, the user placed the OAuth client secret JSON where the authorized user token belongs. Move/use that file with `$GSETUP --client-secret /path/to/client_secret.json`, then run `--auth-url` and `--auth-code` to generate the real `google_token.json`. |
| Advanced Protection blocks auth | Workspace admin must allowlist the OAuth client ID |

## Revoking Access

```bash
$GSETUP --revoke
```
