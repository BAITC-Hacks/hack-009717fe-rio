# Technical Specification: Rio — Smart Event Vendor Matching

**Project:** Rio  
**Team:** Rio  
**Hackathon:** HackAlem AI  
**Challenge:** Smart Vendor Matching, #79-lite  
**Repository:** [BAITC-Hacks/hack-009717fe-rio](https://github.com/BAITC-Hacks/hack-009717fe-rio)

This document describes the current version of the project. Potential future improvements are listed separately and are outside the mandatory scope. This is the English translation of the complete project specification; the current application interface remains in Russian.

## 1. Project Purpose

Rio is a web service that helps event customers in Kazakhstan select vendors from an existing catalog.

The user enters event requirements and receives **up to three suitable profiles**. For each result, the service explains which requirements are satisfied and highlights relevant characteristics from the vendor's description.

The primary value is to reduce selection time and make recommendations understandable and verifiable.

## 2. User Problem

A conventional catalog offers many options but leaves the user to manually check:

- whether the vendor operates in the required city;
- whether the vendor is available on the event date;
- whether the price fits the budget;
- whether the vendor accepts the required event format;
- whether the vendor supports the required language;
- whether the vendor can work for the necessary number of hours;
- whether the vendor's approach matches the customer's preferences.

Rio performs these checks and produces a shortlist.

The service helps the user choose **within the selected city and category**. It does not expand the results with vendors from other cities or vendors that fail the requirements.

## 3. Target Audience

- Private customers organizing weddings, toi celebrations, anniversaries, and birthdays.
- Organizers of corporate events and conferences.
- Event managers who need to compare suitable vendors quickly.
- Hackathon judges evaluating the solution against the provided dataset.

User registration and role-based access are not required in the current version.

## 4. Project Scope

The mandatory scope includes:

- an event requirements form;
- processing of the original catalog;
- vendor filtering;
- deterministic ranking;
- up to three result cards;
- recommendation explanations;
- explanations for empty results and short lists;
- comparison of results when the date changes;
- demonstration scenarios;
- documentation and automated checks.

The current version **does not include**:

- booking;
- sending inquiries or messages to vendors;
- payments;
- user accounts;
- user reviews and ratings;
- live calendar synchronization;
- an administration panel;
- model fine-tuning;
- mandatory use of an external AI API.

## 5. Source Data

The service uses the CSV dataset supplied by the organizers, containing **66 profiles**.

The dataset includes 13 fully synthetic profiles. The team does not add new profiles.

The HTML preview is an additional reference for understanding the catalog structure.

### 5.1. Profile Schema

| Field | Description |
|---|---|
| `id` | Unique identifier |
| `anon_name` | Anonymized name |
| `categories` | One or more vendor categories |
| `city` | City or geographic group |
| `price_from_kzt` | Starting price per event in Kazakhstani tenge |
| `event_formats` | Supported event formats |
| `languages` | Working languages |
| `max_hours` | Maximum number of hours on site |
| `busy_dates` | Unavailable dates |
| `description` | Free-text description |
| `synthetic` | Whether the profile is synthetic |
| `city_imputed` | Whether the city was assigned during dataset preparation |
| `price_imputed` | Whether the price was assigned during dataset preparation |

### 5.2. Interpretation Rules

- The calendar covers **September 23 through December 31, 2026, inclusive**.
- A date listed in `busy_dates` means the vendor is unavailable.
- `max_hours = null` means the service is not tied to hourly on-site attendance.
- A starting price is not a confirmed final quote.
- References to other cities in the description do not override the structured `city` field.
- Venues follow the same calendar rules as individual vendors.
- Original data provenance flags are preserved.

## 6. User Journey

1. The user opens the application.
2. The user specifies the city and event date.
3. The user selects the event format and vendor category.
4. The user enters a budget for one vendor.
5. If needed, the user specifies the language, duration, and preferences.
6. The user clicks the vendor matching button.
7. The user receives one of three outcomes:
   - suitable vendors were found;
   - the selected category does not exist in the selected city's catalog;
   - the category exists, but no vendor satisfies all requirements.
8. The user reviews explanations, profile descriptions, and reasons for excluding alternatives.
9. If needed, the user changes the requirements and runs the search again.

## 7. Input Parameters

| Parameter | Required | Rules |
|---|---|---|
| City | Yes | Selected from the catalog's geographic options |
| Date | Yes | Valid date within the supported calendar |
| Event format | Yes | Selected from the dataset's formats |
| Category | Yes | Selected vendor category |
| Budget | Yes | Positive number in tenge |
| Duration | No | Positive number of hours |
| Language | No | One language, or no language restriction |
| Preferences | No | Text of up to 1,000 characters |

Available geographic options: Almaty, Astana, and Abroad.

Event formats: wedding, toi celebration, corporate event, conference, anniversary, and birthday.

Languages: Russian, Kazakh, and English.

Categories are derived from the source data and include hosts, photographers, videographers, florists, decorators, musical groups, and venues.

**Preferences are a soft ranking criterion.** They do not override mandatory constraints.

## 8. Matching Algorithm

### 8.1. Request Validation

Before searching, the system checks:

- that required fields are present;
- that the date is valid;
- that the date falls within the supported calendar;
- that the budget is a positive finite number;
- that any supplied duration is valid;
- that the event format and language are recognized;
- that preference text has the correct type and length.

If validation fails, the user receives an understandable explanation of the error.

Dates outside the calendar must not be treated as available. Such requests must be rejected.

### 8.2. Initial Candidate Pool

A profile enters the candidate pool only if both conditions are satisfied:

```text
profile.city == request.city

request.category is included in profile.categories
```

If the pool is empty, the system returns the category-not-found outcome.

### 8.3. Mandatory Filtering

A vendor is excluded if at least one of the following conditions applies:

| Reason | Exclusion condition |
|---|---|
| Availability | The event date is included in `busy_dates` |
| Budget | `price_from_kzt` exceeds the budget |
| Format | The requested format is absent from `event_formats` |
| Language | A language is requested but is absent from `languages` |
| Duration | The requested hours exceed `max_hours`, when the limit is not `null` |

Boundary rules:

- A price equal to the budget is accepted.
- A duration equal to the limit is accepted.
- An unspecified language does not restrict results.
- An unspecified duration does not restrict results.
- `max_hours = null` is not a reason for exclusion.
- One profile may have multiple exclusion reasons.

The system must not automatically increase the budget or change the city, date, or other constraints.

### 8.4. Ranking Eligible Profiles

The current version uses explainable lexical ranking.

Preference text and descriptions are processed as follows:

1. Convert text to lowercase.
2. Replace the Russian letter `ё` with `е`.
3. Extract Russian and Latin words.
4. Remove short words and selected stop words.
5. Use the first six letters for approximate matching of word forms.
6. Find matches between the preferences and the description.

The text score is:

```text
score = sum of ln(1 + N / (1 + df))
```

Where:

- `N` is the number of profiles in the source catalog;
- `df` is the number of descriptions containing the matched word prefix;
- the sum is calculated over unique matched prefixes.

Rarer matches receive higher weights.

Final ordering:

1. Text score, descending.
2. Starting price, ascending.
3. Profile identifier, ascending.

If preferences are absent or there are no direct matches, price and ID determine the order.

### 8.5. Determinism

With unchanged data, the same request must return the same cards in the same order.

The result must not depend on:

- random numbers;
- the order of profiles in the CSV;
- the order of fields in the JSON request;
- the number of repeated runs.

## 9. Result Requirements

### 9.1. Vendor Card

Each card contains:

- name;
- selected category;
- city;
- starting price in tenge per event;
- position in the shortlist;
- explanation of how the requirements are satisfied;
- a quotation from the description;
- availability on the selected date;
- languages;
- maximum hours, or a statement that attendance is not hourly;
- profile provenance;
- flags for imputed price and city.

An expandable section contains:

- the full description;
- supported formats;
- ID;
- text score;
- matched word prefixes;
- an explanation when there are no text matches.

### 9.2. Explanations

Explanations must be grounded in profile facts and request parameters.

Example, translated into English:

> Available on October 4; accepts corporate events; starting price is KZT 700,000 within a KZT 1,500,000 budget; works in Russian; the six-hour limit covers the requested four hours.

A quotation highlighting the vendor's characteristics is displayed alongside the explanation.

The following are not permitted:

- invented advantages;
- unsupported ratings;
- claims of a guaranteed final price;
- generic statements unrelated to the request;
- presenting profile text as independently verified information.

The quotation must be labeled as information from the description. In the current implementation, it is limited to approximately 240 characters.

### 9.3. Number of Cards

- The maximum is three.
- If only one or two profiles qualify, all qualifying profiles are displayed.
- Empty positions must not be filled with unsuitable or invented profiles.
- If more than three profiles qualify, the first three under the defined ranking are displayed.

## 10. Result States

| State | Code | Behavior |
|---|---|---|
| Suitable vendors found | `matched` | Display one to three cards |
| Category absent from the city | `no_category` | Explain that the city/category combination is absent |
| No candidate satisfies the requirements | `no_match` | Show why candidates were excluded |

### 10.1. Short Lists

When fewer than three cards are displayed, the user must see:

- how many profiles existed in the city and category;
- how many were excluded;
- why the remaining profiles were excluded.

### 10.2. Empty Results

An empty result is not a technical error.

The user receives a textual explanation and information about which parameters can be reconsidered.

If the city has no profiles in the selected category, the interface must explain that changing the budget or date will not add that category to the catalog.

### 10.3. Exclusion Audit

The system shows:

- the number of excluded profiles;
- the number of occurrences of each exclusion reason;
- reasons for individual vendors.

The interface must explain that the sum of reason counts may exceed the number of excluded profiles because reasons can overlap.

## 11. Date Comparison

If the user changes only the date, the system compares the result with the previous successful request.

It must show:

- the previous and new dates;
- which vendors from the previous shortlist are unavailable on the new date;
- which new vendors appeared.

The comparison must use profile calendars.

If other parameters change at the same time, the system must not attribute all result changes solely to availability.

## 12. Interface Requirements

The application's primary language is Russian.

Main sections:

1. Name and a brief explanation of the service.
2. Requirements form.
3. Matching button.
4. Ready-made demonstration scenarios.
5. Result heading and status.
6. Cards.
7. Exclusion reasons.
8. Explanation of how the service works.
9. Dataset information and limitations.

Requirements:

- readable text and clear visual hierarchy;
- labeled fields;
- visible validation errors;
- keyboard operation;
- responsive layout;
- distinguishable original profiles, synthetic profiles, and imputed data;
- the primary button is disabled while a request is running;
- an understandable message appears for network errors.

Rio's visual style uses a light background, dark green typography, green accents, and restrained card styling.

## 13. Architecture and Technologies

| Layer | Implementation |
|---|---|
| Backend | Python 3.10+, standard library |
| HTTP server | `http.server` |
| Data storage | Local CSV |
| Frontend | HTML, CSS, JavaScript |
| Data exchange | HTTP and JSON |
| Testing | `unittest` |
| Development | Assisted by the Codex AI agent |

Data flow:

```text
Browser form
    ↓
POST /api/recommend
    ↓
Validation
    ↓
Candidate pool by city and category
    ↓
Mandatory filters
    ↓
Ranking
    ↓
Up to three cards + explanations + audit
    ↓
Result display
```

**The current service does not use an LLM or embeddings.** Using Codex during development and the recommendation algorithm executed inside the application are separate aspects of the project.

## 14. API

### `GET /api/meta`

Returns:

- available cities, categories, formats, and languages;
- profile count;
- synthetic profile count;
- calendar boundaries;
- demonstration requests.

### `POST /api/recommend`

Example request:

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

The example intentionally retains Russian catalog values because these are the actual values accepted by the current API. In English, it requests a host in Almaty for a corporate event on October 4, with a budget of KZT 1,500,000, a four-hour duration, Russian as the working language, and preferences for refined humor and improvisation.

Main response fields:

| Field | Purpose |
|---|---|
| `status` | One of the three outcomes |
| `message` | Explanation of the result |
| `cards` | Array of zero to three cards |
| `pool_count` | Size of the city/category pool |
| `eligible_count` | Number of profiles passing the constraints |
| `rejected` | Excluded profiles and their reasons |
| `exclusion_counts` | Counts of exclusion reasons |
| `elapsed_ms` | Server-side matching time |

Response codes:

- `200`: processed request, including an empty result;
- `400`: invalid input;
- `404`: unknown route.

## 15. Non-Functional Requirements

### Performance

The challenge's target is a response within 10 seconds.

For the local catalog of 66 profiles, processing should complete without a noticeable wait. Server-side processing time must not be presented as total network latency.

### Reproducibility

- Start the application with one command.
- No mandatory API keys.
- No need to install third-party Python libraries.
- The source dataset is included in the repository.
- Verification scenarios are documented in the README.

### Security

- API keys and secrets must not be published.
- Profile text is rendered safely in the browser.
- Input is validated on the server.
- Request size is limited.
- The local server listens on `127.0.0.1` by default.
- Matching does not send event details to third-party AI services.

Google Fonts may be used for styling. A system font is used if it is unavailable.

## 16. Testing and Acceptance

Mandatory checks:

| Check | Acceptance criterion |
|---|---|
| Data integrity | 66 unique profiles are loaded; 13 synthetic flags are preserved |
| Availability | A profile unavailable on the selected date never appears |
| Budget | A price above the budget is excluded; an equal price is accepted |
| Format | An unsupported format is excluded |
| Language | The requested language is respected |
| Duration | Exceeding the hour limit causes exclusion |
| `null` hours | Not interpreted as zero hours |
| Result limit | No more than three cards |
| Determinism | Repeating the request preserves the order |
| Date changes | Results change according to calendars |
| Rare category | The actual number of matches is shown with an explanation |
| Category absent | Separate `no_category` state |
| No matches | Separate `no_match` state |
| Quotations | Supported by the original description |
| Invalid input | An understandable error is returned |
| Performance | The response meets the 10-second target |

The current suite contains 10 automated tests, some of which verify multiple properties. It includes constraint checks across 100 calendar days and 17 categories.

## 17. Demonstration Scenarios

1. **Dense category:** hosts in Almaty for a corporate event on October 4, 2026; budget KZT 1,500,000; four hours; Russian.
2. **Date change:** the same request for October 1; show which previous vendors are now unavailable.
3. **Rare category:** florists in Almaty for a wedding on October 4; budget KZT 500,000.
4. **Insufficient budget:** hosts with a budget of KZT 10,000.
5. **Absent category:** florists in the Abroad geographic group.
6. **Venue:** a banquet hall in Almaty for a corporate event on November 14; budget KZT 7,000,000.

The defense must demonstrate the running service, not only presentation slides.

## 18. Deliverables

- Backend and frontend source code.
- Original CSV dataset.
- Automated tests.
- README in Russian.
- Installation and startup commands.
- Verification examples.
- Architecture and algorithm description.
- List of limitations.
- A short defense script.
- Project name and description for the submission form.

Main files:

```text
app.py
web/index.html
web/style.css
web/app.js
data/contractors.csv
tests/test_app.py
README.md
start.ps1
docs/pitch.md
docs/submission.md
```

## 19. Hackathon Submission Requirements

According to the organizers' instructions:

1. The team solves one selected challenge.
2. An AI agent is used during development.
3. Final code is published to the assigned team repository.
4. The README describes only capabilities that actually exist.
5. The team selects the challenge on the platform and clicks “Submit Solution.”
6. The project name and description are entered.
7. Submission acceptance is verified.

A public deployment is not mandatory. A deployment link is supplied only if a deployed version exists.

## 20. Current Limitations

- Lexical search does not understand meaning in the way a language model does.
- Synonyms and negation are not fully handled.
- Prefix matching can produce inaccurate text matches.
- A starting price does not guarantee the final cost.
- The calendar is not updated in real time.
- Profiles are anonymized and partly synthetic.
- The development HTTP server requires replacement or additional infrastructure for public production use.

## 21. Potential Future Improvements

The following capabilities **are not part of the completed current version**:

- multilingual semantic search using embeddings;
- recommendation quality evaluation on labeled queries;
- LLM-generated explanations strictly grounded in facts;
- live calendars and current prices;
- database storage;
- monitoring, request rate limiting, and production deployment;
- feedback collection on recommendation usefulness.

Any future version must preserve the core rules: unavailable and unsuitable vendors are excluded, selection reasons remain verifiable, and identical requests with identical data remain reproducible.
