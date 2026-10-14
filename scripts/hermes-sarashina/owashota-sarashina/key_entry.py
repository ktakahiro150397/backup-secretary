"""One-task, memory-only owner key handoff. Status and signals never expose the key."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
import importlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time

STATE = Path('/opt/data/profiles/owashota-sarashina/run/key-handoff.json')
TTL_SECONDS = 1800


def stamp(pid):
    return Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()[19]


def read_state(path=STATE):
    return json.loads(path.read_text()) if path.exists() else {}


def alive(record):
    try:
        return stamp(record['holder_pid']) == record['kernel_start']
    except (OSError, KeyError, ValueError):
        return False


def save(path, record, **fields):
    record.update(fields, updated_at_utc=datetime.now(timezone.utc).isoformat())
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(record, indent=2))
    temporary.chmod(0o600)
    temporary.replace(path)


def approved_task(key):
    # This callback runs in the process the owner started. The agent only signals it.
    folder = str(Path(__file__).resolve().parent)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    importlib.invalidate_caches()
    for name in ('prepare', 'wire', 'proxy', 'control'):
        if name in sys.modules:
            importlib.reload(sys.modules[name])
    import control
    if control.read_state().get('state') == 'active' and control.gateway_pid(control.PROFILE):
        return
    control.activate(key)


def hold(key, path, ttl_seconds, task):
    os.setsid()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    with open(os.devnull, 'r+') as null:
        for fd in (0, 1, 2):
            os.dup2(null.fileno(), fd)
    proceed = False
    cancelled = False
    def request(*_):
        nonlocal proceed
        proceed = True
    def cancel(*_):
        nonlocal cancelled
        cancelled = True
    signal.signal(signal.SIGUSR1, request)
    signal.signal(signal.SIGTERM, cancel)
    started = datetime.now(timezone.utc)
    state = {'task': 'owashota-sarashina', 'holder_pid': os.getpid(),
             'kernel_start': stamp(os.getpid()), 'has_memory_key': True,
             'key_saved_to_file': False, 'accepted_at_utc': started.isoformat(),
             'expires_at_utc': (started + timedelta(seconds=ttl_seconds)).isoformat()}
    deadline = time.monotonic() + ttl_seconds
    save(path, state, state='accepted')
    try:
        while not cancelled and time.monotonic() < deadline:
            if proceed:
                proceed = False
                save(path, state, state='working')
                try:
                    task(key)
                except Exception as exc:
                    save(path, state, state='waiting-retry', error_type=type(exc).__name__)
                else:
                    save(path, state, state='completed', has_memory_key=False)
                    return
            time.sleep(0.1)
        save(path, state, state='cancelled' if cancelled else 'expired', has_memory_key=False)
    finally:
        key = None


def receive(key, *, path=STATE, ttl_seconds=TTL_SECONDS, task=approved_task):
    old = read_state(path)
    if alive(old) and old.get('has_memory_key'):
        return old
    pid = os.fork()
    if pid == 0:
        try:
            hold(key, path, ttl_seconds, task)
        finally:
            os._exit(0)
    for _ in range(60):
        state = read_state(path)
        if state.get('holder_pid') == pid and state.get('state') == 'accepted' and alive(state):
            return state
        time.sleep(0.05)
    raise RuntimeError('Key handoff was not acknowledged')


def notify_holder(path=STATE, *, cancel=False):
    state = read_state(path)
    if not alive(state) or not state.get('has_memory_key'):
        raise RuntimeError('No current in-memory key is held')
    cmd = Path(f"/proc/{state['holder_pid']}/cmdline").read_bytes()
    if b'key_entry.py' not in cmd:
        raise RuntimeError('Holder process identity mismatch')
    os.kill(state['holder_pid'], signal.SIGTERM if cancel else signal.SIGUSR1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('submit', 'status', 'proceed', 'cancel'))
    parser.add_argument('--approved-context', action='store_true')
    args = parser.parse_args()
    try:
        if os.geteuid() != 1000 or os.getegid() != 1000:
            raise RuntimeError('Use the existing owashota Unix user 1000:1000')
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        if args.action == 'status':
            state = read_state()
            print(json.dumps({**state, 'holder_alive': alive(state)}, indent=2))
        elif args.action == 'submit':
            if not args.approved_context:
                raise RuntimeError('Approved task context is required')
            old = read_state()
            if alive(old) and old.get('has_memory_key'):
                print('This task already holds its key in memory. No re-entry is needed.')
                return 0
            payload = json.load(sys.stdin)
            key = payload.pop('sarashina_api_key').strip()
            payload.clear()
            if not key:
                raise RuntimeError('No key entered')
            receive(key)
            key = None
            print('Key accepted in task memory for up to 30 minutes. You can close this window now; no further key entry is needed while it is held.')
        else:
            notify_holder(cancel=args.action == 'cancel')
            print('Task signal accepted. No key was read or sent by this command.')
    except Exception as exc:
        print('Key handoff action did not complete (' + type(exc).__name__ + '). No key was printed.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
