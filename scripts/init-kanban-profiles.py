#!/usr/bin/env python3
"""Initialize Kanban multi-profile setup for Hermes Agent.

Run this inside the Hermes container (or any container with HERMES_HOME set):
    python3 /workspace/backup-secretary/scripts/init-kanban-profiles.py
"""

import os
import shutil
import sys

try:
    import yaml
except ImportError:
    print("PyYAML not found. Install with: pip install pyyaml")
    sys.exit(1)

HERMES_HOME = os.environ.get("HERMES_HOME", "/opt/data")


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(path, data):
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=120,
        )


def ensure_profile(profile_name):
    """Clone profile from default if it doesn't exist."""
    profile_dir = os.path.join(HERMES_HOME, "profiles", profile_name)
    config_path = os.path.join(profile_dir, "config.yaml")

    if os.path.exists(config_path):
        print(f"Profile '{profile_name}' already exists. Updating config...")
        return config_path

    default_config = os.path.join(HERMES_HOME, "config.yaml")
    if not os.path.exists(default_config):
        print(f"ERROR: Default config not found at {default_config}")
        sys.exit(1)

    os.makedirs(profile_dir, exist_ok=True)
    shutil.copy2(default_config, config_path)
    print(f"Created profile '{profile_name}' from default.")
    return config_path


def setup_coordinator():
    path = ensure_profile("coordinator")
    cfg = load_config(path)

    # Coordinator routes work; it does NOT execute
    cfg["agent"]["disabled_toolsets"] = ["terminal", "code_execution", "browser"]

    # Concise personality for routing efficiency
    cfg["display"]["personality"] = "concise"

    # Ensure kanban dispatch stays enabled
    cfg.setdefault("kanban", {})
    cfg["kanban"]["dispatch_in_gateway"] = True

    save_config(path, cfg)

    # Write coordinator-specific SOUL.md with routing rules
    profile_dir = os.path.join(HERMES_HOME, "profiles", "coordinator")
    soul_path = os.path.join(profile_dir, "SOUL.md")
    soul_content = """# Coordinator SOUL.md

## Role
You are the sole Discord-facing orchestrator. You speak directly to the user in the chat.

## Routing Rules
- **Light chat, small talk, mood check, quick Q&A, opinions, everyday advice** → Reply directly in Discord. Do NOT create a Kanban task.
- **Research, investigation, code writing, document drafting, analysis, anything that takes >2 min** → Create a Kanban task via `kanban_create` and assign to `researcher` or `technical`.
- **If unsure whether it's trivial** → Ask the user "Shall I look into this properly?" before creating a task.

## Anti-temptation
- Do NOT execute the work yourself.
- Do NOT open terminal, browser, or code execution tools.
- Your only job is to decompose, route, and summarize.
"""
    with open(soul_path, "w", encoding="utf-8") as f:
        f.write(soul_content)
    print("Configured 'coordinator' profile (with SOUL.md).")


def setup_researcher():
    path = ensure_profile("researcher")
    cfg = load_config(path)

    # Cheap model for research tasks
    cfg["model"]["default"] = "gemma-4-31b-it"
    cfg["model"]["provider"] = "openrouter"
    cfg["model"]["base_url"] = "https://openrouter.ai/api/v1"

    # Worker does not connect to Discord directly
    cfg["discord"] = {}

    # Ensure kanban dispatch
    cfg.setdefault("kanban", {})
    cfg["kanban"]["dispatch_in_gateway"] = True

    save_config(path, cfg)
    print("Configured 'researcher' profile.")

    if not os.environ.get("OPENROUTER_API_KEY"):
        print("  WARNING: OPENROUTER_API_KEY not set. Researcher profile needs it.")


def setup_technical():
    path = ensure_profile("technical")
    cfg = load_config(path)

    # Fast/cheap model for coding/system ops
    cfg["model"]["default"] = "deepseek-v4-flash"
    cfg["model"]["provider"] = "opencode-go"
    cfg["model"]["base_url"] = "https://opencode.ai/zen/go/v1"

    # Worker does not connect to Discord directly
    cfg["discord"] = {}

    # Ensure kanban dispatch
    cfg.setdefault("kanban", {})
    cfg["kanban"]["dispatch_in_gateway"] = True

    save_config(path, cfg)
    print("Configured 'technical' profile.")

    if not os.environ.get("OPENCODE_GO_API_KEY"):
        print("  WARNING: OPENCODE_GO_API_KEY not set. Technical profile needs it.")


def main():
    print("Initializing Kanban multi-profile setup...")
    print(f"HERMES_HOME: {HERMES_HOME}\n")

    setup_coordinator()
    setup_researcher()
    setup_technical()

    print("\nDone.")
    print("Restart the gateway with: docker compose up -d --force-recreate hermes")


if __name__ == "__main__":
    main()
