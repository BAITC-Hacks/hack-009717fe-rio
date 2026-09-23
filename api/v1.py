"""Vercel adapter for the frontend-facing Rio API v1 endpoints."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from time import perf_counter
from urllib.parse import parse_qs, urlsplit

from app import APPLICATION
from back.http import APIError, _rating_payload


class handler(BaseHTTPRequestHandler):
    def respond(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def route(self) -> tuple[str, dict[str, list[str]]]:
        query = parse_qs(urlsplit(self.path).query)
        return query.get("route", [""])[0].strip("/"), query

    def json_body(self) -> object:
        size = int(self.headers.get("Content-Length", "0"))
        if not 0 < size <= 16000:
            raise ValueError("Некорректный размер запроса.")
        return json.loads(self.rfile.read(size))

    def do_GET(self) -> None:
        route, _ = self.route()
        if route == "meta":
            return self.respond(APPLICATION.meta())
        if route == "health":
            return self.respond(APPLICATION.database.health())
        return self.respond({"error": "Маршрут не найден.", "code": "not_found"}, 404)

    def do_POST(self) -> None:
        route, query = self.route()
        try:
            payload = self.json_body()
            if route == "recommendations":
                started = perf_counter()
                result = APPLICATION.recommend(payload)
                result["elapsed_ms"] = round((perf_counter() - started) * 1000, 2)
                return self.respond(result)
            if route == "ratings":
                work_id = query.get("work_id", [""])[0]
                rated = APPLICATION.repository.rate_work(
                    work_id,
                    _rating_payload(payload),
                )
                if rated is None:
                    return self.respond({"error": "Работа не найдена.", "code": "work_not_found"}, 404)
                return self.respond({"data": rated})
            return self.respond({"error": "Маршрут не найден.", "code": "not_found"}, 404)
        except APIError as error:
            self.respond({"error": error.message, "code": error.code}, error.status)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.respond({"error": str(error), "code": "invalid_request"}, 400)
