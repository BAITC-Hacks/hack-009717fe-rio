"""Deterministic demo portfolio content for the hackathon presentation."""

from __future__ import annotations

from .database import Database


DEMO_WORKS = (
    (
        "work_demo_goku_corporate",
        "HK-27222",
        "Осенний корпоратив на 180 гостей",
        "Динамичная программа для большой команды: открытие, интерактивы, награждение и финал без затянутых пауз.",
        "корпоратив",
        "Алматы",
        "2026-09-10",
        "2026-09-12T10:00:00+00:00",
    ),
    (
        "work_demo_goku_conference",
        "HK-27222",
        "Деловая конференция",
        "Двуязычная модерация сцены, работа со спикерами и точный тайминг программы.",
        "конференция",
        "Алматы",
        "2026-08-28",
        "2026-09-11T10:00:00+00:00",
    ),
    (
        "work_demo_anya_anniversary",
        "HK-29829",
        "Тёплый семейный юбилей",
        "Лёгкий сценарий, музыкальные интерактивы и много общения с гостями без длинных речей.",
        "юбилей",
        "Алматы",
        "2026-09-06",
        "2026-09-10T10:00:00+00:00",
    ),
    (
        "work_demo_kiki_wedding",
        "HK-35215",
        "Современный свадебный вечер",
        "Персональный сценарий, деликатный юмор и трёхъязычная работа с гостями.",
        "свадьба",
        "Алматы",
        "2026-09-14",
        "2026-09-15T10:00:00+00:00",
    ),
)


DEMO_RATINGS = (
    ("work_demo_goku_corporate", "demo_client_1", "Алия", 5, "Команда была вовлечена с первых минут."),
    ("work_demo_goku_corporate", "demo_client_2", "Руслан", 5, "Сильная подача и точный тайминг."),
    ("work_demo_goku_corporate", "demo_client_3", "Дана", 4, "Профессионально и легко."),
    ("work_demo_goku_conference", "demo_client_4", "Мадина", 5, "Отличная работа со спикерами."),
    ("work_demo_goku_conference", "demo_client_5", "Тимур", 4, "Программа прошла по таймингу."),
    ("work_demo_anya_anniversary", "demo_client_6", "Айгерим", 5, "Очень тёплая атмосфера."),
    ("work_demo_anya_anniversary", "demo_client_7", "Ерлан", 5, "Именно тот формат, который мы хотели."),
    ("work_demo_kiki_wedding", "demo_client_8", "Сауле", 5, "Гостям было комфортно на трёх языках."),
    ("work_demo_kiki_wedding", "demo_client_9", "Арман", 4, "Стильно и без шаблонных конкурсов."),
)


def seed_demo_portfolio(database: Database) -> None:
    """Add stable demo works once while preserving user-created portfolio data."""
    with database.connect() as connection:
        for work in DEMO_WORKS:
            connection.execute(
                """INSERT OR IGNORE INTO portfolio_works(
                    id, vendor_id, title, description, event_format, city,
                    occurred_on, published_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (*work, work[-1]),
            )
        for work_id, client_id, client_name, score, comment in DEMO_RATINGS:
            timestamp = "2026-09-16T10:00:00+00:00"
            connection.execute(
                """INSERT OR IGNORE INTO work_ratings(
                    work_id, client_id, client_name, score, comment, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (work_id, client_id, client_name, score, comment, timestamp, timestamp),
            )
