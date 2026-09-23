#!/usr/bin/env python3
"""Validate the contractor catalog and print a reproducible audit report."""

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

START = date(2026, 9, 23)
END = date(2026, 12, 31)
REQUIRED = {
    'id', 'anon_name', 'categories', 'city', 'city_imputed', 'synthetic',
    'price_from_kzt', 'price_imputed', 'event_formats', 'languages',
    'max_hours', 'busy_dates', 'description'
}
LIST_FIELDS = ('categories', 'event_formats', 'languages', 'busy_dates')
BOOL_FIELDS = ('synthetic', 'city_imputed', 'price_imputed')


def audit(path: Path) -> dict:
    errors = []
    rows = []
    try:
        with path.open(encoding='utf-8-sig', newline='') as source:
            reader = csv.DictReader(source)
            headers = set(reader.fieldnames or [])
            missing = sorted(REQUIRED - headers)
            if missing:
                errors.append(f'Missing columns: {", ".join(missing)}')
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        return {'file': str(path), 'profiles': 0, 'errors': [str(exc)], 'ok': False}

    ids = Counter(row.get('id', '') for row in rows)
    duplicates = sorted(identifier for identifier, count in ids.items() if identifier and count > 1)
    if duplicates:
        errors.append('Duplicate IDs: ' + ', '.join(duplicates))

    cities = Counter()
    categories = Counter()
    synthetic = 0
    busy_total = 0
    for row_number, row in enumerate(rows, start=2):
        label = f'row {row_number}'
        if not row.get('id') or not row.get('anon_name'):
            errors.append(f'{label}: id and anon_name are required')
        if not row.get('city'):
            errors.append(f'{label}: city is required')
        else:
            cities[row['city']] += 1
        if not row.get('description', '').strip():
            errors.append(f'{label}: description is required')
        for field in ('categories', 'event_formats', 'languages'):
            values = [value.strip() for value in row.get(field, '').split('|') if value.strip()]
            if not values:
                errors.append(f'{label}: {field} is empty')
            if field == 'categories':
                categories.update(values)
        for field in BOOL_FIELDS:
            if row.get(field, '').lower() not in {'true', 'false'}:
                errors.append(f'{label}: {field} must be true or false')
        if row.get('synthetic', '').lower() == 'true':
            synthetic += 1
        try:
            if int(row.get('price_from_kzt', '')) <= 0:
                errors.append(f'{label}: price_from_kzt must be positive')
        except ValueError:
            errors.append(f'{label}: price_from_kzt must be an integer')
        max_hours = row.get('max_hours', '').strip()
        if max_hours:
            try:
                if float(max_hours) <= 0:
                    errors.append(f'{label}: max_hours must be positive or empty')
            except ValueError:
                errors.append(f'{label}: max_hours must be numeric or empty')
        dates = [value.strip() for value in row.get('busy_dates', '').split('|') if value.strip()]
        busy_total += len(dates)
        for value in dates:
            try:
                parsed = date.fromisoformat(value)
                if not START <= parsed <= END:
                    errors.append(f'{label}: busy date outside supported window: {value}')
            except ValueError:
                errors.append(f'{label}: invalid busy date: {value}')

    report = {
        'file': str(path),
        'ok': not errors,
        'profiles': len(rows),
        'synthetic_profiles': synthetic,
        'cities': dict(sorted(cities.items())),
        'categories': dict(sorted(categories.items())),
        'busy_date_entries': busy_total,
        'calendar': {'start': START.isoformat(), 'end': END.isoformat(), 'days': (END - START).days + 1},
        'errors': errors,
    }
    return report


def markdown(report: dict) -> str:
    status = 'PASS' if report['ok'] else 'FAIL'
    lines = [
        '# Contractor data audit', '',
        f'- Status: **{status}**',
        f'- Profiles: **{report["profiles"]}**',
        f'- Synthetic profiles: **{report["synthetic_profiles"]}**',
        f'- Busy-date entries: **{report["busy_date_entries"]}**',
        f'- Calendar: `{report["calendar"]["start"]}`–`{report["calendar"]["end"]}`', '',
        '## Cities', '', '| City | Profiles |', '|---|---:|',
    ]
    lines.extend(f'| {city} | {count} |' for city, count in report['cities'].items())
    lines.extend(['', '## Categories', '', '| Category | Profiles |', '|---|---:|'])
    lines.extend(f'| {category} | {count} |' for category, count in report['categories'].items())
    lines.extend(['', '## Errors', ''])
    lines.extend(f'- {error}' for error in report['errors'])
    if not report['errors']:
        lines.append('- None')
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_path', nargs='?', default='data/contractors.csv')
    parser.add_argument('--markdown', action='store_true', help='print a Markdown report')
    args = parser.parse_args()
    result = audit(Path(args.csv_path))
    output = markdown(result) if args.markdown else json.dumps(result, ensure_ascii=False, indent=2)
    print(output)
    sys.exit(0 if result['ok'] else 1)
