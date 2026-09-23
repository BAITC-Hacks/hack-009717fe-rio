# Rio — Smart Event Vendor Matching

A working solution for **HackAlem AI challenge #79-lite**. Rio helps event customers in Kazakhstan choose up to three vendors from an existing catalog, explaining recommendations through request constraints and quotations from profiles. Individual vendors, groups and venues share the same matching pipeline.

**Language policy:** developer documentation, comments and identifiers are English. The website, user-facing API messages, demo labels and original catalog remain Russian, as requested. The [Russian README](docs/README.ru.md) is retained for the organizers' submission requirement. Original organizer documents are preserved in their source language.

## Implemented Features

- Required city, date, event format, category and budget; optional language, duration and preferences.
- Strict availability, budget, format, language and duration checks.
- Up to three cards containing prices, specific reasons, quotations and complete descriptions.
- Deterministic lexical ranking, followed by price and ID.
- Three distinct outcomes: matches found, category absent, or candidates failing constraints.
- Explanations for short lists, per-profile rejection reasons and date comparisons.
- Labels for synthetic profiles and imputed prices and cities.
- Six interactive demo scenarios and a responsive Russian-language interface.

## Installation and Startup

Requires **Python 3.10+**. No third-party Python packages, database setup or API keys are needed.

```sh
git clone https://github.com/BAITC-Hacks/hack-009717fe-rio.git
cd hack-009717fe-rio
python app.py
```

Open **http://127.0.0.1:8000**. Stop the server with Ctrl+C. To use another port:

```sh
python app.py --port 8001
```

On Windows, `./start.ps1` finds either Python on PATH or the Python runtime bundled with an installed Codex application. If your Python command is named `python3`, use it instead of `python`.

In WebStorm, open the repository folder and run the startup command from its terminal. If PowerShell refuses to execute the startup script, run the installed Python executable directly; changing system execution policy is not necessary. See the [backend walkthrough](docs/backend-guide.md).

Run the automated checks:

```sh
python -m unittest discover -s tests -v
```

There is no public deployment. A localhost URL is accessible on the machine running the server, not a publicly hosted service.

## User Journey

Enter event requirements and select the matching button. The service checks mandatory constraints and shows up to three cards. Quotations highlight differences, while expandable sections expose the full source description and reasons for excluding alternatives. Change only the date and repeat the request to see which previously selected vendors are now unavailable.

## Three-Minute Demonstration

All queries are available as numbered buttons above the results. The English scenario names below describe the existing Russian buttons.

| Scenario | Parameters | Expected behavior |
|---|---|---|
| 01. Autumn corporate event | Almaty, event host, corporate event, October 4, 2026, KZT 1,500,000, 4 hours, Russian; preferences for refined humor and improvisation | Four eligible profiles, three displayed; ranking selects from a larger pool |
| 02. Another date | Same request on October 1, 2026 | Previous shortlist is unavailable; new results and a calendar explanation appear |
| 03. Rare category | Almaty, florist, wedding, October 4, 2026, KZT 500,000, 8 hours | Two cards with a short-list explanation; null hour limits do not exclude florists |
| 04. Insufficient budget | Scenario 01 with a KZT 10,000 budget | Candidates exist but none qualify; rejection reasons are available |
| 05. Category absent | Abroad, florist | Separate category-not-found state |
| 06. Banquet hall | Almaty, corporate event, November 14, 2026, KZT 7,000,000 | Venues follow the same calendar and filtering rules |

Repeat a request to verify stable ordering. Date comparison uses the previous successful request and appears only if all other parameters remain unchanged.

## Technology and Architecture

**Backend:** Python standard library (`http.server`, `csv`, `json`, `datetime`, `unittest`). **Frontend:** HTML, CSS and JavaScript without a build step. **Storage:** local CSV. Development was assisted by the Codex AI agent. The running application does not call an LLM, embedding model or external AI API.

```text
Browser -> POST /api/recommend -> validation
        -> city/category pool -> mandatory filters
        -> lexical ranking -> top three + facts + quotations + audit
```

| Component | Responsibility |
|---|---|
| `app.py` | API, CSV loading, filters, ranking, explanations and demo queries |
| `web/` | Form, cards, date comparison and responsive styling |
| `data/contractors.csv` | Original 66 profiles, unchanged |
| `tests/test_app.py` | Behavioral and acceptance checks |
| `docs/` | Specification, guides, pitch, submission text and source materials |
| `start.ps1` | Windows launcher |

### Matching Decisions

1. Validate required fields, positive budget and optional hours, known formats/languages and the calendar date. Dates outside September 23–December 31, 2026 are rejected: missing calendar coverage must not be interpreted as availability.
2. Select profiles by exact city and membership in the category array. Travel mentioned in a description does not automatically expand the geographic filter.
3. Exclude unavailable profiles, starting prices above budget, unsupported formats, missing requested languages and insufficient hours. A null `max_hours` means attendance is not hourly. Constraints are never silently relaxed.
4. Tokenize preferences, normalize the Russian letter yo to ye, and discard short and selected stop words. Use the first six letters for approximate word-form matching. The score is the sum of `ln(1 + N / (1 + df))` over unique matching prefixes, where N=66 and df is the number of source descriptions containing a prefix. Rarer matches have greater weight. Break ties by lower price, then string ID. Sum in sorted order to avoid nondeterminism.
5. Build a factual explanation and select a quotation with the most matching prefixes, truncated to approximately 240 characters. The full description remains available.
6. Return cards and an exclusion audit. Reason counts can overlap: a vendor may be both unavailable and over budget.

This is a **deterministic lexical baseline, not a semantic model**. It does not understand negation or synonyms, and prefix matching can be inaccurate. Preferences are a soft signal. Card details show the score, matched prefixes and whether direct matches are absent.

## API

`GET /api/meta` returns field options, statistics, calendar boundaries and demo requests.

`POST /api/recommend` accepts `Content-Type: application/json`:

```json
{
  "city": "Алматы",
  "date": "2026-10-04",
  "event_format": "корпоратив",
  "category": "Ведущий",
  "budget": 1500000,
  "hours": 4,
  "language": "русский",
  "preferences": "интеллигентный юмор импровизация"
}
```

Russian values are intentional: they are the actual catalog values consumed by the unchanged website. This example requests an event host in Almaty for a corporate event, with Russian as the working language and preferences for refined humor and improvisation. Use `/api/meta` for accepted values rather than translating enum values on the client.

Responses contain `status` (`matched`, `no_category`, `no_match`), `message`, `cards` (zero to three), `pool_count`, `eligible_count`, `rejected`, `exclusion_counts` and `elapsed_ms`. Invalid input returns HTTP 400 with `error`. An empty recommendation is a normal HTTP 200 outcome. Timing measures server-side matching, not network latency.

## Data, Sources and External Services

The runtime catalog contains 66 anonymized organizer profiles, including 13 synthetic profiles. No additional profiles are loaded. Calendars and provenance flags are preserved. The CSV and HTML preview represent the same catalog.

- [Challenge brief](https://docs.google.com/document/d/1rhR2HFY164BrnkIP39N3usY9fNY4JeAgkPxEzbqL00w/edit)
- [CSV dataset](https://drive.google.com/file/d/1uUCu-szctwaTaV0-Yfg3FKHY8M3lQ3vw/view)
- [HTML preview](https://drive.google.com/file/d/1IZhWdv53wujvRMHWTA47t9V1UqulmMPs/view)
- [Participant instructions](https://drive.google.com/file/d/105Rnhzg3Q5tKjfGZIddRqY13kmq_w4r_/view)

Matching is local. The browser may load Manrope from Google Fonts; a system font is available offline. No API keys are required. The organizers have not declared a separate license for their source materials. Follow their repository access and data-sharing requirements; inclusion here does not grant permission to redistribute the dataset.

## Verification

Ten automated tests cover data integrity; constraint checks across 100 dates and 17 categories; deterministic ordering under catalog reordering; all three outcomes and demos; calendar-driven date changes; budget boundaries; null hour limits; optional filters; invalid requests; grounded quotations; and execution time. Individual tests may cover several properties.

Run the test command above for current results. Prior local runs completed all ten tests in approximately 0.3 seconds. These measurements are not a production load guarantee.

## Limitations and Future Work

- Starting prices do not guarantee a final quote.
- Availability is an educational calendar snapshot, not live booking. No inquiries or notifications are sent.
- Profile claims are labeled as quotations, not independently verified quality assessments.
- The development HTTP server is bound to localhost. Public production use needs a production server, request limits and monitoring.
- There is no neural semantic search or fine-tuning. A possible next step is multilingual embeddings evaluated on labeled requests, with hard filters retained before model-based ranking.
- Any future LLM explanation layer needs factual grounding, caching by dataset version and query, and a deterministic fallback.

## Documentation and Submission

- [Complete English technical specification](docs/Rio_Technical_Specification_EN.md)
- [Backend walkthrough for participant 2](docs/backend-guide.md)
- [Defense script](docs/pitch.md)
- [Submission text](docs/submission.md)
- [English participant instructions](docs/participant-instructions.en.md)
- [English challenge brief](docs/brief.en.md)
- [Russian README for the organizers](docs/README.ru.md)

The organizers require the final code in the assigned team repository and a separate submission through the hackathon platform. Prepared text is not proof of submission. A public deployment link is required only if a deployment exists. API activation is not needed by this implementation and is not performed by the project.
