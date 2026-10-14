"""Container-loopback compatibility proxy. Never logs payloads, headers, or secrets."""
from __future__ import annotations

import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json

import httpx
from wire import compatible_body, contains_credentials, MODEL, UPSTREAM


class ProxyServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, key, pacer, *, upstream_transport=None, protected_values=()):
        if address[0] != '127.0.0.1':
            raise ValueError('proxy-must-be-loopback')
        self.key = key
        self.protected_values = frozenset([key, *protected_values])
        self.pacer = pacer
        self.upstream = httpx.Client(transport=upstream_transport, trust_env=False,
                                    follow_redirects=False, timeout=300)
        super().__init__(address, Handler)

    def server_close(self):
        super().server_close()
        self.upstream.close()


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *args):
        pass

    def _authorized(self):
        actual = self.headers.get('Authorization', '')
        return hmac.compare_digest(actual, 'Bearer ' + self.server.key)

    def _json(self, status, body):
        content = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(content)
        self.close_connection = True

    def do_GET(self):
        if self.path == '/health':
            return self._json(200, {'ready': bool(self.server.key), 'model': MODEL})
        if not self._authorized():
            return self._json(401, {'error': {'message': 'proxy authentication required'}})
        if self.path == '/v1/models':
            return self._json(200, {'object': 'list', 'data': [{'id': MODEL, 'object': 'model'}]})
        return self._json(404, {'error': {'message': 'unsupported endpoint'}})

    def do_POST(self):
        if not self._authorized():
            return self._json(401, {'error': {'message': 'proxy authentication required'}})
        if self.path != '/v1/chat/completions':
            return self._json(404, {'error': {'message': 'unsupported endpoint'}})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16 * 1024 * 1024:
                raise ValueError('body-size')
            body = compatible_body(json.loads(self.rfile.read(length)))
        except Exception:
            return self._json(400, {'error': {'message': 'unsupported Sarashina request shape'}})
        if contains_credentials(body, self.server.protected_values):
            return self._json(400, {'error': {'message': 'request contains credential material; forwarding blocked'}})
        try:
            self.server.pacer.acquire()
            req = self.server.upstream.build_request('POST', UPSTREAM, json=body,
                headers={'Authorization': 'Bearer ' + self.server.key, 'Content-Type': 'application/json'})
            response = self.server.upstream.send(req, stream=True)
            if response.status_code == 429:
                self.server.pacer.on_rate_limit()
        except Exception:
            return self._json(502, {'error': {'message': 'upstream connection failed'}})
        try:
            self.send_response(response.status_code)
            self.send_header('Content-Type', response.headers.get('Content-Type', 'application/json'))
            self.send_header('Connection', 'close')
            self.end_headers()
            for chunk in response.iter_bytes():
                self.wfile.write(chunk)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            response.close()
            self.close_connection = True
