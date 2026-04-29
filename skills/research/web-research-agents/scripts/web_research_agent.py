#!/usr/bin/env python3
"""Run named Hermes web-research agents from a small JSON catalog.

This script intentionally avoids Hermes core changes. It shells out to
`hermes chat -q ...` with the provider/model/toolsets specified by the
catalog entry.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_CATALOG = Path(__file__).resolve().parents[1] / "templates" / "agents.json"


def load_catalog(path: Path) -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"catalog not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid catalog JSON: {path}: {exc}")
    if not isinstance(data, dict):
        raise SystemExit("catalog root must be an object")
    return data


def agent_prompt(agent: dict[str, Any], prompt: str) -> str:
    display_name = agent.get("display_name", "Web research agent")
    call_name = agent.get("call_name", display_name)
    purpose = agent.get("purpose", "Web research")
    return f"""あなたはWeb調査担当 subagent「{display_name}」（呼び名: {call_name}）です。

役割:
- {purpose}
- Web検索とURL抽出を使い、一次情報・公式情報を優先して調査する
- 推測と確認済み事実を分ける
- 重要な主張には根拠URLを付ける
- 最終判断は親エージェントが行うので、判断材料を簡潔に返す

出力形式:
1. 要約
2. 根拠URLつきの主要事実
3. 不確実な点 / 追加確認が必要な点
4. 親エージェント向けの短い所見

調査依頼:
{prompt}
"""


def build_command(agent: dict[str, Any], prompt: str, hermes_bin: str = "hermes") -> list[str]:
    provider = agent.get("provider")
    model = agent.get("model")
    toolsets = agent.get("toolsets", ["web"])
    if not provider or not model:
        raise SystemExit("agent entry must include provider and model")
    if not isinstance(toolsets, list) or not all(isinstance(t, str) for t in toolsets):
        raise SystemExit("agent toolsets must be a list of strings")

    return [
        hermes_bin,
        "chat",
        "-q",
        agent_prompt(agent, prompt),
        "--provider",
        provider,
        "-m",
        model,
        "-t",
        ",".join(toolsets),
        "-Q",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run named Hermes web-research agents")
    parser.add_argument("prompt", nargs="?", help="research prompt; omit with --list or use --prompt-file")
    parser.add_argument("--agent", default="gemma", help="agent key in the catalog (default: gemma)")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path(os.environ.get("HERMES_WEB_RESEARCH_AGENT_CATALOG", DEFAULT_CATALOG)),
        help="path to agents.json",
    )
    parser.add_argument("--list", action="store_true", help="list available agents")
    parser.add_argument("--prompt-file", type=Path, help="read the research prompt from a UTF-8 text file")
    parser.add_argument("--dry-run", action="store_true", help="print the Hermes command JSON without running it")
    parser.add_argument("--timeout", type=int, default=600, help="subprocess timeout seconds (default: 600)")
    parser.add_argument(
        "--hermes-bin",
        default=os.environ.get("HERMES_BIN", "hermes"),
        help="Hermes CLI executable (default: HERMES_BIN or hermes)",
    )
    args = parser.parse_args()

    catalog = load_catalog(args.catalog)

    if args.list:
        print(json.dumps({"agents": catalog}, ensure_ascii=False, indent=2))
        return 0

    if args.prompt and args.prompt_file:
        parser.error("use either positional prompt or --prompt-file, not both")
    if args.prompt_file:
        try:
            prompt = args.prompt_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise SystemExit(f"prompt file not found: {args.prompt_file}")
    elif args.prompt:
        prompt = args.prompt
    else:
        parser.error("prompt is required unless --list is used; use --prompt-file for long or non-ASCII prompts")

    if args.agent not in catalog:
        raise SystemExit(f"unknown agent: {args.agent}. available: {', '.join(sorted(catalog))}")

    cmd = build_command(catalog[args.agent], prompt, hermes_bin=args.hermes_bin)
    if args.dry_run:
        print(json.dumps({"command": cmd}, ensure_ascii=False, indent=2))
        return 0

    if shutil.which(args.hermes_bin) is None:
        print(
            f"Hermes CLI not found: {args.hermes_bin}. Install Hermes or set HERMES_BIN/--hermes-bin to the executable path.",
            file=sys.stderr,
        )
        return 127

    completed = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=args.timeout)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
