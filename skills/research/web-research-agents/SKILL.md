---
name: web-research-agents
description: Use when delegating web-heavy research to named lightweight Hermes workers without changing Hermes core. Provides a JSON model catalog and script for running a chosen model such as Gemma through `hermes chat -q` with the web toolset.
version: 0.1.0
author: backup-secretary
license: MIT
metadata:
  hermes:
    tags: [web-research, delegation, subagent, openrouter, gemma]
    related_skills: [hermes-agent]
---

# Web Research Agents

## Purpose

Run named, lightweight web-research workers from a skill-managed model catalog, without modifying Hermes core delegation behavior.

This is for the user's desired pattern:

```text
あかり（main agent）
  -> Web調査担当「ほの」 / Gemma / web toolset
  -> あかりが結果を検証・統合して返す
```

The skill does **not** create persistent Hermes profiles. It provides:

- a small agent/model catalog: `templates/agents.json`
- a wrapper script: `scripts/web_research_agent.py`
- a standard prompt shape for web research workers

## When to Use

Use this when:

- the task is web-heavy or source-gathering-heavy
- the main agent should avoid spending expensive model tokens on first-pass search
- the user asks to “Gemmaに調べさせる”, “Web調査を別モデルに投げる”, or similar
- model experimentation should happen via Skill/catalog changes rather than Hermes core changes

Do **not** use this when:

- the result requires immediate user clarification; child runs cannot ask the user
- the task has risky side effects; the parent agent should perform and verify side effects itself
- a normal `web_search` / `web_extract` call is enough
- a long-lived autonomous worker or separate memory is required; consider Hermes profiles or spawned Hermes instances then

## Agent Catalog

Default catalog:

```text
skills/research/web-research-agents/templates/agents.json
```

Initial entry:

```json
{
  "gemma": {
    "display_name": "三崎ほの",
    "call_name": "ほの",
    "provider": "openrouter",
    "model": "google/gemma-4-31b-it",
    "toolsets": ["web"],
    "purpose": "Web-heavy/token-heavy research, broad source gathering, first-pass summaries"
  }
}
```

The important fields are:

| Field | Meaning |
|---|---|
| `display_name` | Worker persona name used inside the task prompt |
| `call_name` | Short name for references in parent-agent reasoning |
| `provider` | Hermes provider passed to `hermes chat --provider` |
| `model` | Model ID passed to `hermes chat -m` |
| `toolsets` | Usually `["web"]` for this skill |
| `purpose` | Short role description injected into the prompt |

To test another model later, add a sibling entry, e.g. `qwen`, without changing Hermes core.

## Commands

From the repository root:

```bash
python3 skills/research/web-research-agents/scripts/web_research_agent.py --list
```

Dry-run the generated Hermes command:

```bash
python3 skills/research/web-research-agents/scripts/web_research_agent.py \
  --agent gemma \
  --dry-run \
  "OpenRouterでtool calling対応のQwenモデルを調べて"
```

Run Gemma web research:

```bash
python3 skills/research/web-research-agents/scripts/web_research_agent.py \
  --agent gemma \
  "Hermes Agentのprofile機能とdelegate_taskの違いを一次情報ベースで調べて"
```

Use a different catalog without editing the skill:

```bash
HERMES_WEB_RESEARCH_AGENT_CATALOG=/opt/data/web-agents.json \
python3 skills/research/web-research-agents/scripts/web_research_agent.py \
  --agent gemma \
  "調査テーマ"
```

## Parent Agent Workflow

1. Decide whether the task is worth delegating. Use this skill for broad web research, not tiny lookups.
2. Run the wrapper with `--agent gemma` and the user's research question.
3. Read the worker's final answer.
4. Verify important claims if they affect user decisions or external side effects.
5. Synthesize the final response in あかり's voice. Do not paste raw worker output unless the user asks.

Recommended parent prompt shape:

```text
<調査対象>について、一次情報・公式情報を優先して調査してください。
根拠URL、未確認事項、親エージェント向け所見を分けて返してください。
```

## Adding More Models Later

Add entries to `templates/agents.json`:

```json
{
  "qwen": {
    "display_name": "成瀬りん",
    "call_name": "りん",
    "provider": "openrouter",
    "model": "qwen/qwen3-32b",
    "toolsets": ["web"],
    "purpose": "Alternative web research perspective and contradiction checks"
  }
}
```

Before adding an OpenRouter model for web work, check whether the exact model advertises tool support. Model-family names are not enough; support differs by exact SKU.

## Common Pitfalls

1. **Assuming the model browses by itself.** It does not. Hermes must expose `web_search` / `web_extract` through the `web` toolset, and the selected model/provider must support tool calls.
2. **Putting secrets in the catalog.** The catalog should contain provider/model/toolset metadata only. API keys stay in Hermes `.env` / provider config.
3. **Treating worker output as verified truth.** The worker is a source-gathering assistant. The parent agent owns final judgment and verification.
4. **Using this for every tiny lookup.** For one or two simple current facts, direct `web_search` is cheaper and less fragile.
5. **Expecting current-session skill discovery to update immediately.** New/edited skills may require a new Hermes session before `skill_view` sees them by name.

## Verification Checklist

- [ ] `python3 scripts/web_research_agent.py --list` prints the catalog
- [ ] `--dry-run` shows `hermes chat -q ... --provider <provider> -m <model> -t web`
- [ ] The selected model/provider has credentials configured in Hermes
- [ ] The selected model supports tool calling for web use
- [ ] The parent agent verifies any high-impact claims before finalizing
