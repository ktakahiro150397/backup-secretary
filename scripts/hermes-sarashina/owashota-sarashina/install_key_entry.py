"""Install only the independent memory-handoff entry point, leaving gateway code untouched."""
import hashlib
from pathlib import Path

source = Path(__file__).resolve().parent / 'key_entry.py'
target = Path('/opt/data/sarashina-support/key_entry.py')
if target.exists() and target.read_bytes() != source.read_bytes():
    raise RuntimeError('Existing entry point differs; do not overwrite a running holder')
target.write_bytes(source.read_bytes())
target.chmod(0o600)
print('Memory-only key entry installed. No key, API probe, gateway start, or gateway stop was performed.')
