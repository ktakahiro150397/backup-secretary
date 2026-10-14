"""Fixed, non-confidential function-call round trip through the real SDK stream."""
from __future__ import annotations

import json
from wire import MODEL


def stream_response(client, metadata, prefix, **kwargs):
    text, calls, finish = '', {}, None
    with client.with_streaming_response.chat.completions.create(
            model=MODEL, max_tokens=256, temperature=0, stream=True, **kwargs) as raw:
        metadata[prefix + '_http_status'] = raw.status_code
        metadata[prefix + '_sse'] = raw.headers.get('content-type', '').lower().startswith('text/event-stream')
        for chunk in raw.parse():
            if chunk.object != 'chat.completion.chunk' or chunk.model != MODEL:
                raise ValueError('Unexpected stream envelope')
            for choice in chunk.choices:
                if choice.index != 0:
                    continue
                text += choice.delta.content or ''
                for delta in choice.delta.tool_calls or []:
                    call = calls.setdefault(delta.index, {'id': '', 'type': 'function',
                        'function': {'name': '', 'arguments': ''}})
                    call['id'] += delta.id or ''
                    if delta.function:
                        call['function']['name'] += delta.function.name or ''
                        call['function']['arguments'] += delta.function.arguments or ''
                finish = choice.finish_reason or finish
    if not 200 <= metadata[prefix + '_http_status'] < 300 or not metadata[prefix + '_sse']:
        raise ValueError('Invalid streaming HTTP response')
    return text, list(calls.values()), finish


def check_tool_roundtrip(client, metadata=None):
    if metadata is None:
        metadata = {}
    metadata['tools_ok'] = False
    tools = [{'type': 'function', 'function': {
        'name': 'owashota_probe_add', 'description': 'Add two integers for a connectivity test.',
        'parameters': {'type': 'object', 'properties': {
            'a': {'type': 'integer'}, 'b': {'type': 'integer'}},
            'required': ['a', 'b'], 'additionalProperties': False}}}]
    messages = [{'role': 'user', 'content':
        'Call owashota_probe_add with a=2 and b=3, then report the returned sum as a digit.'}]
    _, calls, finish = stream_response(client, metadata, 'tool', messages=messages,
        tools=tools, tool_choice={'type': 'function', 'function': {'name': 'owashota_probe_add'}})
    metadata['tool_call_valid'] = (finish == 'tool_calls' and len(calls) == 1
        and bool(calls[0]['id']) and calls[0]['function']['name'] == 'owashota_probe_add')
    if not metadata['tool_call_valid']:
        raise ValueError('Expected function call was not returned')
    args = json.loads(calls[0]['function']['arguments'])
    metadata['tool_arguments_valid'] = (args == {'a': 2, 'b': 3}
        and all(type(x) is int for x in args.values()))
    if not metadata['tool_arguments_valid']:
        raise ValueError('Invalid function arguments')
    result = args['a'] + args['b']
    messages.extend([
        {'role': 'assistant', 'content': None, 'tool_calls': calls},
        {'role': 'tool', 'tool_call_id': calls[0]['id'], 'content': json.dumps({'sum': result})},
    ])
    text, followup_calls, finish = stream_response(client, metadata, 'tool_result',
        messages=messages, tools=tools, tool_choice='none')
    metadata['tool_result_text_present'] = bool(text.strip())
    metadata['tool_result_used'] = str(result) in text
    metadata['tools_ok'] = (finish == 'stop' and not followup_calls
        and metadata['tool_result_text_present'] and metadata['tool_result_used'])
    if not metadata['tools_ok']:
        raise ValueError('Tool result did not produce a completed answer')
    return metadata
