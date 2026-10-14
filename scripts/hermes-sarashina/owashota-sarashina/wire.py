"""Sarashina wire compatibility and Linux cross-process pacing. No credentials on disk."""
from __future__ import annotations

import fcntl
import json
from pathlib import Path
import re
import time

MODEL = 'sarashina3-mini'
UPSTREAM = 'https://api.sarashina.ai/v1/chat/completions'
PROXY_BASE = 'http://127.0.0.1:18761/v1'
BODY_FIELDS = frozenset({
    'model', 'messages', 'frequency_penalty', 'max_completion_tokens', 'n',
    'presence_penalty', 'repetition_penalty', 'response_format', 'seed', 'stop',
    'stream', 'temperature', 'tool_choice', 'tools', 'top_p', 'top_k',
})


def contains_credentials(body, protected_values):
    text = json.dumps(body, ensure_ascii=False)
    if re.search(r'-----BEGIN [A-Z ]*PRIVATE KEY-----', text):
        return True
    return any(value and value in text for value in protected_values)


def compatible_body(original):
    if original.get('model') != MODEL:
        raise ValueError('model')
    body = {k: v for k, v in original.items() if k in BODY_FIELDS and v is not None}
    caps = [int(original[k]) for k in ('max_completion_tokens', 'max_tokens')
            if original.get(k) is not None]
    body['max_completion_tokens'] = max(1, min([8000, *caps]))
    messages = []
    for source in body['messages']:
        item = {k: v for k, v in source.items()
                if k in {'role', 'content', 'tool_calls', 'tool_call_id'}}
        if item['role'] == 'developer':
            item['role'] = 'system'
        if item['role'] not in {'system', 'user', 'assistant', 'tool'}:
            raise ValueError('role')
        if isinstance(item.get('content'), list):
            if any(p.get('type') != 'text' for p in item['content']):
                raise ValueError('non-text-content')
            item['content'] = '\n'.join(p.get('text', '') for p in item['content'])
        if item.get('tool_calls'):
            item['tool_calls'] = [
                {'id': call['id'], 'type': 'function', 'function': {
                    k: call['function'][k] for k in ('name', 'arguments')}}
                for call in item['tool_calls']
            ]
        else:
            item.pop('tool_calls', None)
        messages.append(item)
    body['messages'] = messages
    if body.get('tools'):
        if any(t.get('type') != 'function' for t in body['tools']):
            raise ValueError('tool-type')
        tools = [{'type': 'function', 'function': {
            k: tool['function'][k] for k in ('name', 'description', 'parameters')
            if k in tool['function']}} for tool in body['tools']]
        choice = body.get('tool_choice', 'auto')
        if isinstance(choice, dict):
            name = choice.get('function', {}).get('name')
            tools = [t for t in tools if t['function']['name'] == name]
            if len(tools) != 1:
                raise ValueError('forced-tool')
            choice = 'required'
        if choice not in {'auto', 'none', 'required'}:
            raise ValueError('tool-choice')
        body.update(tools=tools, tool_choice=choice)
    else:
        if body.get('tool_choice') == 'required' or isinstance(body.get('tool_choice'), dict):
            raise ValueError('missing-tools')
        body.pop('tools', None)
        body.pop('tool_choice', None)
    return body


class RequestPacer:
    """One attempt per 10.1 seconds; 429 puts the profile on a 60.1-second cooldown."""
    def __init__(self, path: Path, clock=time.time, sleep=time.sleep):
        self.path, self.clock, self.sleep = path, clock, sleep
        path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self):
        return float(self.path.read_text()) if self.path.exists() else 0.0

    def _reserve(self, cooldown):
        with self.path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if cooldown:
                next_time = max(self._read(), self.clock() + 60.1)
            else:
                wait = self._read() - self.clock()
                if wait > 0:
                    self.sleep(wait)
                next_time = self.clock() + 10.1
            self.path.write_text(str(next_time), encoding='ascii')

    def acquire(self):
        self._reserve(False)

    def on_rate_limit(self):
        self._reserve(True)
