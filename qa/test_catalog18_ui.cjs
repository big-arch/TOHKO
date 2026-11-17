/* Pure catalogue logic: no network, DOM, or fabricated production records. */
const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
const ui = require('../tights-guide/catalog.js');

const NOW = Date.parse('2026-11-17T12:00:00Z');
const RATE = {base: 'USD', quote: 'RUB', rubPerUsd: 82.5143, date: '2026-11-17', checkedAt: '2026-11-17T10:00:00Z', source: 'https://www.cbr.ru/currency_base/daily/', sourceName: 'Банк России'};
const row = (id, brand, priceRub, extra = {}) => ({id, brand, title: brand + ' ' + id, model: id, priceRub, productKind: 'колготки', gender: 'women', categories: [], checkedAt: '2026-11-17T10:00:00Z', source: 'https://example.org/products/' + id, ...extra});
const ROWS = [row('model-10', 'Zulu', 250), row('model-2', 'Alpha', 1250), row('missing-a', 'Alpha', null), row('model-20', 'Beta', 500), row('model-5', 'Alpha', 5000, {gender: 'men', productKind: 'чулки', den: 20}), row('missing-z', 'Zulu', null)];

test('RUB/USD division and two decimal USD values retain the official four-place rate', () => {
  assert.equal(ui.priceText(row('x', 'A', 1000), RATE, NOW).usd, '≈ $12.12');
  assert.equal(ui.priceText(row('x', 'A', 825.143, {priceFrom: true}), RATE, NOW).usd, '≈ от $10.00');
  assert.match(ui.priceText(row('x', 'A', 1000), RATE, NOW).rub, /^1\s000 ₽$/);
  assert.match(ui.rateMarkup(RATE, NOW), /82,5143/);
  assert.equal(ui.priceText(row('x', 'A', null), RATE, NOW).usd, '');
});

test('missing, malformed, non-positive, undated and future rates never manufacture USD', () => {
  for (const rate of [null, {}, {...RATE, rubPerUsd: 0}, {...RATE, rubPerUsd: '80'}, {...RATE, rubPerUsd: NaN}, {...RATE, rubPerUsd: Infinity}, {...RATE, date: ''}, {...RATE, date: '2026-02-30'}, {...RATE, date: '2026-11-18'}, {...RATE, quote: 'EUR'}, {...RATE, checkedAt: 'nonsense'}, {...RATE, checkedAt: '2026-11-18T12:00:00Z'}]) {
    assert.equal(ui.validRate(rate, NOW), null);
    assert.equal(ui.priceText(row('x', 'A', 1000), rate, NOW).usd, '');
  }
  assert.equal(ui.validDay('2024-02-29'), true);
  assert.equal(ui.validDay('2025-02-29'), false);
});

test('48-hour price staleness does not invent a check date', () => {
  assert.equal(ui.freshness('2026-11-15T12:00:00Z', NOW), 'fresh');
  assert.equal(ui.freshness('2026-11-15T11:59:59Z', NOW), 'stale');
  for (const date of [null, '', '2026-11-17', '2026-02-30T10:00:00Z', '2026-11-18T10:00:00Z', '2026-11-16T24:00:00Z', '2026-11-16T12:60:00Z', '2026-11-16T12:00:60Z', '2026-11-16T12:00:00+24:00', '2026-11-16T12:00:00+03:60']) assert.equal(ui.freshness(date, NOW), 'unknown');
});

test('a new effective day begins at Moscow midnight, not UTC midnight', () => {
  const midnight = Date.parse('2026-11-16T21:01:00Z');
  const rate = {...RATE, date: '2026-11-17', checkedAt: '2026-11-16T21:00:00Z'};
  assert.equal(ui.validRate(rate, midnight), rate);
  assert.equal(ui.validRate(rate, midnight - 2 * 60 * 1000), null);
});

test('price sort crosses brand boundaries, while null prices stay last in both directions', () => {
  const selected = sort => ui.selectItems(ROWS, {...ui.DEFAULTS, sort});
  assert.deepEqual(selected('price-asc').map(r => r.priceRub), [250, 500, 1250, 5000, null, null]);
  assert.deepEqual(selected('price-desc').map(r => r.priceRub), [5000, 1250, 500, 250, null, null]);
  assert.equal(selected('price-asc')[0].brand, 'Zulu');
  assert.deepEqual(selected('brand').map(r => r.brand), ['Alpha', 'Alpha', 'Alpha', 'Beta', 'Zulu', 'Zulu']);
  assert.deepEqual([row('20', 'A', 1), row('2', 'A', 1), row('10', 'A', 1)].sort(ui.compareItems).map(r => r.id), ['2', '10', '20']);
});

test('mixed Latin and Cyrillic brands retain the static directory order after hydration', () => {
  const rows = [row('x', 'Хох', 1), row('i', 'Интекс', 1), row('a', 'Adrian', 1)];
  assert.deepEqual(ui.selectItems(rows, ui.DEFAULTS).map(r => r.brand), ['Adrian', 'Интекс', 'Хох']);
});

test('all price band boundaries are disjoint, with unknown separate', () => {
  const cases = [[0, 'unknown'], [null, 'unknown'], [499.99, 'under500'], [500, '500-999'], [999.99, '500-999'], [1000, '1000-1999'], [1999.99, '1000-1999'], [2000, '2000-4999'], [4999.99, '2000-4999'], [5000, '5000plus']];
  for (const [price, expected] of cases) {
    assert.deepEqual([...Object.keys(ui.BANDS), 'unknown'].filter(band => ui.priceBand({priceRub: price}, band)), [expected]);
  }
});

test('brand, type, category, price and multi-word query are combined', () => {
  const state = {...ui.DEFAULTS, brand: 'Alpha', kind: 'чулки', gender: 'men', price: '5000plus', q: 'ALPHA 20 den'};
  assert.deepEqual(ui.selectItems(ROWS, state).map(r => r.id), ['model-5']);
  assert.deepEqual(ui.selectItems(ROWS, {...state, price: 'under500'}), []);
  assert.equal(ui.selectItems([row('ёлочка', 'A', 1)], {...ui.DEFAULTS, q: 'елочка'}).length, 1);
});

test('URL states round-trip Cyrillic and ampersands and reject unknown choices', () => {
  const rows = [...ROWS, row('цвет', 'A & Б', 500)];
  const state = {...ui.DEFAULTS, brand: 'A & Б', q: 'колготки & 20', price: '500-999', sort: 'price-desc'};
  const query = ui.stateQuery(state, 'сложный/id');
  assert.deepEqual(ui.readState(query, rows), state);
  assert.equal(new URLSearchParams(query).get('product'), 'сложный/id');
  assert.equal(ui.stateQuery(ui.DEFAULTS), '');
  assert.deepEqual(ui.readState('?brand=Unknown&kind=no&gender=no&price=no&sort=no', ROWS), ui.DEFAULTS);
});

test('card HTML escapes source text, distinguishes catalogue images and rejects unsafe links', () => {
  const html = ui.cardMarkup(row('x" onclick="bad', '<Alpha>', 1000, {title: '<script>bad</script>', source: 'javascript:alert(1)', image: '../secret', checkedAt: null}), RATE, ui.DEFAULTS, NOW);
  assert.ok(!html.includes('<script>'));
  assert.ok(!html.includes('href="javascript:'));
  assert.ok(!html.includes('src="../'));
  assert.match(html, /&lt;Alpha&gt;/);
  assert.match(html, /Дата проверки не указана/);
});

test('shared price helpers are available on archive pages without catalogue DOM', () => {
  const context = {window: {document: {getElementById: () => null}}};
  vm.runInNewContext(fs.readFileSync(require.resolve('../tights-guide/catalog.js'), 'utf8'), context);
  assert.equal(typeof context.window.TONKO_CATALOG_HELPERS.priceText, 'function');
  assert.equal(context.window.TONKO_CATALOG_HELPERS.priceText({priceRub: 1000}, RATE, NOW).usd, '≈ $12.12');
});
