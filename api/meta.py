import json
from http.server import BaseHTTPRequestHandler

from app import END, OPTIONS, PROFILES, START, demos


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        payload = {
            'options': OPTIONS,
            'count': len(PROFILES),
            'synthetic': sum(profile['synthetic'] for profile in PROFILES),
            'start': START,
            'end': END,
            'demos': demos(),
        }
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
