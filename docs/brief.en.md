# Hackathon Challenge: Smart Vendor Matching (#79-lite)

English translation of the source challenge saved in `brief.md`. The original organizer document remains authoritative.

## Scenario

You work on an event vendor aggregator in Kazakhstan. The customer has already selected an event type and received a catalog for their city. Help the customer choose from that list, rather than make the list longer.

## Task

The service accepts order requirements and returns up to three vendor cards. Every card explains why the vendor was selected. The value lies in the explanation, not merely the sorting.

## Data

The anonymized dataset contains 66 profiles and is available as JSONL, CSV and an HTML preview.

| Field | Meaning |
|---|---|
| `id`, `anon_name` | Identifier and fictional name |
| `categories` | List of vendor categories |
| `city` | Almaty, Astana or Abroad |
| `price_from_kzt` | Starting price in tenge per event |
| `event_formats` | Wedding, toi, corporate event, conference, anniversary or birthday |
| `languages` | Russian, Kazakh or English |
| `max_hours` | Maximum on-site hours; null means the service is not tied to attendance |
| `busy_dates` | Unavailable dates from September 23 to December 31, 2026, a 100-day window |
| `description` | Free text in Russian |
| `synthetic`, `city_imputed`, `price_imputed` | Provenance flags: 13 profiles are fully synthetic, and some cities/prices were assigned during preparation |

The data is already anonymized and needs no further anonymization. Venues have calendars just like individuals.

September–November calendars are 30–50% occupied; December calendars are 70–80% occupied. Very few vendors in dense categories remain available on December weekends. This reflects seasonality rather than a dataset bug.

Teams may add synthetic profiles using the same schema and `synthetic: true`. The demonstration must distinguish original and added synthetic profiles.

## Requirements

1. Input: city, event date, event type, vendor category and budget in tenge. Duration and language are optional.
2. Output: up to three cards containing name, category, city, price and one or two explanatory sentences grounded in budget, format, language, duration or description. Generic praise without specific evidence is not acceptable.
3. A vendor unavailable on the selected date must never appear. Venue matching uses the same catalog and calendar logic.
4. If fewer than three vendors qualify, show the actual number and explain why.
5. Determinism: the same request must produce the same card ordering.
6. Clearly distinguish three outcomes: matches found; category absent from the city; candidates present but none passing the conditions.

## Out of Scope

- Booking, inquiries and vendor notifications: recommendations only.
- A polished UI is not the priority. Prefer explanation quality when a tradeoff is necessary.
- Fine-tuning on 66 records is not useful for this one-day challenge. Ready-made embeddings and LLM APIs are allowed.

## Definition of Done

Evaluation takes place in a live demonstration, not on a slide.

- Requests return within a reasonable time, with a target of under 10 seconds.
- Explanations are not interchangeable: cards should remain distinguishable with names hidden.
- Repeating the same request preserves the order.
- Demonstrate a pair of dates for the same other parameters that changes the results due to availability, with an explanation.
- Demonstrate at least three queries: a dense category on an autumn date; a rare category; and a query with no results.
- Dense examples include event hosts (15 profiles), photographers (12) and banquet halls (8).
- Rare examples include florists, decorators, gifts and souvenirs, ceremony hosts, photo/video booths, hotels and instrumentalists, with three profiles each across the dataset.
- Empty results are explained in words, rather than displayed as a blank screen or technical error.
- The team can explain its pipeline to the judges.

## Evaluation

Priority: explanation quality, then honest handling of rare/unavailable/empty categories, then speed, then interface.

| Criterion | Points |
|---|---:|
| Task fit and functionality | 25 |
| Technical implementation, architecture and accurate claims about AI/other technology | 25 |
| README and reproducibility | 25 |
| Practical value and applicability | 15 |
| Development potential and originality | 10 |
| Total | 100 |
