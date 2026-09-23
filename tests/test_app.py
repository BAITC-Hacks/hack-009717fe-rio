"""Behavioral checks for matching; Russian fixtures mirror the public UI contract."""
import math
import unittest
from datetime import date, timedelta
from time import perf_counter
from app import PROFILES, OPTIONS, recommend, demos, reasons


class RecommendationTests(unittest.TestCase):
    def setUp(self):
        self.q = dict(city='Алматы', category='Ведущий', event_format='корпоратив', date='2026-10-01', budget=1500000, hours=4, language='русский', preferences='юмор импровизация')

    def test_source_integrity(self):
        self.assertEqual(len(PROFILES), 66)
        self.assertEqual(len({p['id'] for p in PROFILES}), 66)
        self.assertEqual(sum(p['synthetic'] for p in PROFILES), 13)
        for p in PROFILES:
            self.assertGreater(p['price_from_kzt'], 0)
            for d in p['busy_dates']:
                self.assertTrue('2026-09-23' <= d <= '2026-12-31')
                date.fromisoformat(d)

    def test_every_day_and_category_respects_all_constraints(self):
        for offset in range(100):
            d = (date(2026, 9, 23) + timedelta(days=offset)).isoformat()
            for category in OPTIONS['categories']:
                q = {**self.q, 'date': d, 'category': category}
                r = recommend(q)
                self.assertLessEqual(len(r['cards']), 3)
                for p in r['cards']:
                    self.assertEqual(reasons(p, q), [])
                    self.assertEqual(p['city'], q['city'])
                    self.assertIn(category, p['categories'])

    def test_deterministic_even_with_reordered_catalog(self):
        a = recommend(self.q)
        self.assertEqual(a, recommend(dict(reversed(list(self.q.items())))))
        b = recommend(self.q, list(reversed(PROFILES)))
        self.assertEqual(a['cards'], b['cards'])

    def test_three_outcomes_and_demos(self):
        scenarios = demos()
        self.assertEqual(recommend(scenarios[0]['query'])['status'], 'matched')
        self.assertGreater(recommend(scenarios[0]['query'])['eligible_count'], 3)
        rare = recommend(scenarios[2]['query'])
        self.assertTrue(0 < len(rare['cards']) < 3)
        self.assertIn('Меньше трёх', rare['message'])
        self.assertEqual(recommend(scenarios[3]['query'])['status'], 'no_match')
        self.assertEqual(recommend(scenarios[4]['query'])['status'], 'no_category')
        self.assertTrue(recommend(scenarios[5]['query'])['pool_count'])

    def test_date_changes_due_to_busy_calendar(self):
        a, b = [x['query'] for x in demos()[:2]]
        first = recommend(a)['cards']
        second = recommend(b)['cards']
        self.assertNotEqual([p['id'] for p in first], [p['id'] for p in second])
        self.assertTrue(any(b['date'] in p['busy_dates'] for p in first))

    def test_budget_boundary_and_null_hours(self):
        p = next(p for p in PROFILES if p['max_hours'] is None)
        free = next((date(2026, 10, d).isoformat() for d in range(1,32) if date(2026,10,d).isoformat() not in p['busy_dates']))
        q = {**self.q, 'date':free, 'category':p['categories'][0], 'city':p['city'], 'event_format':p['event_formats'][0], 'budget':p['price_from_kzt'], 'hours':24, 'language':''}
        self.assertEqual(reasons(p,q), [])
        self.assertIn('budget', reasons(p,{**q,'budget':q['budget']-1}))
        self.assertIn('busy', reasons(p,{**q,'date':p['busy_dates'][0]}))

    def test_optional_constraints(self):
        p = next(p for p in PROFILES if p['max_hours'] is not None)
        self.assertIn('hours', reasons(p, {**self.q, 'hours': p['max_hours'] + 1}))
        self.assertNotIn('hours', reasons(p, {**self.q, 'hours': None}))
        self.assertIn('format', reasons({**p,'event_formats':[]}, self.q))
        self.assertIn('language', reasons({**p,'languages':[]}, self.q))

    def test_invalid_inputs(self):
        for patch in ({'date':'2026-02-30'}, {'date':'2027-01-01'}, {'date':'2026-09-22'}, {'date':'20261001'}, {'budget':0}, {'budget':-1}, {'budget':True}, {'budget':math.nan}, {'budget':'200'}, {'hours':-2}, {'language':'unknown'}, {'preferences':None}, {'event_format':'unknown'}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                recommend({**self.q, **patch})
        for q in ([], None, {}, {'city':'Алматы'}):
            with self.assertRaises(ValueError):
                recommend(q)

    def test_explanations_are_grounded_and_distinct(self):
        for scenario in demos():
            result = recommend(scenario['query'])
            self.assertEqual(len({p['evidence'] for p in result['cards']}), len(result['cards']))
            for p in result['cards']:
                self.assertIn(scenario['query']['date'], p['explanation'])
                self.assertIn(p['evidence'].removesuffix('…'), p['description'])

    def test_latency(self):
        start = perf_counter()
        for _ in range(100):
            recommend(self.q)
        self.assertLess(perf_counter()-start, 10)


if __name__ == '__main__':
    unittest.main()
