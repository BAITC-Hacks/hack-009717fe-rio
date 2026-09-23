"""SQLite schema management and idempotent CSV catalog synchronization."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .catalog import load_csv_profiles


class ManagedConnection(sqlite3.Connection):
    """Commit/rollback and close when used as a context manager."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class Database:
    def __init__(self, path: Path, source_csv: Path, migrations_dir: Path | None = None):
        self.path = Path(path)
        self.source_csv = Path(source_csv)
        self.migrations_dir = migrations_dir or Path(__file__).with_name("migrations")

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, factory=ManagedConnection)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL) WITHOUT ROWID"
            )
            applied = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
            for migration in sorted(self.migrations_dir.glob("*.sql")):
                if migration.name in applied:
                    continue
                connection.executescript(migration.read_text(encoding="utf-8"))
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (migration.name, datetime.now(timezone.utc).isoformat()),
                )
        self.sync_catalog()

    def sync_catalog(self) -> bool:
        """Replace catalog tables only when source content changed."""
        fingerprint = hashlib.sha256(self.source_csv.read_bytes()).hexdigest()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT value FROM catalog_metadata WHERE key = 'source_sha256'"
            ).fetchone()
            if row and row["value"] == fingerprint:
                return False

        profiles = load_csv_profiles(self.source_csv)
        with self.connect() as connection:
            categories = sorted({value for profile in profiles for value in profile["categories"]})
            formats = sorted({value for profile in profiles for value in profile["event_formats"]})
            languages = sorted({value for profile in profiles for value in profile["languages"]})
            connection.executemany("INSERT OR IGNORE INTO categories(name) VALUES (?)", ((v,) for v in categories))
            connection.executemany("INSERT OR IGNORE INTO event_formats(name) VALUES (?)", ((v,) for v in formats))
            connection.executemany("INSERT OR IGNORE INTO languages(name) VALUES (?)", ((v,) for v in languages))

            for profile in profiles:
                connection.execute(
                    """INSERT INTO vendors(
                        id, anon_name, city, city_imputed, synthetic, price_from_kzt,
                        price_imputed, max_hours, description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        anon_name = excluded.anon_name,
                        city = excluded.city,
                        city_imputed = excluded.city_imputed,
                        synthetic = excluded.synthetic,
                        price_from_kzt = excluded.price_from_kzt,
                        price_imputed = excluded.price_imputed,
                        max_hours = excluded.max_hours,
                        description = excluded.description""",
                    (
                        profile["id"], profile["anon_name"], profile["city"],
                        profile["city_imputed"], profile["synthetic"], profile["price_from_kzt"],
                        profile["price_imputed"], profile["max_hours"], profile["description"],
                    ),
                )
                connection.execute("DELETE FROM vendor_categories WHERE vendor_id = ?", (profile["id"],))
                connection.execute("DELETE FROM vendor_event_formats WHERE vendor_id = ?", (profile["id"],))
                connection.execute("DELETE FROM vendor_languages WHERE vendor_id = ?", (profile["id"],))
                connection.execute("DELETE FROM vendor_busy_dates WHERE vendor_id = ?", (profile["id"],))
                connection.executemany(
                    "INSERT INTO vendor_categories(vendor_id, category_name) VALUES (?, ?)",
                    ((profile["id"], value) for value in profile["categories"]),
                )
                connection.executemany(
                    "INSERT INTO vendor_event_formats(vendor_id, event_format_name) VALUES (?, ?)",
                    ((profile["id"], value) for value in profile["event_formats"]),
                )
                connection.executemany(
                    "INSERT INTO vendor_languages(vendor_id, language_name) VALUES (?, ?)",
                    ((profile["id"], value) for value in profile["languages"]),
                )
                connection.executemany(
                    "INSERT INTO vendor_busy_dates(vendor_id, busy_date) VALUES (?, ?)",
                    ((profile["id"], value) for value in profile["busy_dates"]),
                )

            source_ids = [profile["id"] for profile in profiles]
            placeholders = ",".join("?" for _ in source_ids)
            connection.execute(f"DELETE FROM vendors WHERE id NOT IN ({placeholders})", source_ids)
            connection.execute("DELETE FROM categories WHERE name NOT IN (SELECT category_name FROM vendor_categories)")
            connection.execute("DELETE FROM event_formats WHERE name NOT IN (SELECT event_format_name FROM vendor_event_formats)")
            connection.execute("DELETE FROM languages WHERE name NOT IN (SELECT language_name FROM vendor_languages)")

            metadata = {
                "source_sha256": fingerprint,
                "source_file": self.source_csv.name,
                "synced_at": datetime.now(timezone.utc).isoformat(),
                "vendor_count": str(len(profiles)),
            }
            connection.executemany(
                "INSERT OR REPLACE INTO catalog_metadata(key, value) VALUES (?, ?)", metadata.items()
            )
        return True

    def health(self) -> dict:
        with self.connect() as connection:
            connection.execute("SELECT 1").fetchone()
            count = connection.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]
            works = connection.execute("SELECT COUNT(*) FROM portfolio_works").fetchone()[0]
            ratings = connection.execute("SELECT COUNT(*) FROM work_ratings").fetchone()[0]
            version = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
        return {
            "status": "ok",
            "database": "ok",
            "vendors": count,
            "works": works,
            "ratings": ratings,
            "schema_version": version,
        }
