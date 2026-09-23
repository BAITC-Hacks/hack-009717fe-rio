"""Repository for vendors, portfolio works and client ratings."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from .database import Database


class VendorRepository:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _profile(row, relations: dict[str, dict[str, list[str]]]) -> dict:
        identifier = row["id"]
        return {
            "id": identifier,
            "anon_name": row["anon_name"],
            "categories": relations["categories"].get(identifier, []),
            "city": row["city"],
            "city_imputed": bool(row["city_imputed"]),
            "synthetic": bool(row["synthetic"]),
            "price_from_kzt": row["price_from_kzt"],
            "price_imputed": bool(row["price_imputed"]),
            "event_formats": relations["event_formats"].get(identifier, []),
            "languages": relations["languages"].get(identifier, []),
            "max_hours": row["max_hours"],
            "busy_dates": relations["busy_dates"].get(identifier, []),
            "description": row["description"],
        }

    def _relations(self, connection, identifiers: list[str]) -> dict[str, dict[str, list[str]]]:
        result = {key: {} for key in ("categories", "event_formats", "languages", "busy_dates")}
        if not identifiers:
            return result
        placeholders = ",".join("?" for _ in identifiers)
        tables = {
            "categories": ("vendor_categories", "category_name"),
            "event_formats": ("vendor_event_formats", "event_format_name"),
            "languages": ("vendor_languages", "language_name"),
            "busy_dates": ("vendor_busy_dates", "busy_date"),
        }
        for key, (table, column) in tables.items():
            query = f"SELECT vendor_id, {column} AS value FROM {table} WHERE vendor_id IN ({placeholders}) ORDER BY vendor_id, value"
            for row in connection.execute(query, identifiers):
                result[key].setdefault(row["vendor_id"], []).append(row["value"])
        return result

    def load_profiles(self) -> list[dict]:
        with self.database.connect() as connection:
            rows = connection.execute("SELECT * FROM vendors ORDER BY id").fetchall()
            relations = self._relations(connection, [row["id"] for row in rows])
        return [self._profile(row, relations) for row in rows]

    def get(self, identifier: str) -> dict | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM vendors WHERE id = ?", (identifier,)).fetchone()
            if row is None:
                return None
            relations = self._relations(connection, [identifier])
        return self._profile(row, relations)

    def options(self) -> dict[str, list[str]]:
        with self.database.connect() as connection:
            return {
                "city": [row[0] for row in connection.execute("SELECT DISTINCT city FROM vendors ORDER BY city")],
                "categories": [row[0] for row in connection.execute("SELECT name FROM categories ORDER BY name")],
                "event_formats": [row[0] for row in connection.execute("SELECT name FROM event_formats ORDER BY name")],
                "languages": [row[0] for row in connection.execute("SELECT name FROM languages ORDER BY name")],
            }

    def stats(self) -> dict[str, int]:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count, SUM(synthetic) AS synthetic FROM vendors"
            ).fetchone()
        return {"count": row["count"], "synthetic": row["synthetic"] or 0}

    def list(self, filters: dict, limit: int, offset: int) -> tuple[list[dict], int]:
        clauses: list[str] = []
        values: list[object] = []
        direct = {"city": "v.city = ?", "budget_lte": "v.price_from_kzt <= ?"}
        for key, clause in direct.items():
            if filters.get(key) is not None:
                clauses.append(clause)
                values.append(filters[key])
        relation_filters = {
            "category": ("vendor_categories", "category_name"),
            "event_format": ("vendor_event_formats", "event_format_name"),
            "language": ("vendor_languages", "language_name"),
        }
        for key, (table, column) in relation_filters.items():
            if filters.get(key):
                clauses.append(f"EXISTS (SELECT 1 FROM {table} r WHERE r.vendor_id = v.id AND r.{column} = ?)")
                values.append(filters[key])
        if filters.get("available_on"):
            clauses.append("NOT EXISTS (SELECT 1 FROM vendor_busy_dates b WHERE b.vendor_id = v.id AND b.busy_date = ?)")
            values.append(filters["available_on"])
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.database.connect() as connection:
            total = connection.execute(f"SELECT COUNT(*) FROM vendors v{where}", values).fetchone()[0]
            rows = connection.execute(
                f"SELECT v.* FROM vendors v{where} ORDER BY v.price_from_kzt, v.id LIMIT ? OFFSET ?",
                [*values, limit, offset],
            ).fetchall()
            relations = self._relations(connection, [row["id"] for row in rows])
        return [self._profile(row, relations) for row in rows], total

    def availability(self, identifier: str, start: date, end: date) -> dict | None:
        if not self.get(identifier):
            return None
        with self.database.connect() as connection:
            busy = {
                row[0] for row in connection.execute(
                    "SELECT busy_date FROM vendor_busy_dates WHERE vendor_id = ? AND busy_date BETWEEN ? AND ? ORDER BY busy_date",
                    (identifier, start.isoformat(), end.isoformat()),
                )
            }
        days = []
        current = start
        while current <= end:
            value = current.isoformat()
            days.append({"date": value, "available": value not in busy})
            current += timedelta(days=1)
        return {
            "vendor_id": identifier,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": days,
        }

    @staticmethod
    def _ranking_score(average: float, count: int, global_average: float) -> float:
        """Bayesian score: quality matters, while one vote cannot dominate the top."""
        if count == 0:
            return 0.0
        confidence_votes = 5
        score = (
            count / (count + confidence_votes) * average
            + confidence_votes / (count + confidence_votes) * global_average
        )
        return round(score, 4)

    @staticmethod
    def _work(row, media: dict[str, list[str]], global_average: float) -> dict:
        count = int(row["rating_count"] or 0)
        average = round(float(row["rating_average"] or 0), 2)
        return {
            "id": row["id"],
            "vendor_id": row["vendor_id"],
            "title": row["title"],
            "description": row["description"],
            "event_format": row["event_format"],
            "city": row["city"],
            "occurred_on": row["occurred_on"],
            "media_urls": media.get(row["id"], []),
            "published_at": row["published_at"],
            "updated_at": row["updated_at"],
            "rating_average": average,
            "rating_count": count,
            "ranking_score": VendorRepository._ranking_score(average, count, global_average),
        }

    @staticmethod
    def _work_rows(connection, vendor_id: str | None = None):
        where = "WHERE w.vendor_id = ?" if vendor_id else ""
        values = (vendor_id,) if vendor_id else ()
        return connection.execute(
            f"""SELECT w.*, COUNT(r.score) AS rating_count, AVG(r.score) AS rating_average
                FROM portfolio_works w
                LEFT JOIN work_ratings r ON r.work_id = w.id
                {where}
                GROUP BY w.id""",
            values,
        ).fetchall()

    @staticmethod
    def _media(connection, work_ids: list[str]) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        if not work_ids:
            return result
        placeholders = ",".join("?" for _ in work_ids)
        rows = connection.execute(
            f"SELECT work_id, media_url FROM work_media WHERE work_id IN ({placeholders}) ORDER BY work_id, sort_order",
            work_ids,
        )
        for row in rows:
            result.setdefault(row["work_id"], []).append(row["media_url"])
        return result

    def list_works(self, vendor_id: str | None, limit: int, offset: int) -> tuple[list[dict], int]:
        with self.database.connect() as connection:
            rows = self._work_rows(connection, vendor_id)
            global_average = float(
                connection.execute("SELECT COALESCE(AVG(score), 3.0) FROM work_ratings").fetchone()[0]
            )
            media = self._media(connection, [row["id"] for row in rows])
        works = [self._work(row, media, global_average) for row in rows]

        def ranking_key(work: dict):
            published = datetime.fromisoformat(work["published_at"]).timestamp()
            return (
                -work["ranking_score"],
                -work["rating_average"],
                -work["rating_count"],
                -published,
                work["id"],
            )

        works.sort(key=ranking_key)
        return works[offset:offset + limit], len(works)

    def get_work(self, identifier: str) -> dict | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """SELECT w.*, COUNT(r.score) AS rating_count, AVG(r.score) AS rating_average
                   FROM portfolio_works w
                   LEFT JOIN work_ratings r ON r.work_id = w.id
                   WHERE w.id = ? GROUP BY w.id""",
                (identifier,),
            ).fetchone()
            if row is None:
                return None
            global_average = float(
                connection.execute("SELECT COALESCE(AVG(score), 3.0) FROM work_ratings").fetchone()[0]
            )
            media = self._media(connection, [identifier])
            reviews = [
                {
                    "client_name": review["client_name"] or "Клиент Rio",
                    "score": review["score"],
                    "comment": review["comment"] or "",
                    "updated_at": review["updated_at"],
                }
                for review in connection.execute(
                    """SELECT client_name, score, comment, updated_at
                       FROM work_ratings WHERE work_id = ?
                       ORDER BY updated_at DESC, client_id LIMIT 20""",
                    (identifier,),
                )
            ]
        work = self._work(row, media, global_average)
        work["reviews"] = reviews
        return work

    def create_work(self, vendor_id: str, payload: dict) -> dict:
        identifier = "work_" + uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO portfolio_works(
                    id, vendor_id, title, description, event_format, city,
                    occurred_on, published_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    identifier,
                    vendor_id,
                    payload["title"],
                    payload["description"],
                    payload.get("event_format"),
                    payload.get("city"),
                    payload.get("occurred_on"),
                    now,
                    now,
                ),
            )
            connection.executemany(
                "INSERT INTO work_media(work_id, media_url, sort_order) VALUES (?, ?, ?)",
                ((identifier, url, index) for index, url in enumerate(payload.get("media_urls", []))),
            )
        return self.get_work(identifier)

    def rate_work(self, work_id: str, payload: dict) -> dict | None:
        if not self.get_work(work_id):
            return None
        now = datetime.now(timezone.utc).isoformat()
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO work_ratings(
                    work_id, client_id, client_name, score, comment, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(work_id, client_id) DO UPDATE SET
                    client_name = excluded.client_name,
                    score = excluded.score,
                    comment = excluded.comment,
                    updated_at = excluded.updated_at""",
                (
                    work_id,
                    payload["client_id"],
                    payload.get("client_name"),
                    payload["score"],
                    payload.get("comment"),
                    now,
                    now,
                ),
            )
        return self.get_work(work_id)
