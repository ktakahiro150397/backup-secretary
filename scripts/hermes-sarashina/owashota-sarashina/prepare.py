"""Create one inactive named profile without cloning credentials or changing the live gateway."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from datetime import datetime, timezone

ROOT = Path('/opt/data')
PROFILE_NAME = 'owashota-sarashina'
PROFILE = ROOT / 'profiles' / PROFILE_NAME
SUPPORT = ROOT / 'sarashina-support'
RESOURCES = (
    'SOUL.md', 'skills', 'scripts', 'artifacts', 'tools', 'bin', 'venvs', '.venv-tools',
    'lazy-packages', 'models', 'playwright-browsers', 'hooks', 'cron', 'skins',
    'openviking', 'platforms', 'workspace',
)
PAYLOAD_FILES = ('wire.py', 'proxy.py', 'prepare.py', 'control.py', 'compatibility.py', 'test_offline.py', 'RUNBOOK.md')
SECRET_KEY = re.compile(r'(^|_)(key|token|password|secret|authorization)($|_)', re.I)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def secret_paths(value, prefix=''):
    found = []
    if isinstance(value, dict):
        for name, item in value.items():
            path = prefix + '.' + str(name) if prefix else str(name)
            is_reference = str(name).lower().endswith(('_env', '_env_var', '_env_vars'))
            if SECRET_KEY.search(str(name)) and not is_reference and item:
                found.append(path)
            else:
                found += secret_paths(item, path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found += secret_paths(item, f'{prefix}[{index}]')
    return found


def build_config(original):
    cfg = copy.deepcopy(original)
    cfg['model'] = {**cfg.get('model', {}), 'provider': 'sarashina',
                    'default': 'sarashina3-mini', 'base_url': 'http://127.0.0.1:18761/v1',
                    'context_length': 128000}
    cfg.setdefault('agent', {})['reasoning_effort'] = 'none'
    enabled = cfg.setdefault('plugins', {}).setdefault('enabled', [])
    if 'sarashina' not in enabled:
        enabled.append('sarashina')
    # Runtime-specific model metadata, with tool support retained.
    cfg.setdefault('model_overrides', {}).setdefault('sarashina', {})['sarashina3-mini'] = {
        'context_window': 128000, 'supports_tools': True,
        'supports_vision': False, 'supports_reasoning': False,
    }
    return cfg


def protected_hashes(root):
    return {name: digest(root / name) for name in ('config.yaml', 'SOUL.md', '.env', 'auth.json')}


def initial_runtime_state():
    # Never let container-boot restore a keyless Sarashina gateway automatically.
    return {'gateway_state': 'stopped', 'desired_state': 'stopped', 'active_agents': 0}


def main():
    import yaml
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    original = yaml.safe_load((ROOT / 'config.yaml').read_text()) or {}
    secrets = secret_paths(original)
    if secrets:
        raise RuntimeError('Inline credential fields require review before copying: ' + ', '.join(secrets))
    before = protected_hashes(ROOT)
    record = json.loads((ROOT / 'gateway.pid').read_text())
    status = Path('/proc/' + str(record['pid']) + '/status').read_text().splitlines()
    identity = {line.split(':', 1)[0]: int(line.split(':', 1)[1].split()[1])
                for line in status if line.startswith(('Uid:', 'Gid:'))}
    cfg = build_config(original)
    if cfg.get('toolsets') != original.get('toolsets') or cfg.get('mcp_servers') != original.get('mcp_servers'):
        raise RuntimeError('Tool configuration changed unexpectedly')
    plan = {
        'at_utc': datetime.now(timezone.utc).isoformat(),
        'container': 'backup-secretary-hermes-owashota', 'profile': str(PROFILE),
        'support': str(SUPPORT), 'original_hashes': before,
        'changed_sections': ['model', 'agent.reasoning_effort', 'plugins.enabled', 'model_overrides.sarashina'],
        'toolsets_preserved': True, 'mcp_preserved': True, 'memory_preserved': True,
        'vision_preserved': True, 'stt_preserved': True, 'approvals_preserved': True,
        'shared_existing_resources': [name for name in RESOURCES if (ROOT / name).exists()],
        'existing_plugin_links': [p.name for p in (ROOT / 'plugins').iterdir() if p.is_dir()],
        'new_local_history': True, 'credentials_copied': False, 'gateway_started': False,
        'proxy_started': False, 'real_api_calls': 0, 'discord_posts': 0,
        'effective_uid': identity['Uid'], 'effective_gid': identity['Gid'],
    }
    if args.apply:
        if os.geteuid() != identity['Uid'] or os.getegid() != identity['Gid']:
            raise RuntimeError('Apply as the same Unix user/group as the existing gateway')
        if PROFILE.exists() or SUPPORT.exists():
            raise RuntimeError('Prepared path already exists; refusing to overwrite it')
        SUPPORT.mkdir(mode=0o700)
        PROFILE.mkdir(mode=0o700, parents=True)
        for name in PAYLOAD_FILES:
            shutil.copyfile(source / name, SUPPORT / name)
        (PROFILE / 'config.yaml').write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False))
        (PROFILE / 'config.yaml').chmod(0o600)
        (PROFILE / '.env').write_text('# Credentials are supplied to the process; do not put keys here.\n')
        (PROFILE / '.env').chmod(0o600)
        (PROFILE / '.no-bundled-skills').write_text('Existing owashota skills are linked, not replaced.\n')
        (PROFILE / 'gateway_state.json').write_text(json.dumps(initial_runtime_state()) + '\n')
        for name in RESOURCES:
            if (ROOT / name).exists():
                (PROFILE / name).symlink_to(ROOT / name, target_is_directory=(ROOT / name).is_dir())
        plugin_root = PROFILE / 'plugins'
        plugin_root.mkdir()
        for item in (ROOT / 'plugins').iterdir():
            if item.is_dir():
                if item.name == 'model-providers':
                    raise RuntimeError('Existing model-provider directory requires a merge review')
                (plugin_root / item.name).symlink_to(item, target_is_directory=True)
        provider = plugin_root / 'model-providers' / 'sarashina'
        provider.mkdir(parents=True)
        for name in ('__init__.py', 'plugin.yaml'):
            shutil.copyfile(source / 'provider' / name, provider / name)
        if protected_hashes(ROOT) != before:
            raise RuntimeError('A source file changed while staging; live gateway was not touched')
        plan['prepared_config_sha256'] = digest(PROFILE / 'config.yaml')
        plan['support_manifest'] = {name: digest(SUPPORT / name) for name in PAYLOAD_FILES}
        plan['provider_manifest'] = {name: digest(provider / name) for name in ('__init__.py', 'plugin.yaml')}
        (SUPPORT / 'manifest.json').write_text(json.dumps(plan, ensure_ascii=True, indent=2))
        plan['installed_inactive'] = True
    print(json.dumps(plan, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
