"""Offline checks for curated knowledge and idempotent HTML integration."""
import importlib.util
import json
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_assistant", ROOT / "scripts/build-assistant.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class AssistantBuildTests(unittest.TestCase):
    def test_news_requires_ready_text_not_image_or_raw_excerpt(self):
        paragraph = " ".join(["Проверенный текст публикации о колготках и выборе фактуры."] * 10)
        article = {"id": "a123", "title": "Готовая статья", "summary": "Подготовленный пересказ материала источника о новой коллекции.",
                   "sections": [{"heading": "Детали", "paragraphs": [paragraph]}], "publishedAt": "2026-11-16T07:00:00Z", "source": "Источник",
                   "publication": {"status": "ready"}, "ai": {"generatedAt": "2026-11-16"}}
        pending = copy.deepcopy(article); pending.update(id="pending", publication={"status": "pending"})
        failed = copy.deepcopy(article); failed.update(id="failed", publication={"status": "failed"})
        no_text = copy.deepcopy(article); no_text.update(id="image-only", summary="", sections=[], illustration={"src": "assets/cover.jpg"}, backgroundImage="assets/cover.jpg", excerpt=paragraph)
        short = copy.deepcopy(article); short.update(id="too-short", sections=[{"heading": "Анонс", "paragraphs": ["Недостаточный текст"]}])
        legacy = copy.deepcopy(article); legacy["id"] = "legacy"; legacy.pop("publication"); legacy.pop("ai")
        docs = builder.news_documents({"items": [article, pending, failed, no_text, short, legacy]})
        self.assertEqual({d["id"] for d in docs}, {"news-a123", "news-legacy"})
        self.assertIn("AI-пересказ", next(d["text"] for d in docs if d["id"] == "news-a123"))
        self.assertTrue(all(d["href"].startswith("news.html#story-") for d in docs))
        self.assertTrue(all(len(d["text"]) <= 1800 for d in docs))

    def test_snapshots_match_and_links_exist(self):
        public = (ROOT / "tights-guide/data/assistant-knowledge.json").read_bytes()
        server = (ROOT / "supabase/functions/tonko-assistant/knowledge.json").read_bytes()
        self.assertEqual(public, server)
        data = json.loads(server)
        self.assertGreater(len(data["documents"]), 100)
        ids = [d["id"] for d in data["documents"]]
        self.assertEqual(len(ids), len(set(ids)))
        for d in data["documents"]:
            target = d["href"].split("?")[0].split("#")[0]
            self.assertTrue((ROOT / "tights-guide" / target).is_file(), d["href"])
            self.assertNotEqual(target, "fetish.html")
            if target == "brand.html":
                self.assertIn("?brand=", d["href"])
        self.assertIn("guide-size", ids)
        self.assertIn("guide-medical", ids)

    def test_injection_is_idempotent_and_excludes_retired_page(self):
        with tempfile.TemporaryDirectory() as folder:
            site = Path(folder)
            original = "<!doctype html><html><head><title>T</title></head><body><main>Page</main></body></html>"
            (site / "index.html").write_text(original, encoding="utf-8")
            (site / "fetish.html").write_text(original, encoding="utf-8")
            with patch.object(builder, "SITE", site):
                self.assertEqual(builder.inject_pages(), 1)
                once = (site / "index.html").read_text(encoding="utf-8")
                builder.inject_pages()
                twice = (site / "index.html").read_text(encoding="utf-8")
            self.assertEqual(once, twice)
            self.assertEqual(twice.count('src="assistant.js'), 1)
            self.assertEqual(twice.count('href="assistant.css'), 1)
            self.assertEqual((site / "fetish.html").read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
