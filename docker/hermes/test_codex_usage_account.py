"""Run with the Hermes image's Python; credentials and HTTP are mocked."""
import base64
import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, '/opt/hermes')
import agent.account_usage as usage


def token(account):
    claims = {'https://api.openai.com/auth': {'chatgpt_account_id': account}}
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=')
    return 'test.' + payload + '.signature'


class UsageAccountTests(unittest.TestCase):
    def test_explicit_credentials_keep_their_account(self):
        access = token('explicit-account')
        actual = usage._resolve_codex_usage_credentials('https://example.test', access)
        self.assertEqual(actual, (access, 'https://example.test', 'explicit-account'))

    def test_runtime_credentials_do_not_take_another_singleton_account(self):
        access = token('runtime-account')
        with patch.object(usage, 'resolve_codex_runtime_credentials', return_value={'api_key':access, 'base_url':'https://example.test'}):
            with patch.object(usage, '_read_codex_tokens', create=True, return_value={'tokens':{'account_id':'stale-account'}}):
                actual = usage._resolve_codex_usage_credentials(None, None)
        self.assertEqual(actual[2], 'runtime-account')

    def test_pool_fallback_keeps_selected_account(self):
        entry = SimpleNamespace(runtime_api_key=token('pool-account'), runtime_base_url='https://example.test')
        with patch.object(usage, 'resolve_codex_runtime_credentials', side_effect=usage.AuthError('none')):
            with patch('agent.credential_pool.load_pool', return_value=SimpleNamespace(select=lambda:entry)):
                self.assertEqual(usage._resolve_codex_usage_credentials(None,None)[2], 'pool-account')

    def test_refresh_failure_does_not_switch_accounts(self):
        with patch.object(usage, 'resolve_codex_runtime_credentials', side_effect=RuntimeError('refresh failure')):
            with patch('agent.credential_pool.load_pool') as pool:
                with self.assertRaises(RuntimeError):
                    usage._resolve_codex_usage_credentials(None,None)
                pool.assert_not_called()

    def test_invalid_or_missing_claim_does_not_become_header(self):
        for value in ('opaque', token(None), token(123), token(''), token('bad\r\nheader')):
            with self.subTest(value=value):
                self.assertIsNone(usage._resolve_codex_usage_credentials(None,value)[2])

    def test_usage_request_is_account_scoped(self):
        seen = []
        class Client:
            def __init__(self, **kwargs): pass
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def get(self, url, *, headers):
                seen.append(headers)
                percent = 52 if headers.get('ChatGPT-Account-Id') == 'selected-account' else 100
                return SimpleNamespace(raise_for_status=lambda:None, json=lambda:{'rate_limit':{'primary_window':{'used_percent':percent,'reset_at':1791046725}}})
        with patch.object(usage.httpx, 'Client', Client):
            snapshot = usage._fetch_codex_account_usage(api_key=token('selected-account'))
        self.assertEqual(snapshot.windows[0].used_percent, 52)
        self.assertEqual(seen[0]['ChatGPT-Account-Id'], 'selected-account')


if __name__ == '__main__':
    unittest.main()
