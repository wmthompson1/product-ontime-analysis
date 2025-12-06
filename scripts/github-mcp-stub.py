#!/usr/bin/env python3
"""
Simple GitHub MCP stub server for local testing.
Responds to:
- GET /health -> 200 OK JSON {"status":"ok","service":"github-mcp-stub"}
- GET /schema -> 200 OK JSON minimal MCP schema
- All other paths -> 404

This is intentionally minimal and single-purpose for local smoke tests.
"""
import http.server
import socketserver
import json
import os

PORT = int(os.environ.get("WEB_APP_PORT", "8081"))

class Handler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        payload = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == '/health':
            self._send_json({
                'status': 'ok',
                'service': 'github-mcp-stub'
            })
        elif self.path == '/schema':
            # Minimal example schema for testing
            self._send_json({
                'name': 'github-mcp-stub',
                'version': '0.0.1',
                'endpoints': ['/health','/schema']
            })
        else:
            self._send_json({'error': 'not found'}, status=404)

    def log_message(self, format, *args):
        # Shorter logs to stdout
        print("[stub] %s - - %s" % (self.client_address[0], format%args))

if __name__ == '__main__':
    print(f"Starting github-mcp-stub on port {PORT}")
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            httpd.server_close()
