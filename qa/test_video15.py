"""Release 15: neutral textile discovery, fair limits and honest archives."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "qa"))
from video_feed import FetchError, classify, collect, validate_config
from test_video_feed import NOW, SOURCE, ID, config, feed, embed, store, updater


class TextileTests(unittest.TestCase):
    def test_textile_profile_accepts_material_sounds_not_every_asmr_video(self):
        for title in ("Fancy Fabrics ○ ASMR", "ASMR Nylon Gloves Mic Scratching Sounds", "АСМР шорох ткани", "ASMR Tights Scratching Sounds | No Talking"):
            with self.subTest(title=title):
                self.assertEqual(classify(title, profile="textile-asmr"), ["asmr"])
        for title in ("ASMR face massage", "ASMR whispers for sleep", "ASMR Nylon Tights and High Heels", "How to choose tights", "ASMR wet mouth sounds"):
            self.assertEqual(classify(title, "I also make fabric and tights videos", profile="textile-asmr"), [])

    def test_adult_promotion_or_fetish_is_not_neutral_textile_content(self):
        for title, description in (("ASMR fabric sounds", "My onlyfans: https://onlyfans.com/example"),
                                   ("ASMR sensual nylon fabric sounds", ""),
                                   ("Колготки: обзор", "Фетиш-контент"),
                                   ("Secretary siren stockings", "")):
            self.assertEqual(classify(title, description), [])
        self.assertEqual(classify("How to style tights", "Winter outfit ideas"), ["choice", "styling"])

    def test_verified_asmr_keeps_separate_topic_and_source_language(self):
        settings = config()
        settings["sources"][0].update(profile="textile-asmr", language="ru")
        title = "АСМР звуки ткани колготок"
        catalog, state = collect(settings, [], {}, lambda url: feed(title=title) if "feeds/" in url else embed(title=title), store, NOW)
        self.assertEqual(catalog[0]["topics"], ["asmr"])
        self.assertEqual(catalog[0]["language"], "ru")
        self.assertEqual(state["added"], 1)

    def test_one_channel_does_not_consume_the_whole_new_video_budget(self):
        settings = config()
        settings["maxNewPerSource"] = 1
        raw = feed()
        entry = raw[raw.index(b"<entry>"):raw.index(b"</entry>")+8]
        raw = raw.replace(b"</feed>", entry.replace(ID.encode(), b"xxxxxxxxxxx") + b"</feed>")
        catalog, state = collect(settings, [], {}, lambda url: raw if "feeds/" in url else embed(), store, NOW)
        self.assertEqual(len(catalog), 1)
        self.assertEqual(state["sources"][0]["candidates"], 2)

    def test_configuration_rejects_duplicate_channels_or_unknown_profiles(self):
        settings = config()
        duplicate = copy.deepcopy(SOURCE)
        duplicate["id"] = "duplicate-channel"
        settings["sources"].append(duplicate)
        with self.assertRaises(ValueError):
            validate_config(settings)
        settings = config()
        settings["sources"][0]["profile"] = "all-channel-videos"
        with self.assertRaises(ValueError):
            validate_config(settings)

    def test_collection_network_budget_stops_before_another_request(self):
        fetch = updater.Fetcher(config())
        fetch.deadline = 0
        with patch.object(updater.subprocess, "run") as process:
            with self.assertRaises(FetchError):
                fetch(SOURCE["url"])
            process.assert_not_called()

    def test_removed_source_cannot_return_from_deployed_snapshot(self):
        removed = dict(id="xxxxxxxxxxx", addedBy="feed", sourceId="removed-source", title="Old tights review", author="Old")
        curated = dict(id="curated", title="Curated archive", author="Author")
        catalog, _state = collect(config(), [removed, curated], {}, lambda url: feed(title="Unrelated jacket"), store, NOW)
        self.assertEqual(catalog, [curated])

    def test_manual_archive_has_real_date_evidence_or_explicit_unknown(self):
        videos = json.loads((ROOT / "tights-guide/data/videos.json").read_text("utf-8"))
        archive = [v for v in videos if v.get("archive")]
        self.assertTrue(archive)
        for video in archive:
            self.assertEqual(video["addedBy"], "curated")
            self.assertTrue(video["kind"].startswith("Архив"))
            if video.get("publishedAt"):
                self.assertEqual(video["dateStatus"], "verified")
                self.assertTrue(video["dateVerificationUrl"].startswith("https://www.youtube.com/watch?v="))
                self.assertNotEqual(video["publishedAt"][:10], video["checked"])
            else:
                self.assertEqual(video["dateStatus"], "unconfirmed")
                self.assertNotIn("dateSource", video)


if __name__ == "__main__":
    unittest.main()
