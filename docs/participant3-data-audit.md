# Participant 3 — data audit and demo checklist

This document records the data checks and presentation evidence owned by the third participant.

## Source snapshot

- Source file: `data/contractors.csv`
- Profiles: 66
- Synthetic profiles already present in the supplied catalog: 13
- Cities: Алматы — 50, Астана — 15, Зарубежье — 1
- Calendar window: 2026-09-23 through 2026-12-31 (100 days)
- Categories: 17

The source file remains unchanged. Existing `synthetic`, `city_imputed` and `price_imputed` flags must not be removed or silently rewritten.

## What to verify after a data change

Run the complete suite from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

Run the focused catalog audit before the demo:

```bash
python3 tools/audit_data.py --markdown
```

Exit code `0` means the catalog passed. A non-zero exit code identifies a data error that must be fixed or explicitly discussed before submission.

The following checks are mandatory before a demo:

1. Every profile has a unique `id`.
2. Every price is positive and numeric.
3. Every `busy_dates` value is a valid date inside the 100-day window.
4. Every profile has a city, category, event format and description.
5. A profile marked `synthetic=true` is visibly labelled in the website.
6. The same request returns the same card order twice.
7. A busy profile never appears in `cards`.
8. A rare category reports fewer than three when that is the actual result.
9. A missing city/category combination returns `no_category`.
10. A category with candidates but impossible constraints returns `no_match` and reasons.

## Demo sequence

Show these cases in order:

1. Dense category: Алматы, ведущий, корпоратив, autumn date, normal budget.
2. Same request on another date: explain which previously shown profiles became busy.
3. Rare category: флорист or инструменталист; show why fewer than three are returned.
4. Impossible budget: show `no_match` and the exclusion audit.
5. Missing city/category pair: show `no_category`.

Do not turn the demo buttons into canned answers. They must call the same recommendation endpoint as the form.

## Synthetic profiles

The challenge permits additional profiles when they use the same schema and are marked `synthetic: true`. If the team adds profiles, keep them in a separately reviewed data file or merge them explicitly in `load_profiles()`. Do not replace the supplied catalog, create duplicate IDs or tune availability only for the demo date. Record the number and provenance of added profiles in the README and in the presentation.

## Speaking notes

> Мы проверяем не только успешные рекомендации. Для каждой заявки сохраняем причины исключения, отдельно показываем отсутствие категории и ситуацию, когда кандидаты есть, но условия не проходят. Исходный каталог сохранён; синтетические записи помечаются явно и проходят тот же фильтр.

The third participant owns this evidence, the data provenance explanation and the final reproducibility check. The backend logic remains owned by the backend participant, and UI changes remain coordinated with the frontend participant.
