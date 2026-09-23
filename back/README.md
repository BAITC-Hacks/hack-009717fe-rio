# Rio backend

`back/` is the server-side counterpart to `web/`.

- `database.py` applies SQLite migrations and synchronizes the vendor seed catalog.
- `repository.py` reads vendors and calendars, publishes portfolio works, stores one rating per client/work pair and ranks works.
- `recommendations.py` contains deterministic matching business rules.
- `http.py` exposes the versioned JSON API and serves `web/` in local development.
- `migrations/` is the complete reproducible database schema.

Start from the repository root with `python app.py`. See `docs/backend-api.ru.md` and `docs/openapi.json` for the frontend contract.
