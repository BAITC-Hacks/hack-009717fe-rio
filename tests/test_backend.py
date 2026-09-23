"""Database and HTTP contract integration tests."""

import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from back.database import Database
from back.http import BackendApplication, create_handler
from back.repository import VendorRepository


ROOT = Path(__file__).resolve().parents[1]


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp.name) / "rio.sqlite3", ROOT / "data" / "contractors.csv")
        self.database.initialize()
        self.repository = VendorRepository(self.database)

    def tearDown(self):
        self.temp.cleanup()

    def test_normalized_import_and_idempotency(self):
        self.assertEqual(self.repository.stats(), {"count": 200, "synthetic": 147})
        self.assertFalse(self.database.sync_catalog())
        with self.database.connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM vendor_categories").fetchone()[0], 223)
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
            self.assertTrue(connection.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_busy_dates_date'").fetchone())

    def test_repository_filters_and_availability(self):
        items, total = self.repository.list(
            {"city": "Алматы", "category": "Ведущий", "available_on": "2026-10-04", "budget_lte": 1500000},
            100,
            0,
        )
        self.assertEqual(total, len(items))
        self.assertTrue(items)
        self.assertTrue(all("Ведущий" in item["categories"] for item in items))
        self.assertTrue(all("2026-10-04" not in item["busy_dates"] for item in items))
        calendar = self.repository.availability(items[0]["id"], __import__("datetime").date(2026, 10, 1), __import__("datetime").date(2026, 10, 3))
        self.assertEqual(len(calendar["days"]), 3)

    def test_works_ratings_ranking_and_catalog_resync(self):
        vendor_id = self.repository.load_profiles()[0]["id"]
        excellent = self.repository.create_work(vendor_id, {
            "title": "Сильная работа",
            "description": "Полное оформление события.",
            "event_format": "корпоратив",
            "city": "Алматы",
            "media_urls": ["https://example.com/excellent.jpg"],
        })
        average = self.repository.create_work(vendor_id, {
            "title": "Обычная работа",
            "description": "Ещё один проект.",
            "media_urls": [],
        })
        for index in range(6):
            self.repository.rate_work(excellent["id"], {
                "client_id": f"client_{index}", "client_name": f"Клиент {index}", "score": 5,
            })
        self.repository.rate_work(average["id"], {"client_id": "client_average", "score": 3})
        works, total = self.repository.list_works(vendor_id, 20, 0)
        self.assertEqual(total, 2)
        self.assertEqual(works[0]["id"], excellent["id"])
        self.assertGreater(works[0]["ranking_score"], works[1]["ranking_score"])

        self.repository.rate_work(excellent["id"], {"client_id": "client_0", "score": 4})
        updated = self.repository.get_work(excellent["id"])
        self.assertEqual(updated["rating_count"], 6, "one client must update, not duplicate, a rating")
        with self.database.connect() as connection:
            connection.execute("UPDATE catalog_metadata SET value = 'force-resync' WHERE key = 'source_sha256'")
        self.assertTrue(self.database.sync_catalog())
        self.assertIsNotNone(self.repository.get_work(excellent["id"]), "catalog refresh must preserve portfolio")


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        database = Database(Path(cls.temp.name) / "rio.sqlite3", ROOT / "data" / "contractors.csv")
        application = BackendApplication(database)
        handler = create_handler(application, ROOT / "web", ROOT / "docs" / "openapi.json")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temp.cleanup()

    @classmethod
    def get_json(cls, path):
        with urlopen(cls.base + path, timeout=5) as response:
            return response.status, dict(response.headers), json.load(response)

    def test_health_meta_catalog_and_card(self):
        status, _, health = self.get_json("/api/v1/health")
        self.assertEqual((status, health["vendors"]), (200, 200))
        _, _, meta = self.get_json("/api/v1/meta")
        self.assertEqual(meta["api_version"], "v1")
        path = "/api/v1/vendors?city=" + quote("Алматы") + "&category=" + quote("Ведущий") + "&limit=2"
        _, _, page = self.get_json(path)
        self.assertEqual(len(page["data"]), 2)
        identifier = page["data"][0]["id"]
        _, _, card = self.get_json(f"/api/v1/vendors/{identifier}")
        self.assertEqual(card["data"]["id"], identifier)
        _, _, calendar = self.get_json(f"/api/v1/vendors/{identifier}/availability?from=2026-10-01&to=2026-10-03")
        self.assertEqual(len(calendar["data"]["days"]), 3)

    def test_recommendation_and_validation_error(self):
        payload = {"city": "Алматы", "category": "Ведущий", "event_format": "корпоратив", "date": "2026-10-01", "budget": 1500000, "hours": 4, "language": "русский", "preferences": "юмор"}
        request = Request(self.base + "/api/v1/recommendations", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=5) as response:
            body = json.load(response)
            self.assertEqual(response.status, 200)
            self.assertLessEqual(len(body["cards"]), 3)
            for card in body["cards"]:
                self.assertIn("top_works", card)
                self.assertIn("published_work_count", card)
            self.assertIn("X-Request-Id", response.headers)
        payload["budget"] = 0
        bad = Request(self.base + "/api/v1/recommendations", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with self.assertRaises(HTTPError) as caught:
            urlopen(bad, timeout=5)
        self.assertEqual(caught.exception.code, 422)
        error = json.load(caught.exception)
        self.assertEqual(error["code"], "validation_error")

    def test_openapi_and_not_found(self):
        _, _, specification = self.get_json("/api/openapi.json")
        self.assertEqual(specification["openapi"], "3.1.0")
        with self.assertRaises(HTTPError) as caught:
            self.get_json("/api/v1/vendors/DOES-NOT-EXIST")
        self.assertEqual(caught.exception.code, 404)

    def test_publish_rate_and_list_work(self):
        _, _, page = self.get_json("/api/v1/vendors?limit=1")
        vendor_id = page["data"][0]["id"]
        publish = Request(
            self.base + f"/api/v1/vendors/{vendor_id}/works",
            data=json.dumps({
                "title": "Портфолио API",
                "description": "Работа, опубликованная интеграционным тестом.",
                "media_urls": ["https://example.com/work.jpg"],
            }).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(publish, timeout=5) as response:
            self.assertEqual(response.status, 201)
            work = json.load(response)["data"]
        rate = Request(
            self.base + f"/api/v1/works/{work['id']}/ratings",
            data=json.dumps({"client_id": "integration_client", "score": 5, "comment": "Отлично"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(rate, timeout=5) as response:
            rated = json.load(response)["data"]
        self.assertEqual((rated["rating_average"], rated["rating_count"]), (5.0, 1))
        _, _, works = self.get_json(f"/api/v1/vendors/{vendor_id}/works")
        self.assertEqual(works["data"][0]["id"], work["id"])


if __name__ == "__main__":
    unittest.main()
