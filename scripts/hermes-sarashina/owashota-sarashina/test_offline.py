"""Run in the real owashota image as its existing Unix user. All provider traffic is synthetic."""
from __future__ import annotations

import copy
import importlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

import httpx
import yaml

from prepare import build_config, protected_hashes, secret_paths, initial_runtime_state
from wire import compatible_body, BODY_FIELDS, MODEL, PROXY_BASE, RequestPacer
from proxy import ProxyServer

SOURCE = Path(__file__).resolve().parent
REAL_ROOT = Path('/opt/data')
ORIGINAL = yaml.safe_load((REAL_ROOT / 'config.yaml').read_text())
if secret_paths(ORIGINAL):
    raise RuntimeError('Inline credentials require review before preparing a fixture')
BEFORE = protected_hashes(REAL_ROOT)
TEST_ROOT = Path(tempfile.mkdtemp(prefix='owashota-sarashina-offline-'))
HOME = TEST_ROOT / 'profiles' / 'sarashina-test'
HOME.mkdir(parents=True)
SENTINEL = 'offline-test-synthetic-key'
FIXTURE = TEST_ROOT / 'synthetic.txt'
FIXTURE.write_text('3\n')
for name in list(os.environ):
    if any(x in name.upper() for x in ('KEY', 'TOKEN', 'PASSWORD', 'SECRET', 'AUTHORIZATION')):
        os.environ.pop(name)
os.environ.update(HOME=str(TEST_ROOT), HERMES_HOME=str(HOME), SARASHINA_API_KEY=SENTINEL,
                  PYTHONDONTWRITEBYTECODE='1', HERMES_DISABLE_MODEL_CATALOG='1')
sys.dont_write_bytecode = True
sys.path.insert(0, '/opt/hermes')
fixture_cfg = build_config(ORIGINAL)
# Fixture isolation only. The installed candidate retains all existing production settings.
fixture_cfg.update(mcp_servers={}, memory={'memory_enabled': False, 'user_profile_enabled': False, 'provider': ''},
                   plugins={'enabled': ['sarashina']}, compression={'enabled': False},
                   skills={'external_dirs': [], 'project_discovery': False})
fixture_cfg.setdefault('agent', {})['environment_probe'] = False
fixture_cfg['auxiliary'] = {'title_generation': {'enabled': False}, 'background_review': {'enabled': False}}
(HOME / 'config.yaml').write_text(yaml.safe_dump(fixture_cfg))
(HOME / '.env').write_text('# No persisted keys\n')
provider_dir = HOME / 'plugins' / 'model-providers' / 'sarashina'
shutil.copytree(SOURCE / 'provider', provider_dir)

NETWORK_BLOCKS = []
REAL_CONNECT = socket.socket.connect
REAL_GETADDRINFO = socket.getaddrinfo


def guarded_connect(sock, address):
    if isinstance(address, tuple) and address[0] in {'127.0.0.1', '::1'} and address[1] == 18761:
        return REAL_CONNECT(sock, address)
    NETWORK_BLOCKS.append('blocked')
    raise RuntimeError('Only the local synthetic proxy is reachable in this test')


def guarded_dns(host, port, *args, **kwargs):
    if host in {'127.0.0.1', '::1'} and int(port) == 18761:
        return REAL_GETADDRINFO(host, port, *args, **kwargs)
    NETWORK_BLOCKS.append('blocked')
    raise RuntimeError('External DNS is disabled')


class Clock:
    value = 1000.0
    def now(self):
        return self.value
    def sleep(self, delay):
        self.value += delay


REQUESTS = []
REPLY_TEXT = 'OK'
REPLY_STATUS = 200
PROBE_TOOL_MODE = 'valid'


def synthetic_reply(request):
    body = json.loads(request.content)
    REQUESTS.append(body)
    if str(request.url) != 'https://api.sarashina.ai/v1/chat/completions':
        raise AssertionError('Unexpected upstream destination')
    if set(body) - BODY_FIELDS:
        raise AssertionError('Unsupported field reached upstream')
    if REPLY_STATUS != 200:
        return httpx.Response(REPLY_STATUS, json={'error': {'message': 'Synthetic rejection', 'type': 'synthetic'}})
    tool = None
    if body.get('tools') and not any(m.get('role') == 'tool' for m in body['messages']):
        names = {t['function']['name'] for t in body['tools']}
        if 'read_file' in names:
            tool = {'id': 'synthetic-read', 'type': 'function', 'function': {
                'name': 'read_file', 'arguments': json.dumps({'path': str(FIXTURE)})}}
        if 'owashota_probe_add' in names and PROBE_TOOL_MODE != 'missing':
            tool = {'id': 'synthetic-add', 'type': 'function', 'function': {
                'name': 'owashota_probe_add', 'arguments': '{"a":2,"b":3}' if PROBE_TOOL_MODE == 'valid' else '{"a":"invalid"}'}}
    message = {'role': 'assistant', 'content': None if tool else REPLY_TEXT}
    if any(m.get('role') == 'tool' and m.get('tool_call_id') == 'synthetic-add' for m in body['messages']):
        message['content'] = 'The result is 5.'
    if tool:
        message['tool_calls'] = [tool]
    finish = 'tool_calls' if tool else 'stop'
    response = {'id': 'synthetic-response', 'object': 'chat.completion', 'created': 1,
        'model': MODEL, 'choices': [{'index': 0, 'message': message, 'finish_reason': finish}],
        'usage': {'prompt_tokens': 8, 'completion_tokens': 2, 'total_tokens': 10}}
    if body.get('stream'):
        delta = {'role': 'assistant', 'content': message['content']}
        if tool:
            delta['tool_calls'] = [{'index': 0, **tool}]
        start = {**response, 'object': 'chat.completion.chunk', 'choices': [
            {'index': 0, 'delta': delta, 'finish_reason': None}]}
        end = {**start, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': finish}]}
        content = '\n\n'.join('data: ' + json.dumps(x) for x in (start, end)) + '\n\ndata: [DONE]\n\n'
        return httpx.Response(200, text=content, headers={'Content-Type': 'text/event-stream'})
    return httpx.Response(200, json=response)


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clock = Clock()
        cls.server = ProxyServer(('127.0.0.1', 18761), SENTINEL,
            RequestPacer(TEST_ROOT / 'shared-pacing.txt', cls.clock.now, cls.clock.sleep),
            upstream_transport=httpx.MockTransport(synthetic_reply))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(5)
        cls.server.server_close()

    def setUp(self):
        global REPLY_TEXT, REPLY_STATUS, PROBE_TOOL_MODE
        REQUESTS.clear()
        REPLY_TEXT, REPLY_STATUS = 'OK', 200
        PROBE_TOOL_MODE = 'valid'

    def test_live_tool_probe_stream_roundtrip_and_safe_evidence(self):
        import compatibility
        from openai import OpenAI
        with OpenAI(api_key=SENTINEL, base_url=PROXY_BASE, max_retries=0) as client:
            metadata = compatibility.check_tool_roundtrip(client)
        self.assertTrue(metadata['tools_ok'])
        self.assertTrue(metadata['tool_call_valid'])
        self.assertTrue(metadata['tool_arguments_valid'])
        self.assertTrue(metadata['tool_result_used'])
        self.assertEqual(len(REQUESTS), 2)
        self.assertEqual(REQUESTS[0]['tool_choice'], 'required')
        self.assertEqual(REQUESTS[1]['tool_choice'], 'none')
        self.assertEqual(REQUESTS[1]['messages'][-1]['role'], 'tool')
        self.assertNotIn(SENTINEL, json.dumps(metadata))
        self.assertNotIn('The result is', json.dumps(metadata))

    def test_live_tool_probe_failure_never_stops_Codex(self):
        import control
        global PROBE_TOOL_MODE
        class BorrowedProxy:
            def serve_forever(self): pass
            def shutdown(self): pass
            def server_close(self): pass
        for mode in ('missing', 'bad_arguments'):
            PROBE_TOOL_MODE = mode
            with self.subTest(mode=mode), patch.object(control, 'verify_prepared'), \
                 patch.object(control, 'existing_idle'), patch.object(control, 'read_state', return_value={}), \
                 patch.object(control, 'gateway_pid', return_value=None), \
                 patch.object(control, 'new_proxy', return_value=BorrowedProxy()), \
                 patch.object(control, 'PROBE_DIAGNOSTIC', HOME / 'run' / ('tool-failure-' + mode + '.json')), \
                 patch.object(control.os, 'fork') as fork, patch.object(control.time, 'sleep'), \
                 patch.object(control, 'service_manager') as manager:
                with self.assertRaises(control.ControlError):
                    control.activate(SENTINEL)
                fork.assert_not_called()
                manager.assert_not_called()

    def test_probe_accepts_valid_sdk_text_without_exact_OK(self):
        import control
        global REPLY_TEXT
        REPLY_TEXT = 'Hello from the synthetic fixture.'
        class BorrowedProxy:
            def serve_forever(self): pass
            def shutdown(self): pass
            def server_close(self): pass
        diagnostic = HOME / 'run' / 'synthetic-probe-result.json'
        with patch.object(control, 'new_proxy', return_value=BorrowedProxy()), \
             patch.object(control, 'PROBE_DIAGNOSTIC', diagnostic):
            metadata = control.synthetic_probe(SENTINEL)
        self.assertTrue(metadata['ok'])
        self.assertEqual(metadata['http_status'], 200)
        self.assertTrue(metadata['json_content_type'])
        self.assertTrue(metadata['valid_response'])
        self.assertFalse(metadata['response_body_saved'])
        self.assertEqual(REQUESTS[-1]['max_completion_tokens'], 64)
        self.assertEqual(REQUESTS[-1]['messages'], [{'role': 'user', 'content': 'Reply with one short greeting.'}])
        saved = diagnostic.read_text()
        self.assertNotIn(REPLY_TEXT, saved)
        self.assertNotIn(SENTINEL, saved)

    def test_bad_probe_leaves_Codex_running_and_saves_only_safe_metadata(self):
        import control
        global REPLY_TEXT, REPLY_STATUS
        class BorrowedProxy:
            def serve_forever(self): pass
            def shutdown(self): pass
            def server_close(self): pass
        for status, text in ((401, 'OK'), (200, '')):
            with self.subTest(status=status):
                REPLY_STATUS, REPLY_TEXT = status, text
                diagnostic = HOME / 'run' / ('synthetic-bad-probe-' + str(status) + '.json')
                with patch.object(control, 'verify_prepared'), patch.object(control, 'existing_idle'), \
                     patch.object(control, 'read_state', return_value={}), \
                     patch.object(control, 'gateway_pid', return_value=None), \
                     patch.object(control, 'new_proxy', return_value=BorrowedProxy()), \
                     patch.object(control, 'PROBE_DIAGNOSTIC', diagnostic), \
                     patch.object(control.os, 'fork') as fork, \
                     patch.object(control, 'service_manager') as manager:
                    with self.assertRaises(control.ControlError):
                        control.activate(SENTINEL)
                    fork.assert_not_called()
                    manager.assert_not_called()
                metadata = json.loads(diagnostic.read_text())
                self.assertFalse(metadata['ok'])
                self.assertEqual(metadata['http_status'], status)
                self.assertNotIn(SENTINEL, diagnostic.read_text())

    def test_controller_persists_real_state_with_state_keyword(self):
        import control
        path = HOME / 'run' / 'synthetic-controller.json'
        record = {'controller_pid': 123}
        with patch.object(control, 'STATE', path):
            control.save_state(record, state='active')
        self.assertEqual(json.loads(path.read_text())['state'], 'active')

    def test_exited_controller_is_not_alive_while_waiting_to_be_reaped(self):
        import control
        zombie = '872467 (python3) Z ' + '0 ' * 18 + '2117666876 0'
        with patch.object(Path, 'read_text', return_value=zombie):
            self.assertFalse(control.pid_alive({'controller_pid': 872467, 'kernel_start': '2117666876'}))

    def test_stop_marks_verified_pid_even_when_s6_includes_pgid(self):
        import control
        from gateway import status
        from types import SimpleNamespace
        from unittest.mock import Mock
        manager = Mock()
        with patch.object(control, 'gateway_pid', return_value=164), \
             patch.object(control.subprocess, 'run', return_value=SimpleNamespace(stdout='164\n')) as command, \
             patch.object(status, '_get_planned_stop_marker_path', return_value=control.ROOT / 'marker'), \
             patch.object(status, 'write_planned_stop_marker', return_value=True) as marker:
            control.stop_original(manager)
            command.assert_called_once()
            self.assertEqual(command.call_args.args[0][1:3], ['-o', 'pid'])
            marker.assert_called_once_with(164)
            manager.stop.assert_called_once_with('gateway-default')
        manager.reset_mock()
        with patch.object(control, 'gateway_pid', return_value=999), \
             patch.object(control.subprocess, 'run', return_value=SimpleNamespace(stdout='164\n')), \
             patch.object(status, 'write_planned_stop_marker') as marker:
            with self.assertRaises(control.ControlError):
                control.stop_original(manager)
            marker.assert_not_called()
            manager.stop.assert_not_called()

    def test_existing_feature_configuration_preserved(self):
        candidate = build_config(ORIGINAL)
        for name in ('toolsets', 'platform_toolsets', 'mcp_servers', 'auxiliary', 'memory',
                     'approvals', 'delegation', 'terminal', 'stt', 'discord', 'compression'):
            self.assertEqual(candidate.get(name), ORIGINAL.get(name), name)
        for name, value in ORIGINAL['agent'].items():
            if name != 'reasoning_effort':
                self.assertEqual(candidate['agent'][name], value, name)
        self.assertTrue(set(ORIGINAL['plugins']['enabled']) <= set(candidate['plugins']['enabled']))
        from hermes_cli.tools_config import _get_platform_tools
        old_tools = _get_platform_tools(copy.deepcopy(ORIGINAL), 'discord')
        new_tools = _get_platform_tools(copy.deepcopy(candidate), 'discord')
        self.assertTrue(old_tools)
        self.assertEqual(new_tools, old_tools)

    def test_native_provider_resolution_and_auxiliary_request(self):
        from providers import get_provider_profile
        from hermes_cli.runtime_provider import resolve_runtime_provider
        from agent.auxiliary_client import call_llm
        self.assertIsNotNone(get_provider_profile('sarashina'))
        runtime = resolve_runtime_provider(requested='sarashina', target_model=MODEL)
        self.assertEqual(runtime['provider'], 'sarashina')
        self.assertEqual(runtime['base_url'].rstrip('/'), PROXY_BASE)
        result = call_llm(provider='sarashina', model=MODEL, api_key=SENTINEL,
            base_url=PROXY_BASE, messages=[{'role': 'user', 'content': 'Synthetic auxiliary check'}],
            max_tokens=17, reasoning_config={'enabled': True, 'effort': 'high'}, timeout=15)
        self.assertEqual(result.choices[0].message.content, 'OK')
        # This runtime intentionally omits auxiliary max_tokens for generic providers.
        # Keep that existing behavior and impose Sarashina's hard 8000 ceiling at the wire.
        self.assertEqual(REQUESTS[-1]['max_completion_tokens'], 8000)
        from openai import OpenAI
        with OpenAI(api_key=SENTINEL, base_url=PROXY_BASE, max_retries=0) as client:
            client.chat.completions.create(model=MODEL,
                messages=[{'role': 'user', 'content': 'Synthetic explicit-cap check'}], max_tokens=17)
        self.assertEqual(REQUESTS[-1]['max_completion_tokens'], 17)

    def test_main_agent_real_sdk_stream_and_file_tool_roundtrip(self):
        from run_agent import AIAgent
        agent = AIAgent(provider='sarashina', api_mode='chat_completions', model=MODEL,
            base_url=PROXY_BASE, api_key=SENTINEL, enabled_toolsets=['file'],
            max_iterations=4, quiet_mode=True, max_tokens=8000,
            skip_context_files=True, skip_memory=True, skip_background_review=True,
            save_trajectories=False)
        self.assertTrue(agent.tools)
        self.assertEqual(agent.context_compressor.context_length, 128000)
        result = agent.run_conversation('Read the synthetic fixture file and reply OK.')
        self.assertEqual(result.get('final_response'), 'OK')
        self.assertEqual(len(REQUESTS), 2)
        self.assertTrue(REQUESTS[0]['tools'])
        self.assertEqual(REQUESTS[0]['tool_choice'], 'auto')
        tool_messages = [m for m in REQUESTS[1]['messages'] if m['role'] == 'tool']
        self.assertTrue(tool_messages)
        self.assertIn('3', str(tool_messages[-1]['content']))
        agent.client.close()

    def test_strict_fields_forced_function_and_output_cap(self):
        tools = [{'type': 'function', 'function': {'name': name, 'strict': True,
                  'parameters': {'type': 'object', 'properties': {}}}} for name in ('first', 'second')]
        source = {'model': MODEL, 'messages': [{'role': 'developer', 'content': 'Synthetic'}],
            'max_tokens': 20000, 'stream_options': {'include_usage': True},
            'parallel_tool_calls': True, 'prompt_cache_key': 'synthetic', 'reasoning_effort': 'high',
            'tools': tools, 'tool_choice': {'type': 'function', 'function': {'name': 'second'}}}
        result = compatible_body(source)
        self.assertLessEqual(set(result), BODY_FIELDS)
        self.assertEqual(result['max_completion_tokens'], 8000)
        self.assertEqual(result['tool_choice'], 'required')
        self.assertEqual([t['function']['name'] for t in result['tools']], ['second'])
        self.assertEqual(result['messages'][0]['role'], 'system')

    def test_proxy_rejects_foreign_credentials_and_unsupported_images(self):
        with httpx.Client(trust_env=False) as client:
            response = client.post(PROXY_BASE + '/chat/completions',
                headers={'Authorization': 'Bearer another-provider-synthetic-key'},
                json={'model': MODEL, 'messages': []})
            self.assertEqual(response.status_code, 401)
            response = client.post(PROXY_BASE + '/chat/completions',
                headers={'Authorization': 'Bearer ' + SENTINEL},
                json={'model': MODEL, 'messages': [{'role': 'user', 'content': [
                    {'type': 'image_url', 'image_url': {'url': 'unused'}}]}]})
            self.assertEqual(response.status_code, 400)
            response = client.post(PROXY_BASE + '/chat/completions',
                headers={'Authorization': 'Bearer ' + SENTINEL},
                json={'model': MODEL, 'messages': [{'role': 'user', 'content': 'Do not forward: ' + SENTINEL}]})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(REQUESTS, [])

    def test_native_profile_auth_references_original_root_without_cloning(self):
        from hermes_constants import get_default_hermes_root
        from hermes_cli.auth import _global_auth_file_path
        self.assertEqual(get_default_hermes_root(), TEST_ROOT)
        self.assertEqual(_global_auth_file_path(), TEST_ROOT / 'auth.json')

    def test_ephemeral_profile_does_not_autostart_without_a_key(self):
        from hermes_cli.container_boot import _read_desired_state
        from gateway.status import write_runtime_status
        (HOME / 'gateway_state.json').write_text(json.dumps(initial_runtime_state()))
        self.assertEqual(_read_desired_state(HOME), 'stopped')
        write_runtime_status(gateway_state='running')
        self.assertEqual(_read_desired_state(HOME), 'stopped')

    def test_switch_and_restore_order_without_touching_real_services(self):
        import control
        import dotenv
        events = []
        class Child:
            alive = True
            def poll(self): return None if self.alive else 0
            def terminate(self):
                events.append('new-terminate'); self.alive = False
            def wait(self, **kwargs): self.alive = False
        child = Child()
        class Manager:
            def stop(self, name): events.append('stop:' + name)
            def start(self, name): events.append('start:' + name)
        class Proxy:
            def serve_forever(self): pass
            def shutdown(self): events.append('proxy-shutdown')
            def server_close(self): events.append('proxy-close')
        class Event:
            def set(self): pass
            def wait(self, *args): return True
        class Thread:
            def __init__(self, *args, **kwargs): pass
            def start(self): pass
        def spawn(*args, **kwargs):
            events.append('new-spawn')
            self.assertEqual(kwargs['env']['SARASHINA_API_KEY'], SENTINEL)
            self.assertIn('--no-supervise', args[0])
            from hermes_cli.gateway import _maybe_redirect_run_to_s6_supervision
            from types import SimpleNamespace
            self.assertFalse(_maybe_redirect_run_to_s6_supervision(SimpleNamespace(no_supervise=True)))
            return child
        with patch.object(control.os, 'setsid'), patch.object(control.os, 'dup2'), \
             patch.object(control.signal, 'signal'), patch.object(control, 'kernel_start', return_value='synthetic'), \
             patch.object(control, 'verify_prepared'), patch.object(control, 'existing_idle'), \
             patch.object(control, 'new_proxy', return_value=Proxy()), \
             patch.object(control, 'service_manager', return_value=Manager()), \
             patch.object(control, 'stop_original', side_effect=lambda m: m.stop('gateway-default')), \
             patch.object(control, 'wait_pid', return_value=123), \
             patch.object(control, 'gateway_pid', return_value=None), \
             patch.object(control, 'save_state'), patch.object(dotenv, 'dotenv_values', return_value={}), \
             patch.object(control.subprocess, 'Popen', side_effect=spawn), \
             patch.object(control.threading, 'Event', Event), patch.object(control.threading, 'Thread', Thread):
            control.supervise(SENTINEL)
        self.assertLess(events.index('stop:gateway-default'), events.index('new-spawn'))
        self.assertLess(events.index('new-terminate'), events.index('start:gateway-default'))
        self.assertEqual([x for x in events if x.startswith('stop:')], ['stop:gateway-default'])

    def test_orphan_recovery_stops_only_the_validated_named_profile(self):
        import control
        with patch.object(control, 'read_state', return_value={}), \
             patch.object(control, 'pid_alive', return_value=False), \
             patch.object(control, 'gateway_pid', side_effect=lambda h: 303 if h == control.PROFILE else 164), \
             patch.object(control.os, 'kill') as kill, patch.object(control, 'wait_pid') as wait, \
             patch.object(control, 'service_manager') as manager, patch.object(sys, 'stdout', io.StringIO()):
            control.restore()
            kill.assert_called_once_with(303, control.signal.SIGTERM)
            wait.assert_any_call(control.PROFILE, False)
            manager.return_value.start.assert_called_once_with('gateway-default')
        with patch.object(control, 'read_state', return_value={}), \
             patch.object(control, 'pid_alive', return_value=False), \
             patch.object(control, 'gateway_pid', return_value=164), \
             patch.object(control.os, 'kill') as kill, patch.object(control, 'service_manager') as manager:
            with self.assertRaises(control.ControlError):
                control.restore()
            kill.assert_not_called()
            manager.assert_not_called()

    def test_shared_pacing_and_429(self):
        clock = Clock()
        path = TEST_ROOT / 'rate-proof.txt'
        pacers = [RequestPacer(path, clock.now, clock.sleep) for _ in range(2)]
        starts = []
        for i in range(7):
            pacers[i % 2].acquire()
            starts.append(clock.now())
        self.assertGreaterEqual(starts[6] - starts[0], 60)
        last = clock.now()
        pacers[0].on_rate_limit()
        pacers[1].acquire()
        self.assertGreaterEqual(clock.now() - last, 60)

    def test_activation_without_data_approval_never_reads_a_key_or_stops_service(self):
        import control
        with patch.object(sys, 'argv', ['control.py', 'activate', '--approve-synthetic-probe']), \
             patch.object(control, 'key_input') as keys, \
             patch.object(control, 'service_manager') as services, \
             patch.object(sys, 'stderr', io.StringIO()):
            self.assertEqual(control.main(), 1)
            keys.assert_not_called()
            services.assert_not_called()


def main():
    with patch.object(socket.socket, 'connect', guarded_connect), \
         patch.object(socket, 'getaddrinfo', guarded_dns):
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    persisted = [str(p.relative_to(HOME)) for p in HOME.rglob('*')
                 if p.is_file() and p.stat().st_size < 1024 * 1024 and SENTINEL.encode() in p.read_bytes()]
    unchanged = protected_hashes(REAL_ROOT) == BEFORE
    summary = {'successful': result.wasSuccessful() and not persisted and unchanged,
        'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'original_protected_files_unchanged': unchanged, 'synthetic_key_persisted_files': persisted,
        'external_network_attempts_blocked': len(NETWORK_BLOCKS), 'real_provider_requests': 0,
        'discord_posts': 0, 'unix_uid': os.geteuid(), 'test_home': str(TEST_ROOT)}
    print('RESULT_JSON=' + json.dumps(summary, ensure_ascii=True))
    return 0 if summary['successful'] else 1


if __name__ == '__main__':
    sys.exit(main())
