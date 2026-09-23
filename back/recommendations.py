"""Deterministic recommendation business rules."""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import date


START, END = "2026-09-23", "2026-12-31"
STOP_WORDS = set("это для про как что или при без под над все мне меня вами вас ваш наши они его она где чем так более очень".split())


def text_tokens(text: str) -> set[str]:
    return {
        word[:6]
        for word in re.findall(r"[а-яёa-z]+", text.lower().replace("ё", "е"))
        if len(word) > 2 and word not in STOP_WORDS
    }


def rejection_reasons(profile: dict, query: dict) -> list[str]:
    """Return every hard constraint that a vendor fails."""
    return [
        key
        for key, failed in (
            ("busy", query["date"] in profile["busy_dates"]),
            ("budget", profile["price_from_kzt"] > query["budget"]),
            ("format", query["event_format"] not in profile["event_formats"]),
            ("language", bool(query.get("language")) and query["language"] not in profile["languages"]),
            (
                "hours",
                bool(query.get("hours"))
                and profile["max_hours"] is not None
                and profile["max_hours"] < query["hours"],
            ),
        )
        if failed
    ]


def money(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ") + " ₸"


class RecommendationService:
    def __init__(self, profiles: list[dict], options: dict[str, list[str]] | None = None):
        self.profiles = profiles
        self.options = options or {
            key: sorted({value for profile in profiles for value in (profile[key] if isinstance(profile[key], list) else [profile[key]])})
            for key in ("city", "categories", "event_formats", "languages")
        }
        self.document_frequency = Counter(
            token for profile in profiles for token in text_tokens(profile["description"])
        )

    def validate(self, query: dict) -> None:
        if not isinstance(query, dict):
            raise ValueError("Запрос должен быть JSON-объектом.")
        for field in ("city", "category", "event_format", "date"):
            if not isinstance(query.get(field), str) or not query[field].strip():
                raise ValueError("Заполните город, дату, формат и категорию.")
        try:
            parsed = date.fromisoformat(query["date"])
            if parsed.isoformat() != query["date"] or not START <= query["date"] <= END:
                raise ValueError
        except ValueError:
            raise ValueError("Календарь доступен только с 23.09.2026 по 31.12.2026.") from None
        for field in ("budget", "hours"):
            value = query.get(field)
            if field == "hours" and value in (None, ""):
                continue
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
                raise ValueError("Бюджет и указанная длительность должны быть положительными числами.")
        if query["event_format"] not in self.options["event_formats"]:
            raise ValueError("Неизвестный формат мероприятия.")
        if query.get("language") and query["language"] not in self.options["languages"]:
            raise ValueError("Неизвестный язык.")
        if not isinstance(query.get("preferences", ""), str) or len(query.get("preferences", "")) > 1000:
            raise ValueError("Пожелания: максимум 1000 символов.")

    def recommend(self, query: dict) -> dict:
        self.validate(query)
        pool = [
            profile for profile in self.profiles
            if profile["city"] == query["city"] and query["category"] in profile["categories"]
        ]
        rejected = [
            {"id": profile["id"], "name": profile["anon_name"], "reasons": rejection_reasons(profile, query)}
            for profile in pool
            if rejection_reasons(profile, query)
        ]
        eligible = [profile for profile in pool if not rejection_reasons(profile, query)]
        query_tokens = text_tokens(query.get("preferences", ""))

        def score(profile: dict) -> float:
            matched = query_tokens & text_tokens(profile["description"])
            return sum(
                math.log(1 + len(self.profiles) / (1 + self.document_frequency[token]))
                for token in sorted(matched)
            )

        eligible.sort(key=lambda profile: (-score(profile), profile["price_from_kzt"], profile["id"]))
        cards = []
        for profile in eligible[:3]:
            sentences = [
                sentence.strip()
                for sentence in re.split(r"(?<=[.!?])\s+", profile["description"])
                if sentence.strip()
            ]
            quote = max(
                sentences,
                key=lambda sentence: sum(token in text_tokens(sentence) for token in query_tokens),
                default="Описание не заполнено",
            )
            if len(quote) > 240:
                quote = quote[:240].rsplit(" ", 1)[0] + "…"
            details = [
                f"свободен {query['date']}",
                f"берёт формат «{query['event_format']}»",
                f"цена от {money(profile['price_from_kzt'])} при бюджете {money(query['budget'])}",
            ]
            if query.get("language"):
                details.append(f"язык — {query['language']}")
            if query.get("hours"):
                details.append(
                    "присутствие по часам не требуется"
                    if profile["max_hours"] is None
                    else f"лимит {profile['max_hours']:g} ч покрывает ваши {query['hours']:g} ч"
                )
            explanation = "; ".join(details)
            cards.append({
                **profile,
                "explanation": explanation[0].upper() + explanation[1:] + ".",
                "evidence": quote,
                "text_score": round(score(profile), 4),
                "matched_terms": sorted(query_tokens & text_tokens(profile["description"])),
            })

        counts = dict(Counter(reason for item in rejected for reason in item["reasons"]))
        status = "matched" if cards else ("no_category" if not pool else "no_match")
        message = {
            "matched": f"Подобрали {len(cards)} из {len(eligible)} подходящих профилей.",
            "no_category": "В этом городе такой категории нет в каталоге.",
            "no_match": "Кандидаты есть, но ни один не проходит все условия.",
        }[status]
        if 0 < len(cards) < 3:
            message += f" Меньше трёх: в городе в этой категории всего {len(pool)}, исключено по условиям {len(rejected)}."
        return {
            "status": status,
            "message": message,
            "cards": cards,
            "pool_count": len(pool),
            "eligible_count": len(eligible),
            "rejected": rejected,
            "exclusion_counts": counts,
        }

    def demos(self) -> list[dict]:
        base = {
            "city": "Алматы", "category": "Ведущий", "event_format": "корпоратив",
            "budget": 1500000, "hours": 4, "language": "русский",
            "preferences": "интеллигентный юмор импровизация",
        }
        autumn = [date(2026, 10, day).isoformat() for day in range(1, 32)]
        first = next({**base, "date": day} for day in autumn if self.recommend({**base, "date": day})["eligible_count"] > 3)
        identifiers = {profile["id"] for profile in self.recommend(first)["cards"]}
        second = next(
            {**base, "date": day}
            for day in autumn
            if any(profile["id"] in identifiers and day in profile["busy_dates"] for profile in self.profiles)
            and self.recommend({**base, "date": day})["cards"]
        )
        rare = {
            "city": "Алматы", "category": "Флорист", "event_format": "свадьба",
            "budget": 500000, "hours": 8, "language": "", "preferences": "цветочное оформление",
        }
        rare["date"] = next(day for day in autumn if self.recommend({**rare, "date": day})["cards"])
        return [
            {"label": "01 · Осенний корпоратив", "query": first},
            {"label": "02 · Другая дата", "query": second},
            {"label": "03 · Редкая категория", "query": rare},
            {"label": "04 · Бюджет не проходит", "query": {**first, "budget": 10000}},
            {"label": "05 · Нет категории", "query": {**first, "city": "Зарубежье", "category": "Флорист"}},
            {"label": "06 · Банкетный зал", "query": {**first, "category": "Банкетный зал", "date": "2026-11-14", "budget": 7000000, "preferences": "панорамный вид горы"}},
        ]
