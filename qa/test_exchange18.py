"""Currency display cannot silently invert, invent, or redate source quotes."""
from datetime import datetime, timedelta, timezone
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from exchange_rates import parse_cbr, preferred_rate, refresh_rate, validate_rate

NOW = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)


def xml(day='17.11.2026', nominal='1', value='80,2500'):
    return f'<ValCurs Date="{day}"><Valute ID="R01235"><CharCode>USD</CharCode><Nominal>{nominal}</Nominal><Value>{value}</Value></Valute></ValCurs>'.encode()


class ExchangeRateTests(unittest.TestCase):
    def test_decimal_comma_and_nominal_produce_rubles_per_dollar(self):
        rate = parse_cbr(xml(nominal='10', value='802,5000'), NOW)
        self.assertEqual(rate['rubPerUsd'], 80.25)
        self.assertEqual(802.5 / rate['rubPerUsd'], 10)
        self.assertEqual(rate['date'], '2026-11-17')

    def test_non_trading_day_keeps_official_effective_date(self):
        rate = parse_cbr(xml(day='14.11.2026'), NOW)
        self.assertEqual(rate['date'], '2026-11-14')
        self.assertEqual(rate['checkedAt'], NOW.isoformat())

    def test_invalid_quotes_and_entities_are_rejected(self):
        for raw in (xml(value='0'), xml(value='NaN'), xml(nominal='0'), xml(day='18.11.2026'),
                    b'<html>Error</html>', b'<ValCurs Date="17.11.2026"/>',
                    b'<!DOCTYPE x [<!ENTITY x "bad">]><ValCurs/>'):
            with self.subTest(raw=raw):
                with self.assertRaises((ValueError, KeyError)):
                    parse_cbr(raw, NOW)

    def test_failed_refresh_preserves_price_and_check_date(self):
        old = parse_cbr(xml(day='16.11.2026'), NOW - timedelta(days=1))
        before = copy.deepcopy(old)
        def fail(_): raise OSError('offline')
        result, status, _ = refresh_rate(old, fail, NOW)
        self.assertEqual(status, 'retained')
        self.assertEqual(result, before)

    def test_same_moscow_day_skips_redundant_requests(self):
        old = parse_cbr(xml(), NOW)
        result, status, _ = refresh_rate(old, lambda _: self.fail('Unexpected request'), NOW + timedelta(hours=1))
        self.assertEqual(status, 'fresh')
        self.assertEqual(result, old)

    def test_refresh_requests_current_moscow_day(self):
        requested = []
        def fetch(url):
            requested.append(url)
            return xml(day='18.11.2026')
        rate, _, _ = refresh_rate(None, fetch, NOW.replace(hour=22))
        self.assertTrue(requested[0].endswith('date_req=18/11/2026'))
        self.assertEqual(rate['date'], '2026-11-18')

    def test_public_snapshot_never_regresses_to_seed_or_future(self):
        old = parse_cbr(xml(day='16.11.2026'), NOW - timedelta(days=1))
        current = parse_cbr(xml(), NOW)
        self.assertEqual(preferred_rate(old, current, NOW), current)
        invalid = {**current, 'date': '2026-11-18'}
        self.assertEqual(preferred_rate(current, invalid, NOW), current)

    def test_schema_rejects_nonfinite_boolean_and_unzoned_values(self):
        rate = parse_cbr(xml(), NOW)
        for change in ({'rubPerUsd': True}, {'rubPerUsd': float('nan')}, {'source': 'https://other.example/'},
                       {'checkedAt': '2026-11-17T12:00:00'}, {'date': '2026-02-30'},
                       {'checkedAt': '2026-11-16T24:00:00Z'}, {'checkedAt': '2026-11-17T10:00:00+03:60'},
                       {'checkedAt': '2026-11-17T10:60:00Z'}, {'date': '20261117'}):
            with self.subTest(change=change):
                with self.assertRaises((ValueError, KeyError)):
                    validate_rate({**rate, **change}, NOW)


if __name__ == '__main__':
    unittest.main()
