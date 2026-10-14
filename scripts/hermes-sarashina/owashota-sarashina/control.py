"""Owner-operated ephemeral switch for the confirmed owashota container only.

Key input arrives on stdin, never argv or a file. No action is run at import.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time

from prepare import ROOT, PROFILE, SUPPORT, digest
from wire import MODEL, PROXY_BASE, RequestPacer
from proxy import ProxyServer

STATE = PROFILE / 'run' / 'sarashina-controller.json'
PROBE_DIAGNOSTIC = PROFILE / 'run' / 'probe-result.json'
RUNTIME_PYTHON = Path('/opt/hermes/.venv/bin/python')


class ControlError(Exception):
    pass


def hermes_imports():
    if '/opt/hermes' not in sys.path:
        sys.path.insert(0, '/opt/hermes')


def kernel_start(pid):
    fields = Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()
    if fields[0] in {'Z', 'X'}:
        raise ProcessLookupError('Process has exited')
    return fields[19]


def pid_alive(record):
    try:
        return kernel_start(int(record['controller_pid'])) == str(record['kernel_start'])
    except (OSError, KeyError, ValueError):
        return False


def gateway_pid(home):
    hermes_imports()
    from gateway.status import get_running_pid
    return get_running_pid(home / 'gateway.pid', cleanup_stale=False)


def read_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(record, **fields):
    STATE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    record.update(fields, updated_at_utc=datetime.now(timezone.utc).isoformat())
    temporary = STATE.with_suffix('.tmp')
    temporary.write_text(json.dumps(record, indent=2))
    temporary.replace(STATE)


def verify_prepared():
    manifest = json.loads((SUPPORT / 'manifest.json').read_text())
    if digest(PROFILE / 'config.yaml') != manifest['prepared_config_sha256']:
        raise ControlError('Prepared config changed; review it before switching')
    for name, expected in manifest['support_manifest'].items():
        if digest(SUPPORT / name) != expected:
            raise ControlError('Support code changed; repeat offline validation')
    provider = PROFILE / 'plugins' / 'model-providers' / 'sarashina'
    for name, expected in manifest['provider_manifest'].items():
        if digest(provider / name) != expected:
            raise ControlError('Provider registration changed; repeat offline validation')
    for name in ('config.yaml', 'SOUL.md'):
        if digest(ROOT / name) != manifest['original_hashes'][name]:
            raise ControlError('Existing owashota context/config changed; refresh the reviewed preparation')
    if os.geteuid() != manifest['effective_uid'] or os.getegid() != manifest['effective_gid']:
        raise ControlError('Use the same Unix user as the existing owashota gateway')
    return manifest


def existing_idle():
    path = ROOT / 'gateway_state.json'
    if not path.exists():
        raise ControlError('Existing gateway activity could not be verified')
    data = json.loads(path.read_text())
    if data.get('active_agents') != 0:
        raise ControlError('Existing owashota still has active agents; let them finish first')


def key_input():
    try:
        key = json.load(sys.stdin)['sarashina_api_key'].strip()
    except Exception:
        raise ControlError('Supply the existing key as JSON on stdin; never put it in command arguments')
    if not key or any(x in key.lower() for x in ('placeholder', 'synthetic', 'offline-test')):
        raise ControlError('A real existing Sarashina key is required')
    return key


def existing_credential_values():
    # Read locally into memory only. Do not refresh, echo, or persist any credential.
    from dotenv import dotenv_values
    values = []
    sensitive = re.compile(r'(^|_)(key|token|secret|password|authorization)($|_)', re.I)
    for name, value in {**os.environ, **dotenv_values(ROOT / '.env')}.items():
        if sensitive.search(name) and isinstance(value, str) and len(value) >= 12:
            values.append(value)
    def visit(item):
        if isinstance(item, dict):
            for name, value in item.items():
                if sensitive.search(str(name)) and isinstance(value, str) and len(value) >= 12:
                    values.append(value)
                else:
                    visit(value)
        elif isinstance(item, list):
            for value in item:
                visit(value)
    if (ROOT / 'auth.json').exists():
        visit(json.loads((ROOT / 'auth.json').read_text()))
    return values


def new_proxy(key):
    return ProxyServer(('127.0.0.1', 18761), key,
                       RequestPacer(PROFILE / 'run' / 'next-request.txt'),
                       protected_values=existing_credential_values())


def probe_response_metadata(response):
    choices = getattr(response, 'choices', None) or []
    choice = choices[0] if choices else None
    message = getattr(choice, 'message', None)
    content = getattr(message, 'content', None)
    finish = getattr(choice, 'finish_reason', None)
    valid_text = isinstance(content, str) and bool(content.strip())
    response_object_valid = getattr(response, 'object', None) == 'chat.completion'
    role_valid = getattr(message, 'role', None) == 'assistant'
    finish_valid = finish in {'stop', 'length'}
    return {
        'response_object_valid': response_object_valid,
        'choices_count': len(choices), 'assistant_role_valid': role_valid,
        'text_present': valid_text, 'text_characters': len(content) if isinstance(content, str) else 0,
        'finish_reason': finish if finish in {'stop', 'length', 'tool_calls', 'content_filter'} else 'other',
        'model_matches_request': getattr(response, 'model', None) == MODEL,
        'valid_response': response_object_valid and role_valid and valid_text and finish_valid,
    }


def save_probe_metadata(metadata):
    PROBE_DIAGNOSTIC.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = PROBE_DIAGNOSTIC.with_suffix('.tmp')
    temporary.write_text(json.dumps(metadata, indent=2))
    temporary.replace(PROBE_DIAGNOSTIC)


def synthetic_probe(key, *, include_tools=False):
    from openai import OpenAI
    metadata = {'ok': False, 'at_utc': datetime.now(timezone.utc).isoformat(),
                'http_status': None, 'response_body_saved': False, 'key_saved': False}
    started = time.monotonic()
    server = new_proxy(key)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with OpenAI(api_key=key, base_url=PROXY_BASE, max_retries=0, timeout=90) as client:
            raw = client.with_raw_response.chat.completions.create(model=MODEL,
                messages=[{'role': 'user', 'content': 'Reply with one short greeting.'}],
                max_tokens=64, temperature=0, stream=False)
            metadata['http_status'] = raw.status_code
            metadata['json_content_type'] = raw.headers.get('content-type', '').lower().startswith('application/json')
            response = raw.parse()
            metadata.update(probe_response_metadata(response))
            if not 200 <= raw.status_code < 300 or not metadata['valid_response']:
                raise ControlError('Synthetic probe did not return a valid non-empty assistant response; live gateway was not stopped')
            if include_tools:
                from compatibility import check_tool_roundtrip
                check_tool_roundtrip(client, metadata)
            metadata['ok'] = True
    except Exception as exc:
        status = getattr(exc, 'status_code', None)
        if isinstance(status, int):
            metadata['http_status'] = status
        metadata['error_type'] = type(exc).__name__
        if isinstance(exc, ControlError):
            raise
        label = 'HTTP ' + str(metadata['http_status']) if metadata['http_status'] else type(exc).__name__
        raise ControlError('Synthetic probe failed (' + label + '); live gateway was not stopped') from None
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        metadata['elapsed_ms'] = round((time.monotonic() - started) * 1000)
        save_probe_metadata(metadata)
    return metadata


def service_manager():
    hermes_imports()
    from hermes_cli.service_manager import S6ServiceManager
    return S6ServiceManager()


def stop_original(manager):
    # The installed Hermes parser expects "(pid N)"; this s6 emits
    # "(pid N pgid N)", so its normal stop silently skips the planned marker.
    # Ask s6 for its machine-readable PID and cross-check the Hermes identity.
    result = subprocess.run(['/command/s6-svstat', '-o', 'pid', '/run/service/gateway-default'],
        check=True, capture_output=True, text=True, timeout=5)
    pid = int(result.stdout.strip())
    if pid <= 0 or gateway_pid(ROOT) != pid:
        raise ControlError('Original gateway identity disagrees with s6; no process was stopped')
    hermes_imports()
    from gateway.status import _get_planned_stop_marker_path, write_planned_stop_marker
    if _get_planned_stop_marker_path().parent != ROOT or not write_planned_stop_marker(pid):
        raise ControlError('Original gateway planned-stop marker could not be written')
    manager.stop('gateway-default')


def wait_pid(home, running, seconds=40):
    for _ in range(seconds):
        pid = gateway_pid(home)
        if bool(pid) == running:
            return pid
        time.sleep(1)
    raise ControlError('Gateway process transition did not complete; inspect status before retrying')


def supervise(key):
    os.setsid()
    with open(os.devnull, 'r+') as null:
        for fd in (0, 1, 2):
            os.dup2(null.fileno(), fd)
    stopped = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    state = {'controller_pid': os.getpid(), 'kernel_start': kernel_start(os.getpid()),
             'state': 'starting', 'profile': str(PROFILE)}
    server = None
    child = None
    original_stopped = False
    try:
        verify_prepared()
        existing_idle()
        server = new_proxy(key)  # Binding failure must happen before stopping Codex.
        threading.Thread(target=server.serve_forever, daemon=True).start()
        save_state(state)
        manager = service_manager()
        original_stopped = True
        stop_original(manager)
        wait_pid(ROOT, False)
        from dotenv import dotenv_values
        env = os.environ.copy()
        env.update({k: v for k, v in dotenv_values(ROOT / '.env').items() if v is not None})
        env.update(SARASHINA_API_KEY=key, HERMES_HOME=str(ROOT), HOME=str(ROOT),
                   PYTHONDONTWRITEBYTECODE='1')
        child = subprocess.Popen([str(RUNTIME_PYTHON), '-m', 'hermes_cli.main',
            '-p', 'owashota-sarashina', 'gateway', 'run', '--no-supervise'], cwd='/opt/hermes', env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
        pid = wait_pid(PROFILE, True)
        save_state(state, state='active', gateway_pid=pid, proxy_port=18761)
        while not stopped.wait(1) and child.poll() is None:
            pass
    except Exception as exc:
        save_state(state, state='error', error_type=type(exc).__name__)
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=40)
            except subprocess.TimeoutExpired:
                save_state(state, state='shutdown-pending')
                # Keep the proxy and its in-memory key available until the active turn ends.
                child.wait()
        if server is not None:
            server.shutdown()
            server.server_close()
        if original_stopped and not gateway_pid(PROFILE):
            try:
                service_manager().start('gateway-default')
                wait_pid(ROOT, True)
                save_state(state, state='codex-restored')
            except Exception as exc:
                save_state(state, state='recovery-required', error_type=type(exc).__name__)


def activate(key):
    verify_prepared()
    existing_idle()
    old = read_state()
    if pid_alive(old) or gateway_pid(PROFILE):
        raise ControlError('Sarashina is already running; no duplicate was started')
    probe = synthetic_probe(key, include_tools=True)  # All checks run while Codex remains up.
    print('Synthetic probe passed (HTTP ' + str(probe['http_status']) + '; valid assistant text; streamed tool round trip)')
    pid = os.fork()
    if pid == 0:
        try:
            supervise(key)
        finally:
            os._exit(0)
    for _ in range(55):
        state = read_state()
        if state.get('controller_pid') == pid:
            if state.get('state') == 'active':
                print('owashota Sarashina profile is active; no Discord test post was sent')
                return
            if state.get('state') in {'error', 'codex-restored', 'recovery-required'}:
                raise ControlError('Activation did not complete; inspect controller status')
        time.sleep(1)
    raise ControlError('Activation status is pending; inspect status before retrying')


def restore():
    record = read_state()
    if pid_alive(record):
        os.kill(record['controller_pid'], signal.SIGTERM)
        for _ in range(50):
            if not gateway_pid(PROFILE) and gateway_pid(ROOT):
                print('Original owashota Codex gateway is running')
                return
            time.sleep(1)
        raise ControlError('Sarashina shutdown is pending; wait for its active turn and inspect status')
    orphan = gateway_pid(PROFILE)
    if orphan:
        if orphan == gateway_pid(ROOT):
            raise ControlError('Profile PID identity conflict; no process was stopped')
        # get_running_pid validated the named profile's live process identity.
        # This does not rely on an s6 slot, which need not exist for our ephemeral child.
        os.kill(orphan, signal.SIGTERM)
        wait_pid(PROFILE, False)
    service_manager().start('gateway-default')
    wait_pid(ROOT, True)
    print('Original owashota Codex gateway is running')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status', 'smoke', 'activate', 'restore'))
    parser.add_argument('--approve-synthetic-probe', action='store_true')
    parser.add_argument('--approve-context-transfer', action='store_true')
    args = parser.parse_args()
    try:
        if args.action == 'status':
            print(json.dumps({'original_gateway_pid': gateway_pid(ROOT),
                'sarashina_gateway_pid': gateway_pid(PROFILE), 'controller': read_state()}, indent=2))
        elif args.action == 'restore':
            restore()
        else:
            if not args.approve_synthetic_probe:
                raise ControlError('Approve the fixed synthetic probe before using a key')
            if args.action == 'activate' and not args.approve_context_transfer:
                raise ControlError('Approval for the documented owashota context/tool-output transfer is required')
            verify_prepared()
            key = key_input()
            if args.action == 'smoke':
                probe = synthetic_probe(key, include_tools=True)
                print('Synthetic probe passed (HTTP ' + str(probe['http_status']) + '; valid text and streamed tool round trip). Existing Codex gateway was not stopped')
            else:
                activate(key)
    except ControlError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print('Action did not complete: ' + type(exc).__name__ + '. No credentials were printed.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
