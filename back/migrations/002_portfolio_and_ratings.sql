PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS portfolio_works (
    id TEXT PRIMARY KEY,
    vendor_id TEXT NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 120),
    description TEXT NOT NULL CHECK (length(description) BETWEEN 1 AND 2000),
    event_format TEXT,
    city TEXT,
    occurred_on TEXT CHECK (occurred_on IS NULL OR length(occurred_on) = 10),
    published_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS work_media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id TEXT NOT NULL REFERENCES portfolio_works(id) ON DELETE CASCADE,
    media_url TEXT NOT NULL CHECK (length(media_url) BETWEEN 1 AND 500),
    sort_order INTEGER NOT NULL CHECK (sort_order BETWEEN 0 AND 9),
    UNIQUE (work_id, sort_order)
);

CREATE TABLE IF NOT EXISTS work_ratings (
    work_id TEXT NOT NULL REFERENCES portfolio_works(id) ON DELETE CASCADE,
    client_id TEXT NOT NULL CHECK (length(client_id) BETWEEN 3 AND 64),
    client_name TEXT CHECK (client_name IS NULL OR length(client_name) <= 80),
    score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5),
    comment TEXT CHECK (comment IS NULL OR length(comment) <= 1000),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (work_id, client_id)
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS idx_portfolio_works_vendor_published
    ON portfolio_works(vendor_id, published_at DESC, id);
CREATE INDEX IF NOT EXISTS idx_work_ratings_work_score
    ON work_ratings(work_id, score DESC);
