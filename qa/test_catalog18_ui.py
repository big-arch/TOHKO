"""Builder regressions using temporary QA-only records; production data is untouched."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_catalog", ROOT / 'scripts/build-catalog.py')
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)
NOW = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)
RATE = {"version": 1, "base": "USD", "quote": "RUB", "rubPerUsd": 82.5143, "date": "2026-11-17", "checkedAt": "2026-11-17T10:00:00Z", "source": "https://www.cbr.ru/currency_base/daily/", "sourceName": "Банк России"}


def fixture(count=53):
    return {"version": 1, "source": {"name": "QA only", "url": "https://example.org/"}, "checkedAt": "2026-11-17T10:00:00Z", "items": [{"id": f"qa-{i:03d}", "brand": "QA brand", "title": f"QA model {i:03d}", "model": f"Model {i:03d}", "productKind": "колготки", "gender": "unknown", "priceRub": None if i == 0 else 1000, "source": f"https://example.org/qa/{i}", "checkedAt": "2026-11-17T10:00:00Z"} for i in range(count)]}


class BuilderTests(unittest.TestCase):
    def test_static_subset_and_factual_noscript(self):
        page = BUILD.body_markup(fixture(), RATE, NOW)
        self.assertEqual(page.count('<article class="catalog-card"'), 48)
        self.assertIn('первые 48 из 53 моделей', page)
        self.assertIn('53</strong> моделей', page)
        self.assertIn('≈ $12.12', page)
        self.assertIn('82,5143', page)
        self.assertNotIn('≈ $0.00', page)

    def test_invalid_rates_preserve_rub(self):
        for rate in [None, {}, {**RATE, 'date': '2026-02-30'}, {**RATE, 'date': '2026-11-18'}, {**RATE, 'rubPerUsd': 0}, {**RATE, 'checkedAt': None}]:
            page = BUILD.body_markup(fixture(2), rate, NOW)
            self.assertIn('1\xa0000 ₽', page)
            self.assertNotIn('≈ $', page)

    def test_rate_day_and_timestamp_use_strict_moscow_rules(self):
        midnight = datetime(2026, 11, 16, 21, 1, tzinfo=timezone.utc)
        self.assertTrue(BUILD.rate_valid({**RATE, 'checkedAt': '2026-11-16T21:00:00Z'}, midnight))
        for date in ['2026-02-30T10:00:00Z', '2026-11-16T24:00:00Z', '2026-11-16T12:60:00Z', '2026-11-16T12:00:60Z', '2026-11-16T12:00:00+24:00', '2026-11-16T12:00:00+03:60', '2026-11-16T12:00:00']:
            self.assertIsNone(BUILD.timestamp(date))

    def test_validation_rejects_zeros_duplicates_and_unsafe_assets(self):
        for mutate in [lambda data: data['items'][0].update(priceRub=0), lambda data: data['items'].append(data['items'][0]), lambda data: data['items'][0].update(image='assets/catalog/../secret'), lambda data: data['items'][0].update(source='javascript:bad')]:
            data = fixture(2)
            mutate(data)
            with self.assertRaises(ValueError):
                BUILD.validate(data)

    def test_build_is_repeatable_and_only_writes_owned_outputs(self):
        with tempfile.TemporaryDirectory(prefix='catalog18-qa-') as temp:
            folder = Path(temp)
            (folder / 'input.json').write_text(json.dumps(fixture()), encoding='utf-8')
            (folder / 'rate.json').write_text(json.dumps(RATE), encoding='utf-8')
            output = folder / 'output'
            BUILD.build(folder / 'input.json', folder / 'rate.json', output, now=NOW)
            first = {path.relative_to(output).as_posix(): path.read_bytes() for path in output.rglob('*') if path.is_file()}
            BUILD.build(folder / 'input.json', folder / 'rate.json', output, now=NOW)
            second = {path.relative_to(output).as_posix(): path.read_bytes() for path in output.rglob('*') if path.is_file()}
            self.assertEqual(first, second)
            self.assertEqual(set(first), {'catalog.html', 'data/catalog.js', 'data/exchange-rate.js'})
            self.assertNotIn('news-seed', first['catalog.html'].decode())
            (folder / 'rate.json').write_text('{invalid JSON', encoding='utf-8')
            BUILD.build(folder / 'input.json', folder / 'rate.json', output, now=NOW)
            self.assertEqual((output / 'data/exchange-rate.js').read_text(encoding='utf-8'), 'window.TONKO_EXCHANGE_RATE = null;\n')
            self.assertNotIn('≈ $', (output / 'catalog.html').read_text(encoding='utf-8'))

    def test_output_json_cannot_break_out_of_script(self):
        script = BUILD.script_data('TONKO_CATALOG', {'name': '</script><script>bad</script>'})
        self.assertNotIn('</script>', script)
        self.assertIn('\\u003c/script>', script)


if __name__ == '__main__':
    unittest.main()
