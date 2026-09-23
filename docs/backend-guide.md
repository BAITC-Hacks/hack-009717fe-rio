# Backend Walkthrough for Participant 2

Your responsibility is the correctness of matching and the API contract shared with the frontend. The code already implements the baseline; understand it, verify it and coordinate changes with the other participants.

## 1. Open the Correct Project in WebStorm

Use File > Open and select the repository root, the folder containing `app.py`, `web`, `data` and `tests`. Do not open the entire Windows user directory as the project.

Open the terminal with Alt+F12. Confirm the working directory is the repository root.

## 2. Start the Server

With Python available on PATH:

```powershell
python app.py --port 8001
```

If Python is installed through the Codex bundled runtime instead:

```powershell
& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" app.py --port 8001
```

This invokes Python directly and does not require running a PowerShell script. Port 8001 avoids a conflict if another instance is already using port 8000. Open http://127.0.0.1:8001 and keep the terminal running. Ctrl+C stops your server.

Python does not automatically reload this application. After a backend edit, stop and restart the server. Refresh the browser after frontend changes.

## 3. Understand the Functions

| Function | Responsibility |
|---|---|
| `load_profiles()` | Read CSV and parse lists, booleans, prices and nullable hours |
| `validate(q)` | Reject invalid input before searching |
| `reasons(p, q)` | List every constraint that a profile fails |
| `recommend(q, profiles=None)` | Select the pool, filter, rank and explain up to three candidates |
| `demos()` | Find useful queries from the actual source calendars |
| `Handler` | Expose HTTP endpoints and the website assets |

`q` is the request, `p` is one profile, `pool` is the city/category selection, and `eligible` contains profiles with no rejection reasons.

## 4. Follow One Request

1. `/api/recommend` receives JSON from the browser.
2. `validate()` checks required fields, numeric limits and calendar coverage.
3. `recommend()` selects the exact city and category.
4. `reasons()` checks date, budget, format, language and hours.
5. Profiles with no failed constraints are sorted by text score, then price, then ID.
6. The first three receive factual explanations and source quotations.
7. The response includes a business status and an exclusion audit.

The catalog and UI use Russian values. Do not translate category names, language values or API messages when editing developer-facing documentation: those strings are part of the existing website contract.

## 5. Important Edge Cases

- Unavailable vendors must never appear.
- A price equal to the budget is accepted.
- A requested duration equal to the maximum is accepted.
- Null maximum hours means no hourly attendance limit, not zero hours.
- Omitted optional language and duration fields do not restrict results.
- Unsupported calendar dates must be rejected instead of assumed available.
- Changing dates can change results, but not every pair of dates must yield different results.
- The same request and dataset must preserve card order.

## 6. Coordinate with the Team

**Participant 1:** preserve endpoint names and JSON field names. The website relies on `status`, `cards`, `message`, `rejected`, `exclusion_counts` and metadata options. Agree on contract changes before editing either side.

**Participant 3:** the runtime reads `data/contractors.csv` plus the optional `data/synthetic_profiles.csv`. New records must use the same schema, unique IDs and `synthetic=true`. Run `python3 tools/audit_data.py --include-synthetic --markdown` before changing demos or presenting the expanded catalog.

## 7. Run Verification

```powershell
python -m unittest discover -s tests -v
```

Or use the full Python executable path shown above with the same arguments. Then verify the numbered website scenarios: autumn event, another date, rare category, insufficient budget and absent category.

Tests are local algorithm checks, not load tests against the hackathon network.

## 8. Explain Your Work

“We select profiles by city and category, then exclude anyone failing availability, budget, format, language or duration. The remaining profiles are ranked by weighted text overlap, followed by price and ID. That makes the order deterministic. Explanations use profile facts and quotations; rejected candidates retain specific reasons. This is a lexical baseline, not neural semantic understanding.”

Before a future commit or push, obtain the project owner's approval unless that specific operation has already been authorized. Keep unrelated files and other participants' staged work out of your commit.
