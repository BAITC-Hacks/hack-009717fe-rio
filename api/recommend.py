import json
from http.server import BaseHTTPRequestHandler
from time import perf_counter

from app import recommend


class handler(BaseHTTPRequestHandler):
    def respond(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 16000:
                raise ValueError('Некорректный размер запроса.')
            query = json.loads(self.rfile.read(size))
            started = perf_counter()
            result = recommend(query)
            result['elapsed_ms'] = round((perf_counter() - started) * 1000, 2)
            self.respond(result)
        except (ValueError, TypeError, UnicodeError) as exc:
            self.respond({'error': str(exc)}, 400)
