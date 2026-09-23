"""Rio: deterministic vendor recommendations using the Python standard library.

Developer documentation and identifiers are English. Catalog values and messages
remain Russian because they are displayed by the existing Russian-language UI.
"""
import argparse
import csv
import json
import math
import re
from collections import Counter
from datetime import date
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parent
START, END = '2026-09-23', '2026-12-31'


def load_profiles():
    """Load the organizer CSV and convert delimited fields into typed values."""
    # contractors.csv is the authoritative expanded runtime catalog.
    # Keep synthetic_profiles.csv as a separate audit artifact without appending it.
    paths = [ROOT / 'data/contractors.csv']
    profiles = []
    for path in paths:
        with path.open(encoding='utf-8-sig', newline='') as source:
            profiles.extend(csv.DictReader(source))
    for p in profiles:
        for key in ('categories', 'languages', 'event_formats', 'busy_dates'):
            p[key] = p[key].split('|') if p[key] else []
        for key in ('synthetic', 'city_imputed', 'price_imputed'):
            p[key] = p[key].lower() == 'true'
        p['price_from_kzt'] = int(p['price_from_kzt'])
        p['max_hours'] = float(p['max_hours']) if p['max_hours'] else None
    ids = [p['id'] for p in profiles]
    if len(ids) != len(set(ids)):
        raise ValueError('Catalog contains duplicate profile IDs.')
    return profiles


PROFILES = load_profiles()
OPTIONS = {key: sorted({v for p in PROFILES for v in (p[key] if isinstance(p[key], list) else [p[key]])})
           for key in ('city', 'categories', 'event_formats', 'languages')}
STOP = set('это для про как что или при без под над все мне меня вами вас ваш наши они его она где чем так более очень'.split())


def tokens(text):
    # Transparent prefix normalization, not an embedding or a language model.
    return {w[:6] for w in re.findall(r'[а-яёa-z]+', text.lower().replace('ё', 'е')) if len(w) > 2 and w not in STOP}


DF = Counter(t for p in PROFILES for t in tokens(p['description']))


def validate(q):
    """Reject invalid requests before filtering; errors are user-facing Russian."""
    if not isinstance(q, dict):
        raise ValueError('Запрос должен быть JSON-объектом.')
    for field in ('city', 'category', 'event_format', 'date'):
        if not isinstance(q.get(field), str) or not q[field].strip():
            raise ValueError('Заполните город, дату, формат и категорию.')
    try:
        parsed = date.fromisoformat(q['date'])
        if parsed.isoformat() != q['date'] or not START <= q['date'] <= END:
            raise ValueError()
    except ValueError:
        raise ValueError('Календарь доступен только с 23.09.2026 по 31.12.2026.') from None
    for field in ('budget', 'hours'):
        value = q.get(field)
        if field == 'hours' and value in (None, ''):
            continue
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
            raise ValueError('Бюджет и указанная длительность должны быть положительными числами.')
    if q['event_format'] not in OPTIONS['event_formats']:
        raise ValueError('Неизвестный формат мероприятия.')
    if q.get('language') and q['language'] not in OPTIONS['languages']:
        raise ValueError('Неизвестный язык.')
    if not isinstance(q.get('preferences', ''), str) or len(q.get('preferences', '')) > 1000:
        raise ValueError('Пожелания: максимум 1000 символов.')


def reasons(p, q):
    """Return every failed constraint; a null hour limit means not applicable."""
    return [key for key, failed in (
        ('busy', q['date'] in p['busy_dates']),
        ('budget', p['price_from_kzt'] > q['budget']),
        ('format', q['event_format'] not in p['event_formats']),
        ('language', bool(q.get('language')) and q['language'] not in p['languages']),
        ('hours', bool(q.get('hours')) and p['max_hours'] is not None and p['max_hours'] < q['hours'])
    ) if failed]


def money(value):
    return f'{value:,.0f}'.replace(',', ' ') + ' ₸'


def recommend(q, profiles=None):
    """Filter, rank and explain up to three candidates without relaxing constraints.

    The optional profile list supports isolated tests. Text ranking uses the
    original catalog's document frequencies, then price and ID break ties.
    """
    validate(q)
    profiles = PROFILES if profiles is None else profiles
    pool = [p for p in profiles if p['city'] == q['city'] and q['category'] in p['categories']]
    rejected = [{'id': p['id'], 'name': p['anon_name'], 'reasons': reasons(p, q)} for p in pool if reasons(p, q)]
    eligible = [p for p in pool if not reasons(p, q)]
    query_tokens = tokens(q.get('preferences', ''))

    def score(p):
        matched = query_tokens & tokens(p['description'])
        return sum(math.log(1 + len(PROFILES) / (1 + DF[t])) for t in sorted(matched))

    eligible.sort(key=lambda p: (-score(p), p['price_from_kzt'], p['id']))
    cards = []
    for p in eligible[:3]:
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', p['description']) if s.strip()]
        quote = max(sentences, key=lambda s: sum(t in tokens(s) for t in query_tokens), default='Описание не заполнено')
        quote = quote[:240].rsplit(' ', 1)[0] + '…' if len(quote) > 240 else quote
        details = [f'свободен {q["date"]}', f'берёт формат «{q["event_format"]}»',
                   f'цена от {money(p["price_from_kzt"])} при бюджете {money(q["budget"])}']
        if q.get('language'):
            details.append(f'язык — {q["language"]}')
        if q.get('hours'):
            details.append('присутствие по часам не требуется' if p['max_hours'] is None else f'лимит {p["max_hours"]:g} ч покрывает ваши {q["hours"]:g} ч')
        explanation = '; '.join(details)
        cards.append({**p, 'explanation': explanation[0].upper() + explanation[1:] + '.', 'evidence': quote,
                      'text_score': round(score(p), 4), 'matched_terms': sorted(query_tokens & tokens(p['description']))})
    counts = dict(Counter(r for p in rejected for r in p['reasons']))
    status = 'matched' if cards else ('no_category' if not pool else 'no_match')
    message = {'matched': f'Подобрали {len(cards)} из {len(eligible)} подходящих профилей.',
               'no_category': 'В этом городе такой категории нет в каталоге.',
               'no_match': 'Кандидаты есть, но ни один не проходит все условия.'}[status]
    if 0 < len(cards) < 3:
        message += f' Меньше трёх: в городе в этой категории всего {len(pool)}, исключено по условиям {len(rejected)}.'
    return {'status': status, 'message': message, 'cards': cards, 'pool_count': len(pool),
            'eligible_count': len(eligible), 'rejected': rejected, 'exclusion_counts': counts}


def demos():
    """Find reproducible examples in the real calendars, not canned responses."""
    base = dict(city='Алматы', category='Ведущий', event_format='корпоратив', budget=1500000, hours=4, language='русский', preferences='интеллигентный юмор импровизация')
    autumn = [date(2026, 10, d).isoformat() for d in range(1, 32)]
    first = next({**base, 'date': d} for d in autumn if recommend({**base, 'date': d})['eligible_count'] > 3)
    ids = {p['id'] for p in recommend(first)['cards']}
    second = next({**base, 'date': d} for d in autumn if any(p['id'] in ids and d in p['busy_dates'] for p in PROFILES)
                  and recommend({**base, 'date': d})['cards'])
    rare = dict(city='Алматы', category='Флорист', event_format='свадьба', budget=500000, hours=8, language='', preferences='цветочное оформление')
    rare['date'] = next(d for d in autumn if recommend({**rare, 'date': d})['cards'])
    return [{'label': '01 · Осенний корпоратив', 'query': first}, {'label': '02 · Другая дата', 'query': second},
            {'label': '03 · Редкая категория', 'query': rare},
            {'label': '04 · Бюджет не проходит', 'query': {**first, 'budget': 10000}},
            {'label': '05 · Нет категории', 'query': {**first, 'city': 'Зарубежье', 'category': 'Флорист'}},
            {'label': '06 · Банкетный зал', 'query': {**first, 'category': 'Банкетный зал', 'date': '2026-11-14', 'budget': 7000000, 'preferences': 'панорамный вид горы'}}]


class Handler(SimpleHTTPRequestHandler):
    """Expose catalog metadata, matching, and an allowlisted set of UI assets."""
    def json_response(self, value, status=200):
        body = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/api/meta':
            return self.json_response({'options': OPTIONS, 'count': len(PROFILES), 'synthetic': sum(p['synthetic'] for p in PROFILES), 'start': START, 'end': END, 'demos': demos()})
        if self.path.split('?')[0] not in ('/', '/index.html', '/app.js', '/style.css'):
            return self.json_response({'error': 'Страница не найдена.'}, 404)
        super().do_GET()

    def do_POST(self):
        if self.path != '/api/recommend':
            return self.json_response({'error': 'Маршрут не найден.'}, 404)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 16000:
                raise ValueError('Некорректный размер запроса.')
            q = json.loads(self.rfile.read(size))
            start = perf_counter()
            result = recommend(q)
            result['elapsed_ms'] = round((perf_counter() - start) * 1000, 2)
            self.json_response(result)
        except (ValueError, TypeError, UnicodeError) as exc:
            self.json_response({'error': str(exc)}, 400)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--host', default='127.0.0.1')
    args = parser.parse_args()
    print(f'Rio: http://{args.host}:{args.port}', flush=True)
    ThreadingHTTPServer((args.host, args.port), partial(Handler, directory=str(ROOT / 'web'))).serve_forever()
