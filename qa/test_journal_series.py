"""Regression checks for journal features regenerated alongside the live feed."""
import hashlib
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("journal_series", ROOT / "scripts/build-journal-series.py")
series = importlib.util.module_from_spec(spec)
spec.loader.exec_module(series)


class JournalSeriesTests(unittest.TestCase):
    def test_rebuild_preserves_neighbouring_feed_and_emits_each_object_once(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            for name in ("journal.html", "business.html", "journal-series.js", "journal-series.css"):
                shutil.copyfile(series.SITE / name, site / name)
            journal_path = site / "journal.html"
            # A feed builder may replace the whole early section before this collection is rebuilt.
            journal_path.write_text(series.clear_block(journal_path.read_text("utf-8"), "journal-series"), "utf-8")
            with patch.object(series, "SITE", site):
                series.build()
                first = {p.name: hashlib.sha256(p.read_bytes()).digest() for p in site.glob("*.html")}
                series.build()
                self.assertEqual(first, {p.name: hashlib.sha256(p.read_bytes()).digest() for p in site.glob("*.html")})
            journal = journal_path.read_text("utf-8")
            self.assertLess(journal.index("<!-- /journal-series -->"), journal.index("<!-- live-sections -->"))
            self.assertEqual(journal.count('id="journal-series"'), 1)
            wear = (site / "five-wears.html").read_text("utf-8")
            self.assertEqual(wear.count('class="diary-day"'), 5)
            self.assertNotIn('id="live-seed"', wear)
            industry = (site / "business.html").read_text("utf-8")
            for anchor in ("factory-floor", "private-label", "batch-plan", "unit-economics"):
                self.assertEqual(industry.count(f'id="{anchor}"'), 1)
                self.assertIn(f'href="#{anchor}"', industry)
            for obj in series.ARCHIVE:
                article = (site / (obj["slug"] + ".html")).read_text("utf-8")
                self.assertEqual(article.count('id="archive-viewer"'), 1)
                self.assertIn(obj["sources"][0][1], article)
                self.assertIn('href="' + obj["image"] + '"', article)
                for desc in obj["responsive"]:
                    self.assertTrue((series.SITE / desc["src"]).is_file())


if __name__ == "__main__":
    unittest.main()
