"""Rio backend entrypoint and backwards-compatible business API."""

from __future__ import annotations

import argparse
import os
from http.server import ThreadingHTTPServer
from pathlib import Path

from back.database import Database
from back.demo import seed_demo_portfolio
from back.http import BackendApplication, create_handler
from back.recommendations import END, START, RecommendationService, rejection_reasons


ROOT = Path(__file__).resolve().parent
DEFAULT_DB_PATH = Path(os.getenv(
    "RIO_DB_PATH",
    "/tmp/rio.sqlite3" if os.getenv("VERCEL") else ROOT / "data" / "rio.sqlite3",
))
DATABASE = Database(DEFAULT_DB_PATH, ROOT / "data" / "contractors.csv")
APPLICATION = BackendApplication(DATABASE)
seed_demo_portfolio(DATABASE)
PROFILES = APPLICATION.service.profiles
OPTIONS = APPLICATION.service.options


def load_profiles() -> list[dict]:
    """Return catalog profiles from SQLite (kept for existing integrations)."""
    return APPLICATION.repository.load_profiles()


def validate(query: dict) -> None:
    APPLICATION.service.validate(query)


def reasons(profile: dict, query: dict) -> list[str]:
    return rejection_reasons(profile, query)


def recommend(query: dict, profiles: list[dict] | None = None) -> dict:
    service = APPLICATION.service if profiles is None else RecommendationService(profiles)
    return service.recommend(query)


def demos() -> list[dict]:
    return APPLICATION.service.demos()


Handler = create_handler(APPLICATION, ROOT / "web", ROOT / "docs" / "openapi.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Rio vendor recommendation backend")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--init-db", action="store_true", help="initialize/sync the database and exit")
    args = parser.parse_args()

    application = APPLICATION
    handler = Handler
    if args.db.resolve() != DEFAULT_DB_PATH.resolve():
        application = BackendApplication(Database(args.db, ROOT / "data" / "contractors.csv"))
        seed_demo_portfolio(application.database)
        handler = create_handler(application, ROOT / "web", ROOT / "docs" / "openapi.json")
    if args.init_db:
        print(f"Database ready: {args.db} ({application.repository.stats()['count']} vendors)")
        return

    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Rio API: http://{args.host}:{args.port}/api/v1", flush=True)
    print(f"OpenAPI: http://{args.host}:{args.port}/api/openapi.json", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
