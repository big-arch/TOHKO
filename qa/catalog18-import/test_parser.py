"""Offline parser and refresh regression checks; no source requests are made."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/collect-catalog18.py"
spec = importlib.util.spec_from_file_location("catalog18", SCRIPT)
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)
URL = catalog.BASE + "catalog/kolgotki-klassika/muzhskie-kolgotki"
STAMP = "2026-11-17T00:00:00Z"


def card(sku="284084", title="Pearl &amp; Poseidon Thor Nylon", price="800", old="1200", available=True, description="Мужской прозрачный бесшовный нейлоновый аксессуар.", density=""):
    prices = f'<span class="card__price"><strong>{price}</strong></span>' if price is not None else ""
    if old is not None:
        prices += f'<span class="sale-card__price-discount">{old}</span>'
    actions = f'<form><input name="tocart" value="{sku}"><input name="goodsId" value="1267438"><button>В КОРЗИНУ</button></form>' if available else f'<span class="available">Нет в наличии</span><button class="predZak" data-hid="{sku}">УВЕДОМИТЬ</button>'
    return f'''<div class="card-item">
    <div class="card-item__img"><img src="/pics/cache/378_v_1267438.jpg"></div>
    <div class="card-item__title"><a href="{URL}/pearl-poseidon_thor">{title}</a></div>
    {prices}<div class="card-item__text">{description}</div>
    <div class="card-details">{density}</div>{actions}</div>'''


def page(cards, count, next_url=None):
    return (f'<link rel="next" href="{next_url}">' if next_url else "") + f'<span class="head__count">Товаров: {count}</span><div class="product-list">{cards}</div><aside>{card(sku="999")}</aside>'


class FakeClient:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url):
        return self.pages[url].encode(), {"fetchedAt": STAMP}


class ParserTests(unittest.TestCase):
    def test_sale_price_and_stock_are_not_confused(self):
        row = catalog.parse_listing(page(card(), 1), URL, STAMP)["items"][0]
        self.assertEqual((row["priceRub"], row["oldPriceRub"]), (800, 1200))
        self.assertEqual((row["id"], row["availability"]), ("loretta-284084", "in_stock"))
        self.assertEqual(len(catalog.parse_listing(page(card(), 1), URL, STAMP)["items"]), 1)

    def test_missing_price_is_null_and_unavailable(self):
        row = catalog.parse_listing(page(card(price=None, old=None, available=False), 1), URL, STAMP)["items"][0]
        self.assertIsNone(row["priceRub"])
        self.assertIsNone(row["oldPriceRub"])
        self.assertEqual(row["availability"], "out_of_stock")
        self.assertEqual(row["id"], "loretta-284084")

    def test_price_from_and_russian_thousands(self):
        row = catalog.parse_listing(page(card(price="от 1&nbsp;299,50", old="1 500"), 1), URL, STAMP)["items"][0]
        self.assertEqual(row["priceRub"], 1299.5)
        self.assertEqual(row["oldPriceRub"], 1500)
        self.assertTrue(row["priceFrom"])

    def test_compound_density_is_not_fabricated(self):
        row = catalog.parse_listing(page(card(density="Плотность: 20/40 den"), 1), URL, STAMP)["items"][0]
        self.assertIsNone(row["den"])
        self.assertEqual(row["densityText"], "20/40")

    def test_pagination_and_source_count(self):
        next_url = URL + "/filter/page=1"
        p1 = page(card(), 2, next_url)
        p2 = page(card(sku="284085").replace("1267438", "1267439").replace("pearl-poseidon_thor", "pearl-poseidon_zeus"), 2)
        summary, items, _ = catalog.crawl_category(FakeClient({URL: p1, next_url: p2}), {"url": URL, "name": "Мужские колготки"})
        self.assertTrue(summary["complete"])
        self.assertEqual(summary["collectedCount"], 2)
        self.assertEqual(len(items), 2)
        self.assertEqual(len(summary["pages"]), 2)

    def test_pagination_cycle_is_incomplete(self):
        summary, _, _ = catalog.crawl_category(FakeClient({URL: page(card(), 2, URL)}), {"url": URL, "name": "Мужские колготки"})
        self.assertFalse(summary["complete"])
        self.assertTrue(any("cycle" in error["reason"] for error in summary["errors"]))

    def test_cumulative_pagination_reads_final_page_and_proves_coverage(self):
        def cards(number):
            return "".join(card(sku=str(1000+i)).replace("1267438", str(10000+i)).replace("pearl-poseidon_thor", f"pearl-poseidon_model{i}") for i in range(number))
        p1, p2, p4 = (URL + f"/filter/page={i}" for i in (1, 2, 4))
        pages = {URL: page(cards(10), 50, p1), p1: page(cards(20), 50, p2), p4: page(cards(50), 50)}
        summary, _, _ = catalog.crawl_category(FakeClient(pages), {"url": URL, "name": "Мужские колготки"})
        self.assertTrue(summary["complete"])
        self.assertEqual(summary["collectedCount"], 50)
        self.assertEqual(summary["paginationMode"], "cumulative")
        self.assertEqual(len(summary["pages"]), 3)
        self.assertEqual(summary["redundantIntermediatePagesSkipped"], 2)

    def test_count_mismatch_is_incomplete(self):
        summary, _, _ = catalog.crawl_category(FakeClient({URL: page(card(), 21)}), {"url": URL, "name": "Мужские колготки"})
        self.assertFalse(summary["complete"])
        self.assertEqual(summary["collectedCount"], 1)
        self.assertEqual(summary["advertisedCount"], 21)

    def test_duplicate_sku_merges_categories_and_keeps_accessory_type(self):
        records = catalog.parse_listing(page(card(), 1), URL, STAMP)["items"]
        results = [({"url": URL, "name": "Мужские колготки"}, records, set()), ({"url": URL + "-other", "name": "Другой раздел"}, records, set())]
        items, excluded, conflicts, unknown = catalog.merge_records(results, {"Pearl & Poseidon"})
        self.assertEqual(len(items), 1)
        self.assertEqual(len(items[0]["categories"]), 2)
        self.assertEqual((items[0]["productKind"], items[0]["gender"]), ("аксессуар", "men"))
        self.assertEqual(items[0]["brand"], "Pearl & Poseidon")
        self.assertTrue(items[0]["imageNeedsReview"])
        self.assertEqual((excluded, conflicts, unknown), ([], [], []))

    def test_leggings_are_excluded_from_mixed_category(self):
        records = catalog.parse_listing(page(card(description="Леггинсы из хлопка."), 1), URL, STAMP)["items"]
        items, excluded, _, _ = catalog.merge_records([({"url": URL, "name": "Мужские колготки"}, records, set())], {"Pearl & Poseidon"})
        self.assertEqual(items, [])
        self.assertEqual(len(excluded), 1)

    def test_external_next_link_rejected(self):
        with self.assertRaises(ValueError):
            catalog.parse_listing(page(card(), 2, "https://example.com/private"), URL, STAMP)

    def test_failed_refresh_preserves_existing_json_and_date(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site = root / "site"
            target = site / "data/catalog.json"
            target.parent.mkdir(parents=True)
            before = '{"checkedAt":"2020-01-01T00:00:00Z","items":[{"priceRub":800}],"coverage":{"complete":true}}'
            target.write_text(before, encoding="utf-8")
            with patch.object(catalog, "SITE", site), patch.object(catalog, "QA", root / "qa"):
                code = catalog.main(["--offline", "--no-images", "--cache", str(root / "cache")])
            self.assertEqual(code, 2)
            self.assertEqual(target.read_text("utf-8"), before)

    def test_daily_guard_only_accepts_successful_recent_snapshot(self):
        data = {"checkedAt": catalog.utc_now(), "coverage": {"complete": True}, "items": [{}]}
        self.assertTrue(catalog.catalog_is_recent(data))
        data["coverage"]["complete"] = False
        self.assertFalse(catalog.catalog_is_recent(data))


if __name__ == "__main__":
    unittest.main()
