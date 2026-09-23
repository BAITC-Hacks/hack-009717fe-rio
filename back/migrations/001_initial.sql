PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS catalog_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS vendors (
    id TEXT PRIMARY KEY,
    anon_name TEXT NOT NULL,
    city TEXT NOT NULL,
    city_imputed INTEGER NOT NULL CHECK (city_imputed IN (0, 1)),
    synthetic INTEGER NOT NULL CHECK (synthetic IN (0, 1)),
    price_from_kzt INTEGER NOT NULL CHECK (price_from_kzt > 0),
    price_imputed INTEGER NOT NULL CHECK (price_imputed IN (0, 1)),
    max_hours REAL CHECK (max_hours IS NULL OR max_hours > 0),
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    name TEXT PRIMARY KEY
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS event_formats (
    name TEXT PRIMARY KEY
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS languages (
    name TEXT PRIMARY KEY
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS vendor_categories (
    vendor_id TEXT NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    category_name TEXT NOT NULL REFERENCES categories(name),
    PRIMARY KEY (vendor_id, category_name)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS vendor_event_formats (
    vendor_id TEXT NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    event_format_name TEXT NOT NULL REFERENCES event_formats(name),
    PRIMARY KEY (vendor_id, event_format_name)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS vendor_languages (
    vendor_id TEXT NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    language_name TEXT NOT NULL REFERENCES languages(name),
    PRIMARY KEY (vendor_id, language_name)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS vendor_busy_dates (
    vendor_id TEXT NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    busy_date TEXT NOT NULL CHECK (length(busy_date) = 10),
    PRIMARY KEY (vendor_id, busy_date)
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS idx_vendors_city_price ON vendors(city, price_from_kzt, id);
CREATE INDEX IF NOT EXISTS idx_vendor_categories_category ON vendor_categories(category_name, vendor_id);
CREATE INDEX IF NOT EXISTS idx_vendor_formats_format ON vendor_event_formats(event_format_name, vendor_id);
CREATE INDEX IF NOT EXISTS idx_vendor_languages_language ON vendor_languages(language_name, vendor_id);
CREATE INDEX IF NOT EXISTS idx_busy_dates_date ON vendor_busy_dates(busy_date, vendor_id);
