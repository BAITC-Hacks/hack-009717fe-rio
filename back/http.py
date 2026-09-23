"""HTTP transport for the Rio backend."""

from __future__ import annotations

import json
import os
import re
from datetime import date
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from time import perf_counter
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from .database import Database
from .recommendations import END, START, RecommendationService
from .repository import VendorRepository


class APIError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details


class BackendApplication:
    def __init__(self, database: Database):
        self.database = database
        self.database.initialize()
        self.repository = VendorRepository(database)
        self.service = RecommendationService(self.repository.load_profiles(), self.repository.options())

    def meta(self) -> dict:
        return {
            "options": self.repository.options(),
            **self.repository.stats(),
            "start": START,
            "end": END,
            "demos": self.service.demos(),
            "api_version": "v1",
            "work_ranking": "bayesian_rating",
        }

    def vendor_with_works(self, identifier: str) -> dict | None:
        profile = self.repository.get(identifier)
        if not profile:
            return None
        works, total = self.repository.list_works(identifier, 3, 0)
        profile["top_works"] = works
        profile["published_work_count"] = total
        return profile

    def recommend(self, payload: dict) -> dict:
        result = self.service.recommend(payload)
        podium = ("gold", "silver", "bronze")
        for index, card in enumerate(result["cards"]):
            card["rank"] = index + 1
            card["medal"] = podium[index]
            works, total = self.repository.list_works(card["id"], 3, 0)
            card["top_works"] = works
            card["published_work_count"] = total
        return result


def _one(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    if not values:
        return None
    if len(values) != 1:
        raise APIError(400, "invalid_query", f"Параметр {key} должен быть указан один раз.")
    return values[0]


def _positive_int(value: str | None, name: str, default: int, maximum: int) -> int:
    if value is None:
        return default
    try:
        number = int(value)
    except ValueError:
        raise APIError(400, "invalid_query", f"Параметр {name} должен быть целым числом.") from None
    if number < 0 or number > maximum or (name == "limit" and number == 0):
        raise APIError(400, "invalid_query", f"Параметр {name} вне допустимого диапазона.")
    return number


def _calendar_date(value: str | None, name: str) -> date:
    if not value:
        raise APIError(400, "invalid_query", f"Параметр {name} обязателен.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise APIError(400, "invalid_query", f"Параметр {name} должен быть датой YYYY-MM-DD.") from None
    if not START <= parsed.isoformat() <= END:
        raise APIError(400, "calendar_out_of_range", "Дата выходит за границы календаря каталога.")
    return parsed


def _work_payload(payload: object, options: dict[str, list[str]]) -> dict:
    if not isinstance(payload, dict):
        raise APIError(422, "validation_error", "Работа должна быть JSON-объектом.")

    def required_text(name: str, maximum: int) -> str:
        value = payload.get(name)
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
            raise APIError(422, "validation_error", f"Поле {name}: от 1 до {maximum} символов.")
        return value.strip()

    result = {
        "title": required_text("title", 120),
        "description": required_text("description", 2000),
    }
    for name, maximum in (("event_format", 80), ("city", 120)):
        value = payload.get(name)
        if value not in (None, ""):
            if not isinstance(value, str) or len(value.strip()) > maximum:
                raise APIError(422, "validation_error", f"Некорректное поле {name}.")
            result[name] = value.strip()
    if result.get("event_format") and result["event_format"] not in options["event_formats"]:
        raise APIError(422, "validation_error", "Неизвестный формат мероприятия.")
    if result.get("city") and result["city"] not in options["city"]:
        raise APIError(422, "validation_error", "Неизвестный город.")

    occurred_on = payload.get("occurred_on")
    if occurred_on not in (None, ""):
        if not isinstance(occurred_on, str):
            raise APIError(422, "validation_error", "occurred_on должен быть датой YYYY-MM-DD.")
        try:
            date.fromisoformat(occurred_on)
        except ValueError:
            raise APIError(422, "validation_error", "occurred_on должен быть датой YYYY-MM-DD.") from None
        result["occurred_on"] = occurred_on

    media_urls = payload.get("media_urls", [])
    if not isinstance(media_urls, list) or len(media_urls) > 10:
        raise APIError(422, "validation_error", "media_urls должен содержать не больше 10 ссылок.")
    clean_urls = []
    for url in media_urls:
        if not isinstance(url, str) or len(url) > 500:
            raise APIError(422, "validation_error", "Некорректная ссылка в media_urls.")
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise APIError(422, "validation_error", "Медиа-ссылки должны использовать http или https.")
        clean_urls.append(url)
    result["media_urls"] = clean_urls
    return result


def _rating_payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise APIError(422, "validation_error", "Оценка должна быть JSON-объектом.")
    client_id = payload.get("client_id")
    if not isinstance(client_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{3,64}", client_id):
        raise APIError(422, "validation_error", "client_id: 3–64 латинских букв, цифр, '_' или '-'.")
    score = payload.get("score")
    if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 5:
        raise APIError(422, "validation_error", "Оценка score должна быть целым числом от 1 до 5.")
    result = {"client_id": client_id, "score": score}
    for name, maximum in (("client_name", 80), ("comment", 1000)):
        value = payload.get(name)
        if value not in (None, ""):
            if not isinstance(value, str) or len(value.strip()) > maximum:
                raise APIError(422, "validation_error", f"Поле {name}: максимум {maximum} символов.")
            result[name] = value.strip()
    return result


def create_handler(application: BackendApplication, web_root: Path, openapi_path: Path):
    allowed_origins = {
        value.strip()
        for value in os.getenv(
            "RIO_CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if value.strip()
    }

    class Handler(SimpleHTTPRequestHandler):
        server_version = "Rio/1.0"

        def __init__(self, *args, **kwargs):
            self.request_id = uuid4().hex[:16]
            super().__init__(*args, directory=str(web_root), **kwargs)

        def end_headers(self):
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Request-Id", self.request_id)
            origin = self.headers.get("Origin")
            if origin and (origin in allowed_origins or "*" in allowed_origins):
                self.send_header("Access-Control-Allow-Origin", "*" if "*" in allowed_origins else origin)
                self.send_header("Vary", "Origin")
            super().end_headers()

        def json_response(self, value: dict, status: int = 200):
            body = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def api_error(self, error: APIError):
            payload = {"error": error.message, "code": error.code, "request_id": self.request_id}
            if error.details:
                payload["details"] = error.details
            self.json_response(payload, error.status)

        def do_OPTIONS(self):
            path = urlsplit(self.path).path
            if not path.startswith("/api/"):
                return self.api_error(APIError(404, "not_found", "Маршрут не найден."))
            self.send_response(204)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Request-Id")
            self.send_header("Access-Control-Max-Age", "600")
            self.end_headers()

        def do_GET(self):
            try:
                parsed = urlsplit(self.path)
                path = parsed.path.rstrip("/") or "/"
                query = parse_qs(parsed.query, keep_blank_values=True)
                if path in {"/api/health", "/api/v1/health"}:
                    return self.json_response(application.database.health())
                if path in {"/api/meta", "/api/v1/meta"}:
                    return self.json_response(application.meta())
                if path in {"/api/openapi.json", "/api/v1/openapi.json"}:
                    return self._openapi()
                if path == "/api/v1/vendors":
                    return self._vendors(query)
                if path == "/api/v1/works":
                    return self._works(query)
                availability = re.fullmatch(r"/api/v1/vendors/([^/]+)/availability", path)
                if availability:
                    return self._availability(availability.group(1), query)
                vendor_works = re.fullmatch(r"/api/v1/vendors/([^/]+)/works", path)
                if vendor_works:
                    return self._works(query, vendor_works.group(1))
                work = re.fullmatch(r"/api/v1/works/([^/]+)", path)
                if work:
                    item = application.repository.get_work(work.group(1))
                    if not item:
                        raise APIError(404, "work_not_found", "Работа не найдена.")
                    return self.json_response({"data": item})
                vendor = re.fullmatch(r"/api/v1/vendors/([^/]+)", path)
                if vendor:
                    profile = application.vendor_with_works(vendor.group(1))
                    if not profile:
                        raise APIError(404, "vendor_not_found", "Подрядчик не найден.")
                    return self.json_response({"data": profile})
                if path.startswith("/api/"):
                    raise APIError(404, "not_found", "Маршрут не найден.")
                if path not in {"/", "/index.html", "/app.js", "/style.css"}:
                    raise APIError(404, "not_found", "Страница не найдена.")
                return super().do_GET()
            except APIError as error:
                return self.api_error(error)
            except Exception:
                return self.api_error(APIError(500, "internal_error", "Внутренняя ошибка сервера."))

        def do_POST(self):
            try:
                path = urlsplit(self.path).path.rstrip("/")
                payload = self._read_json()
                if path in {"/api/recommend", "/api/v1/recommendations"}:
                    started = perf_counter()
                    try:
                        result = application.recommend(payload)
                    except (ValueError, TypeError) as error:
                        raise APIError(422, "validation_error", str(error)) from None
                    result["elapsed_ms"] = round((perf_counter() - started) * 1000, 2)
                    result["request_id"] = self.request_id
                    return self.json_response(result)

                vendor_works = re.fullmatch(r"/api/v1/vendors/([^/]+)/works", path)
                if vendor_works:
                    vendor_id = vendor_works.group(1)
                    if not application.repository.get(vendor_id):
                        raise APIError(404, "vendor_not_found", "Подрядчик не найден.")
                    work = application.repository.create_work(
                        vendor_id, _work_payload(payload, application.repository.options())
                    )
                    return self.json_response({"data": work}, 201)

                rating = re.fullmatch(r"/api/v1/works/([^/]+)/ratings", path)
                if rating:
                    work = application.repository.rate_work(rating.group(1), _rating_payload(payload))
                    if not work:
                        raise APIError(404, "work_not_found", "Работа не найдена.")
                    return self.json_response({"data": work})
                raise APIError(404, "not_found", "Маршрут не найден.")
            except APIError as error:
                return self.api_error(error)
            except Exception:
                return self.api_error(APIError(500, "internal_error", "Внутренняя ошибка сервера."))

        def _read_json(self) -> object:
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/json":
                raise APIError(415, "unsupported_media_type", "Используйте Content-Type: application/json.")
            try:
                size = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                raise APIError(400, "invalid_body", "Некорректный размер запроса.") from None
            if not 0 < size <= 16000:
                raise APIError(413 if size > 16000 else 400, "invalid_body", "Некорректный размер запроса.")
            try:
                return json.loads(self.rfile.read(size))
            except (json.JSONDecodeError, UnicodeError):
                raise APIError(400, "invalid_json", "Тело запроса должно быть корректным JSON.") from None

        def _openapi(self):
            body = openapi_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "public, max-age=300")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _vendors(self, query: dict[str, list[str]]):
            budget = _one(query, "budget_lte")
            try:
                budget_value = int(budget) if budget is not None else None
            except ValueError:
                raise APIError(400, "invalid_query", "budget_lte должен быть целым числом.") from None
            if budget_value is not None and budget_value <= 0:
                raise APIError(400, "invalid_query", "budget_lte должен быть положительным.")
            available_on = _one(query, "available_on")
            if available_on is not None:
                _calendar_date(available_on, "available_on")
            filters = {
                "q": _one(query, "q"),
                "city": _one(query, "city"),
                "category": _one(query, "category"),
                "event_format": _one(query, "event_format"),
                "language": _one(query, "language"),
                "available_on": available_on,
                "budget_lte": budget_value,
            }
            limit = _positive_int(_one(query, "limit"), "limit", 20, 100)
            offset = _positive_int(_one(query, "offset"), "offset", 0, 100000)
            items, total = application.repository.list(filters, limit, offset)
            return self.json_response({
                "data": items,
                "pagination": {"limit": limit, "offset": offset, "total": total},
            })

        def _availability(self, identifier: str, query: dict[str, list[str]]):
            start = _calendar_date(_one(query, "from") or START, "from")
            end = _calendar_date(_one(query, "to") or END, "to")
            if end < start:
                raise APIError(400, "invalid_query", "Дата to не может быть раньше from.")
            result = application.repository.availability(identifier, start, end)
            if not result:
                raise APIError(404, "vendor_not_found", "Подрядчик не найден.")
            return self.json_response({"data": result})

        def _works(self, query: dict[str, list[str]], vendor_id: str | None = None):
            requested_vendor = vendor_id or _one(query, "vendor_id")
            if requested_vendor and not application.repository.get(requested_vendor):
                raise APIError(404, "vendor_not_found", "Подрядчик не найден.")
            limit = _positive_int(_one(query, "limit"), "limit", 20, 100)
            offset = _positive_int(_one(query, "offset"), "offset", 0, 100000)
            items, total = application.repository.list_works(requested_vendor, limit, offset)
            return self.json_response({
                "data": items,
                "pagination": {"limit": limit, "offset": offset, "total": total},
                "ranking": "bayesian_rating",
            })

        def log_message(self, format, *args):
            super().log_message("[%s] %s", self.request_id, format % args)

    return Handler
