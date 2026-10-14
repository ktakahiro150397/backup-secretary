"""Update only our inactive support bundle after a validated repair."""
import json
import shutil
import socket
import sys
from pathlib import Path
from datetime import datetime, timezone
from prepare import PROFILE, SUPPORT, PAYLOAD_FILES, digest

sys.dont_write_bytecode = True
sys.path.insert(0, '/opt/hermes')
from gateway.status import get_running_pid

source = Path(__file__).resolve().parent
manifest_path = SUPPORT / 'manifest.json'
manifest = json.loads(manifest_path.read_text())
if get_running_pid(PROFILE / 'gateway.pid', cleanup_stale=False):
    raise RuntimeError('Candidate is active; no code was overwritten')
for name, expected in manifest['support_manifest'].items():
    if digest(SUPPORT / name) != expected:
        raise RuntimeError('Installed support was changed by another writer')
if digest(PROFILE / 'config.yaml') != manifest['prepared_config_sha256']:
    raise RuntimeError('Candidate config was changed by another writer')
for name in PAYLOAD_FILES:
    shutil.copyfile(source / name, SUPPORT / name)
manifest['support_manifest'] = {name: digest(SUPPORT / name) for name in PAYLOAD_FILES}
manifest['support_updated_at_utc'] = datetime.now(timezone.utc).isoformat()
temporary = manifest_path.with_suffix('.tmp')
temporary.write_text(json.dumps(manifest, ensure_ascii=True, indent=2))
temporary.replace(manifest_path)
print('Only the inactive support bundle was refreshed; original gateway and profile config were untouched.')
