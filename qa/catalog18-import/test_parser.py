"""Offline parser and refresh regression checks; no source requests are made."""
import importlib.util
import io
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

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


class CurlTransportTests(unittest.TestCase):
    def test_curl_keeps_tls_limits_argv_and_cache_for_html_and_images(self):
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            self.assertFalse(kwargs["shell"])
            self.assertEqual(kwargs["timeout"], 45)
            self.assertNotIn("--insecure", command)
            self.assertIn("--disable", command)
            self.assertEqual(command[command.index("--proto") + 1], "=https")
            self.assertEqual(command[command.index("--proto-redir") + 1], "=https")
            body = b"image fixture" if "/pics/" in command[-1] else b'<div class="card-item">/catalog/</div>'
            Path(command[command.index("--output") + 1]).write_bytes(body)
            return SimpleNamespace(returncode=0, stdout=json.dumps({"http_code": 200, "url_effective": command[-1], "content_type": "image/jpeg" if "/pics/" in command[-1] else "text/html; charset=utf-8", "time_total": 0.1}), stderr="")
        with tempfile.TemporaryDirectory() as directory, patch.object(catalog.shutil, "which", return_value="curl"), patch.object(catalog.subprocess, "run", side_effect=run):
            cache = Path(directory)
            client = catalog.PublicClient(cache, transport="curl", delay=0)
            html, meta = client.get(URL)
            again, cached_meta = client.get(URL)
            image, _ = client.get(catalog.BASE + "pics/cache/985_v_123.jpg", image=True)
            client.get(URL, force_refresh=True)
            self.assertEqual(html, again)
            self.assertEqual(meta["fetchedAt"], cached_meta["fetchedAt"])
            self.assertEqual(meta["transport"], "curl")
            self.assertEqual(len(calls), 3)
            self.assertEqual(calls[0][calls[0].index("--max-filesize") + 1], "50000000")
            self.assertEqual(calls[1][calls[1].index("--max-filesize") + 1], "15000000")
            self.assertEqual(image, b"image fixture")
            self.assertEqual(list(cache.glob("*.download")), [])

    def test_curl_foreign_final_host_is_rejected_and_temp_body_removed(self):
        def run(command, **kwargs):
            Path(command[command.index("--output") + 1]).write_bytes(b"untrusted redirect")
            return SimpleNamespace(returncode=0, stdout=json.dumps({"http_code": 200, "url_effective": "https://example.org/image.jpg"}), stderr="")
        with tempfile.TemporaryDirectory() as directory, patch.object(catalog.shutil, "which", return_value="curl"), patch.object(catalog.subprocess, "run", side_effect=run):
            cache = Path(directory)
            client = catalog.PublicClient(cache, transport="curl")
            with self.assertRaises(ValueError):
                client.curl_get(catalog.BASE + "pics/cache/985_v_123.jpg", image=True)
            self.assertEqual(list(cache.iterdir()), [])


class ParserTests(unittest.TestCase):
    def test_named_cyrillic_brands_have_distinct_source_based_slugs(self):
        inteks = catalog.brand_slug("Интекс", catalog.BASE + "catalog/kolgotki-klassika/dlya-beremennyh/inteks_ikb-1r1k")
        hoh = catalog.brand_slug("ХОХ", catalog.BASE + "catalog/detskoe/kolgotki/hoh_dk-1311")
        self.assertEqual((inteks, hoh), ("inteks", "hoh"))
        self.assertNotEqual(inteks, hoh)

    def test_discovery_includes_four_parent_listings_and_only_childrens_tights(self):
        html = '<a href="/catalog/kolgotki-klassika/tonkie">Тонкие</a><a href="/catalog/detskoe/kolgotki">Колготки</a><a href="/catalog/detskoe/noski">Носки</a>'
        categories = catalog.discover_categories(catalog.TreeParser(html).root)
        urls = {item["url"] for item in categories}
        self.assertEqual(len(categories), 6)
        self.assertEqual(sum(item["scopeLevel"] == "parent" for item in categories), 4)
        self.assertIn(catalog.BASE + "catalog/chulki-pod-poyas", urls)
        self.assertIn(catalog.BASE + "catalog/detskoe/kolgotki", urls)
        self.assertNotIn(catalog.BASE + "catalog/detskoe", urls)
        self.assertNotIn(catalog.BASE + "catalog/detskoe/noski", urls)

    def test_windows1251_header_preserves_russian_text_and_prices(self):
        html = page(card(description="Мужские колготки, прозрачные.", density="Плотность: 20 den"), 1)
        decoded = catalog.decode_html(html.encode("windows-1251"), "text/html; charset=windows-1251")
        row = catalog.parse_listing(decoded, URL, STAMP)["items"][0]
        self.assertEqual(row["_description"], "Мужские колготки, прозрачные.")
        self.assertEqual((row["priceRub"], row["den"]), (800, 20))

    def test_windows1251_meta_without_header_is_detected(self):
        html = '<meta http-equiv="Content-Type" content="text/html; charset=windows-1251">' + page(card(), 1)
        decoded = catalog.decode_html(html.encode("windows-1251"))
        self.assertIn("Товаров: 1", decoded)
        self.assertIn("Мужской прозрачный", decoded)

    def test_declared_utf8_with_invalid_bytes_is_rejected(self):
        with self.assertRaises(UnicodeError):
            catalog.decode_html(b'<meta charset="utf-8">\xff', "text/html; charset=utf-8")

    def test_conflicting_charsets_do_not_silently_corrupt_names(self):
        with self.assertRaises(UnicodeError):
            catalog.decode_html('<meta charset="utf-8">Товаров: 1'.encode("utf-8"), "text/html; charset=windows-1251")

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

    def test_inventory_counter_change_retries_only_that_category_with_fresh_html(self):
        next_url = URL + "/filter/page=1"
        two = card(sku="1") + card(sku="2")
        calls = []
        class ChangingInventory:
            def get(self, url, force_refresh=False):
                calls.append((url, force_refresh))
                if force_refresh:
                    html = page(two, 2)
                else:
                    html = page(two, 3, next_url) if url == URL else page(two, 2)
                return html.encode(), {"fetchedAt": STAMP}
        summary, items, _ = catalog.crawl_category(ChangingInventory(), {"url": URL, "name": "Мужские колготки"})
        self.assertTrue(summary["complete"])
        self.assertEqual(summary["advertisedCount"], 2)
        self.assertTrue(summary["freshRetry"]["succeeded"])
        self.assertEqual(summary["freshRetry"]["previousAdvertisedCount"], 3)
        self.assertEqual(calls, [(URL, False), (next_url, False), (URL, True)])

    def test_second_inventory_counter_change_still_fails_after_one_retry(self):
        next_url = URL + "/filter/page=1"
        two = card(sku="1") + card(sku="2")
        calls = []
        class AlwaysChanging:
            def get(self, url, force_refresh=False):
                calls.append((url, force_refresh))
                html = page(two, 3, next_url) if url == URL else page(two, 2)
                return html.encode(), {"fetchedAt": STAMP}
        summary, _, _ = catalog.crawl_category(AlwaysChanging(), {"url": URL, "name": "Мужские колготки"})
        self.assertFalse(summary["complete"])
        self.assertFalse(summary["freshRetry"]["succeeded"])
        self.assertEqual(len(calls), 4)
        self.assertEqual(sum(fresh for _, fresh in calls), 2)

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


class ImageRefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.site = Path(self.temp.name)
        self.patch = patch.object(catalog, "SITE", self.site)
        self.patch.start()
        self.qa_patch = patch.object(catalog, "QA", self.site / "qa")
        self.qa_patch.start()
        self.Image, _ = catalog.pillow_runtime()
        self.previous = {
            "imageSource": catalog.BASE + "pics/cache/985_v_old.jpg",
            "image": "assets/catalog/loretta-123.webp",
            "thumbnail": "assets/catalog/loretta-123-320.webp",
        }
        for key in ("image", "thumbnail"):
            path = self.site / self.previous[key]
            path.parent.mkdir(parents=True, exist_ok=True)
            self.Image.new("RGB", (24, 32), "red").save(path, "WEBP")

    def tearDown(self):
        self.qa_patch.stop()
        self.patch.stop()
        self.temp.cleanup()

    def item(self, changed=False):
        return {"id": "loretta-123", "imageSource": catalog.BASE + "pics/cache/985_v_new.jpg" if changed else self.previous["imageSource"], "imageNeedsReview": False, "image": None, "thumbnail": None, "width": 0, "height": 0}

    def test_same_source_preserves_valid_legacy_local_images(self):
        class NoNetwork:
            def get(self, *args, **kwargs):
                raise AssertionError("An unchanged valid local photograph must not be fetched")
        row, error = catalog.optimize_image(NoNetwork(), self.item(), self.previous)
        self.assertIsNone(error)
        self.assertEqual(row["image"], self.previous["image"])
        self.assertEqual((row["width"], row["height"]), (24, 32))

    def test_reviewed_source_exclusion_keeps_product_and_price_but_clears_photo(self):
        row = {**self.item(), "imageSource": catalog.BASE + "pics/cache/985_v_1267492.jpg", "priceRub": 800, "model": "0108 High Pantyhose", "image": self.previous["image"], "thumbnail": self.previous["thumbnail"]}
        class NoNetwork:
            def get(self, *args, **kwargs):
                raise AssertionError("Excluded source photograph must not be fetched")
        result, error = catalog.optimize_image(NoNetwork(), row, self.previous)
        self.assertIsNone(error)
        self.assertEqual(result["priceRub"], 800)
        self.assertEqual(result["model"], "0108 High Pantyhose")
        self.assertTrue(result["imageNeedsReview"])
        self.assertIsNone(result["image"])
        self.assertIsNone(result["thumbnail"])

    def test_changed_source_gets_new_file_and_new_photo(self):
        buffer = io.BytesIO()
        self.Image.new("RGB", (30, 42), "blue").save(buffer, "PNG")
        payload = buffer.getvalue()
        calls = []
        class NewImage:
            def get(self, url, image=False):
                calls.append(url)
                return payload, {"fetchedAt": STAMP}
        row, error = catalog.optimize_image(NewImage(), self.item(changed=True), self.previous)
        self.assertIsNone(error)
        self.assertEqual(calls, [row["imageSource"]])
        self.assertNotEqual(row["image"], self.previous["image"])
        self.assertNotEqual(row["thumbnail"], self.previous["thumbnail"])
        with self.Image.open(self.site / row["image"]) as opened:
            red, green, blue = opened.convert("RGB").getpixel((10, 10))
            self.assertGreater(blue, red + 150)
        self.assertTrue((self.site / self.previous["image"]).exists())

    def test_failed_changed_source_does_not_inherit_old_photo(self):
        class FailedImage:
            def get(self, *args, **kwargs):
                raise OSError("new photograph unavailable")
        row, error = catalog.optimize_image(FailedImage(), self.item(changed=True), self.previous)
        self.assertIsNotNone(error)
        self.assertIsNone(row["image"])
        self.assertIsNone(row["thumbnail"])
        self.assertEqual((row["width"], row["height"]), (0, 0))

    def initial_manifest(self):
        entry = {"id": "loretta-123", "image": self.previous["image"], "thumbnail": self.previous["thumbnail"], "width": 24, "height": 32, "sha256": hashlib.sha256((self.site / self.previous["image"]).read_bytes()).hexdigest(), "thumbnailSha256": hashlib.sha256((self.site / self.previous["thumbnail"]).read_bytes()).hexdigest()}
        manifest = {"version": 1, "purpose": "one-time-initial-ci-image-adoption", "provenance": {"githubRunId": "44085884185", "gitCommit": "6fffdb4"}, "items": [entry]}
        path = self.site / "initial-manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def newly_listed_item(self):
        return {**self.item(), "brand": "Platino", "model": "Test", "source": URL + "/platino_test", "sourceProductId": "345", "imageSource": catalog.BASE + "pics/cache/985_v_345.jpg", "checkedAt": STAMP}

    def test_explicit_first_import_manifest_reuses_verified_legacy_pair(self):
        row = self.newly_listed_item()
        adoption = catalog.bind_initial_images([row], self.initial_manifest())
        class NoNetwork:
            def get(self, *args, **kwargs):
                raise AssertionError("Approved first-CI image must not be downloaded again")
        result, error = catalog.optimize_image(NoNetwork(), row, adoption["loretta-123"])
        self.assertIsNone(error)
        self.assertEqual(result["image"], self.previous["image"])

    def test_first_import_manifest_rejects_modified_image_bytes(self):
        path = self.initial_manifest()
        self.Image.new("RGB", (24, 32), "green").save(self.site / self.previous["image"], "WEBP")
        self.assertEqual(catalog.bind_initial_images([self.newly_listed_item()], path), {})

    def test_first_import_manifest_rejects_unmatched_source_product_image(self):
        row = self.newly_listed_item()
        row["imageSource"] = catalog.BASE + "pics/cache/985_v_999.jpg"
        self.assertEqual(catalog.bind_initial_images([row], self.initial_manifest()), {})


class DeploymentSafetyTests(unittest.TestCase):
    def test_restore_only_does_not_create_source_client_even_for_old_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site = root / "site"
            target = site / "data/catalog.json"
            target.parent.mkdir(parents=True)
            snapshot = {"version": 1, "source": {"id": "loretta"}, "checkedAt": "2020-01-01T00:00:00Z", "coverage": {"complete": True, "uniqueProducts": 1}, "items": [{"id": "loretta-123", "brand": "Platino", "title": "Platino Test", "source": URL + "/platino_test", "priceRub": 800, "image": None, "thumbnail": None}]}
            target.write_text(json.dumps(snapshot), encoding="utf-8")
            with patch.object(catalog, "SITE", site), patch.object(catalog, "QA", root / "qa"), patch.object(catalog, "restore_deployed", return_value=(snapshot, 0)), patch.object(catalog, "PublicClient", side_effect=AssertionError("Source client must not be created")) as source:
                code = catalog.main(["--restore-only", "--deployed", "https://example.org/tights-guide/"])
            self.assertEqual(code, 0)
            source.assert_not_called()

    def test_restore_only_rejects_missing_local_photo_without_calling_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site = root / "site"
            target = site / "data/catalog.json"
            target.parent.mkdir(parents=True)
            snapshot = {"version": 1, "source": {"id": "loretta"}, "checkedAt": "2020-01-01T00:00:00Z", "coverage": {"complete": True, "uniqueProducts": 1}, "items": [{"id": "loretta-123", "brand": "Platino", "title": "Platino Test", "source": URL + "/platino_test", "priceRub": 800, "image": "assets/catalog/loretta-123.webp", "thumbnail": None}]}
            target.write_text(json.dumps(snapshot), encoding="utf-8")
            with patch.object(catalog, "SITE", site), patch.object(catalog, "QA", root / "qa"), patch.object(catalog, "restore_deployed", return_value=(snapshot, 0)), patch.object(catalog, "PublicClient", side_effect=AssertionError("Source client must not be created")) as source:
                code = catalog.main(["--restore-only", "--deployed", "https://example.org/tights-guide/"])
            self.assertEqual(code, 3)
            source.assert_not_called()

    def run_with_failed_restore(self, error, seed=True):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site = root / "site"
            target = site / "data/catalog.json"
            target.parent.mkdir(parents=True)
            snapshot = {"version": 1, "source": {"id": "loretta"}, "checkedAt": "2020-01-01T00:00:00Z", "coverage": {"complete": True, "uniqueProducts": 1}, "items": [{"id": "loretta-123", "brand": "Platino", "title": "Platino Test", "source": URL + "/platino_test", "priceRub": 800, "oldPriceRub": None, "image": None, "thumbnail": None}]}
            original = json.dumps(snapshot)
            if seed:
                target.write_text(original, encoding="utf-8")
            with patch.object(catalog, "SITE", site), patch.object(catalog, "QA", root / "qa"), patch.object(catalog, "restore_deployed", side_effect=error):
                code = catalog.main(["--deployed", "https://example.org/tights-guide/", "--offline", "--no-images", "--cache", str(root / "cache")])
            if seed:
                self.assertEqual(target.read_text("utf-8"), original)
            else:
                self.assertFalse(target.exists())
            return code

    def test_remote_json_404_accepts_complete_seed_and_source_error_is_nonfatal(self):
        code = self.run_with_failed_restore(catalog.DeploymentCatalogNotFound("HTTP 404"))
        self.assertEqual(code, 2)

    def test_remote_json_404_without_seed_is_fatal(self):
        code = self.run_with_failed_restore(catalog.DeploymentCatalogNotFound("HTTP 404"), seed=False)
        self.assertEqual(code, 3)

    def test_other_restore_failure_is_fatal_even_with_valid_repository_seed(self):
        code = self.run_with_failed_restore(OSError("Deployment request timed out"))
        self.assertEqual(code, 3)

    def test_interrupted_images_keep_listing_checkpoint_without_replacing_published_data(self):
        menu = "".join(f'<a href="/catalog/kolgotki-klassika/sub-{i}">Раздел {i}</a>' for i in range(40))
        class Source:
            network_count = 0
            cache_count = 0
            def get(self, url):
                return menu.encode("utf-8"), {"fetchedAt": STAMP, "contentType": "text/html; charset=utf-8"}
        def crawled(client, category):
            summary = {**category, "advertisedCount": 1, "collectedCount": 1, "cardCount": 1, "pages": [{"url": category["url"], "count": 1, "checkedAt": STAMP}], "complete": True, "errors": []}
            raw = {"id": "loretta-123", "sku": "123", "sourceProductId": "345", "title": "Platino Test", "source": URL + "/platino_test", "den": 20, "densityText": "20", "priceRub": 800, "oldPriceRub": None, "priceFrom": False, "availability": "in_stock", "imageSource": catalog.BASE + "pics/cache/test.jpg", "checkedAt": STAMP, "_description": "Классические колготки.", "_details": ""}
            return summary, [raw], {"Platino"}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site = root / "site"
            qa = root / "qa"
            target = site / "data/catalog.json"
            target.parent.mkdir(parents=True)
            original = '{"checkedAt":"2020-01-01T00:00:00Z","items":[],"coverage":{"complete":false}}'
            target.write_text(original, encoding="utf-8")
            with patch.object(catalog, "SITE", site), patch.object(catalog, "QA", qa), patch.object(catalog, "PublicClient", return_value=Source()), patch.object(catalog, "crawl_category", side_effect=crawled), patch.object(catalog, "optimize_image", side_effect=RuntimeError("simulated interruption")):
                with self.assertRaisesRegex(RuntimeError, "simulated interruption"):
                    catalog.main(["--resume", "--workers", "1"])
            candidate = json.loads((qa / "catalog-candidate.json").read_text("utf-8"))
            report = json.loads((qa / "coverage-report.json").read_text("utf-8"))
            self.assertEqual(len(candidate["items"]), 1)
            self.assertTrue(candidate["coverage"]["complete"])
            self.assertEqual(candidate["checkedAt"], STAMP)
            self.assertEqual(report["phase"], "listing_complete")
            self.assertFalse(report["published"])
            self.assertFalse(report["imagePhaseComplete"])
            self.assertEqual(target.read_text("utf-8"), original)


if __name__ == "__main__":
    unittest.main()
