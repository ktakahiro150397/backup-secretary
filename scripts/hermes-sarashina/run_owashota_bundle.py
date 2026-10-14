"""Deliver code-only test/preparation payload to the confirmed container over existing SSH."""
import argparse
import io
from pathlib import Path
import shlex
import subprocess
import tarfile

work = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('action', choices=('test', 'preview', 'apply', 'refresh', 'key-test', 'key-install'))
args = parser.parse_args()
bundle = work / 'owashota-sarashina'
payload = io.BytesIO()
with tarfile.open(fileobj=payload, mode='w:gz') as archive:
    # Explicit code-only allowlist. Never open or package the owner's .env.
    for relative in ('wire.py', 'proxy.py', 'prepare.py', 'control.py',
                     'test_offline.py', 'RUNBOOK.md', 'refresh.py', 'key_entry.py', 'compatibility.py',
                     'test_key_entry.py', 'install_key_entry.py',
                     'provider/__init__.py', 'provider/plugin.yaml'):
        path = bundle / relative
        if path.is_file():
            archive.add(path, arcname=relative, recursive=False)
script = {'test': 'test_offline.py', 'refresh': 'refresh.py', 'key-test': 'test_key_entry.py', 'key-install': 'install_key_entry.py'}.get(args.action, 'prepare.py')
extra = ['--apply'] if args.action == 'apply' else []
bootstrap = f'''import os,sys,tarfile,tempfile
from pathlib import Path
target=Path(tempfile.mkdtemp(prefix='owashota-sarashina-payload-'))
with tarfile.open(fileobj=sys.stdin.buffer,mode='r|gz') as t:
    t.extractall(target,filter='data')
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.chdir(target)
os.execv('/opt/hermes/.venv/bin/python',['/opt/hermes/.venv/bin/python',str(target/{script!r}),*{extra!r}])
'''
command = 'docker exec -i --user 1000:1000 backup-secretary-hermes-owashota /opt/hermes/.venv/bin/python -c ' + shlex.quote(bootstrap)
result = subprocess.run(['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
    '-o', 'ConnectTimeout=8', 'yanelmoserver', command], input=payload.getvalue(),
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
output = result.stdout.decode('utf-8', errors='replace')
(work / ('owashota-' + args.action + '-result.txt')).write_text(output, encoding='utf-8')
print(output)
raise SystemExit(result.returncode)
