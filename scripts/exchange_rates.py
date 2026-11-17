"""Dated CBR USD/RUB reference rate; a failed refresh never renews its timestamp."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import json
import math
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

SOURCE = 'https://www.cbr.ru/scripts/XML_daily.asp'
MOSCOW = timezone(timedelta(hours=3))


def parse_stamp(value):
    match = isinstance(value, str) and re.fullmatch(r'(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|[+-](\d{2}):(\d{2}))', value)
    if not match or any(int(match[index] or 0) > maximum for index, maximum in ((2, 23), (3, 59), (4, 59), (5, 23), (6, 59))):
        raise ValueError('Invalid rate check date')
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('Rate check date must have a time zone')
    return stamp.astimezone(timezone.utc)


def validate_rate(value, now=None):
    now = now or datetime.now(timezone.utc)
    if not isinstance(value, dict) or value.get('version') != 1 or value.get('base') != 'USD' or value.get('quote') != 'RUB':
        raise ValueError('Invalid exchange rate schema')
    rate = value.get('rubPerUsd')
    if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not math.isfinite(rate) or not 0 < rate < 1_000_000:
        raise ValueError('Invalid USD/RUB reference rate')
    source = urlsplit(value.get('source') or '')
    if source.scheme != 'https' or source.hostname not in ('www.cbr.ru', 'cbr.ru') or source.username or source.path not in ('/scripts/XML_daily.asp', '/currency_base/daily/'):
        raise ValueError('Unexpected exchange rate source')
    if not isinstance(value.get('date'), str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value['date']):
        raise ValueError('Invalid effective date')
    effective = date.fromisoformat(value['date'])
    checked = parse_stamp(value.get('checkedAt'))
    if effective > now.astimezone(MOSCOW).date() or checked > now + timedelta(minutes=5):
        raise ValueError('Future exchange rate date')
    if effective > checked.astimezone(MOSCOW).date():
        raise ValueError('Effective rate date is later than the source check')
    return value


def parse_cbr(raw, now=None):
    now = now or datetime.now(timezone.utc)
    if len(raw) > 1_000_000 or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('Invalid CBR response')
    root = ET.fromstring(raw)
    if root.tag != 'ValCurs':
        raise ValueError('Not a CBR daily-rate response')
    effective = datetime.strptime(root.attrib['Date'], '%d.%m.%Y').date()
    usd = [item for item in root.findall('Valute') if item.findtext('CharCode') == 'USD']
    if len(usd) != 1:
        raise ValueError('USD rate missing or ambiguous')
    try:
        nominal = Decimal(usd[0].findtext('Nominal', '').replace(' ', '').replace(',', '.'))
        quoted = Decimal(usd[0].findtext('Value', '').replace(' ', '').replace(',', '.'))
        if not nominal.is_finite() or not quoted.is_finite() or nominal <= 0 or quoted <= 0:
            raise ValueError('Invalid CBR amount')
        rate = float(quoted / nominal)
    except (InvalidOperation, ZeroDivisionError) as exc:
        raise ValueError('Invalid CBR amount') from exc
    return validate_rate({'version': 1, 'base': 'USD', 'quote': 'RUB', 'rubPerUsd': rate,
                          'date': effective.isoformat(), 'checkedAt': now.astimezone(timezone.utc).isoformat(),
                          'source': SOURCE, 'sourceName': 'Банк России'}, now)


def refresh_rate(previous, fetch, now=None, force=False):
    """At most one successful request per Moscow day; keep last good rate on failure."""
    now = now or datetime.now(timezone.utc)
    previous = validate_rate(previous, now) if previous else None
    if previous and not force and parse_stamp(previous['checkedAt']).astimezone(MOSCOW).date() == now.astimezone(MOSCOW).date():
        return previous, 'fresh', None
    url = SOURCE + '?date_req=' + now.astimezone(MOSCOW).strftime('%d/%m/%Y')
    try:
        return parse_cbr(fetch(url), now), 'updated', None
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as exc:
        if previous:
            return previous, 'retained', type(exc).__name__
        raise


def preferred_rate(seed, published, now=None):
    """A more recent validated published snapshot wins over an old repository seed."""
    valid = []
    for candidate in (seed, published):
        try:
            valid.append(validate_rate(candidate, now))
        except (TypeError, KeyError, ValueError):
            continue
    return max(valid, key=lambda value: (value['date'], parse_stamp(value['checkedAt']))) if valid else None
