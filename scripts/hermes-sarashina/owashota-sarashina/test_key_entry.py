"""Offline acceptance/expiry tests; a synthetic string has no provider access."""
import json
import os
from pathlib import Path
import signal
import tempfile
import time
import unittest
import key_entry

SYNTHETIC = 'test-value-with-no-provider-access'


def wait_for(path, state):
    for _ in range(100):
        current = key_entry.read_state(path)
        if current.get('state') == state:
            return current
        time.sleep(0.05)
    raise AssertionError('Expected holder state was not reached')


class KeyEntryTests(unittest.TestCase):
    def test_controller_state_keyword_does_not_collide_with_record(self):
        import control
        from unittest.mock import patch
        folder = Path(tempfile.mkdtemp(prefix='owashota-key-entry-state-'))
        path = folder / 'state.json'
        with patch.object(control, 'STATE', path):
            control.save_state({'controller_pid': 123}, state='active')
        self.assertEqual(json.loads(path.read_text())['state'], 'active')

    def test_acknowledges_before_work_and_signals_without_key_transfer(self):
        folder = Path(tempfile.mkdtemp(prefix='owashota-key-entry-offline-'))
        path = folder / 'state.json'
        proof = folder / 'work.json'
        def task(value):
            proof.write_text(json.dumps({'matched': value == SYNTHETIC}))
        state = key_entry.receive(SYNTHETIC, path=path, ttl_seconds=20, task=task)
        try:
            self.assertEqual(state['state'], 'accepted')
            self.assertFalse(proof.exists())
            self.assertNotIn(SYNTHETIC, path.read_text())
            key_entry.notify_holder(path)
            done = wait_for(path, 'completed')
            self.assertFalse(done['has_memory_key'])
            self.assertTrue(json.loads(proof.read_text())['matched'])
            self.assertNotIn(SYNTHETIC, ''.join(p.read_text() for p in folder.iterdir() if p.is_file()))
        finally:
            if key_entry.alive(key_entry.read_state(path)):
                os.kill(state['holder_pid'], signal.SIGTERM)
            os.waitpid(state['holder_pid'], 0)

    def test_expiry_drops_key_without_running_work(self):
        folder = Path(tempfile.mkdtemp(prefix='owashota-key-entry-offline-'))
        path = folder / 'state.json'
        state = key_entry.receive(SYNTHETIC, path=path, ttl_seconds=0.5, task=lambda _: None)
        expired = wait_for(path, 'expired')
        self.assertFalse(expired['has_memory_key'])
        self.assertNotIn(SYNTHETIC, path.read_text())
        os.waitpid(state['holder_pid'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
