"""Offline checks for publication ordering and channel identity in release 17."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("video_builder17", ROOT / "scripts/build-videos.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def video(identifier, date=None, author="Same name", url="https://www.youtube.com/@one", **extra):
    return dict(id=identifier, publishedAt=date, author=author, authorUrl=url, **extra)


def source(identifier="one", name="Same name", **extra):
    return dict(id=identifier, name=name, url="https://www.youtube.com/feed",
                authorUrls=[f"https://www.youtube.com/@{identifier}", f"https://www.youtube.com/channel/UC{identifier}"], **extra)


class PublicationTests(unittest.TestCase):
    def test_known_dates_and_explicit_offsets_represent_the_source_instant(self):
        expected = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)
        for value in ("2026-11-17T12:00:00Z", "2026-11-17T15:00:00+03:00", "2026-11-17T04:00:00-08:00"):
            with self.subTest(value=value):
                self.assertEqual(builder.publication_time(value), expected)
        self.assertEqual(builder.publication_time("2024-02-29"), datetime(2024, 2, 29, tzinfo=timezone.utc))
        self.assertEqual(builder.publication_time("2026-11-17T12:00:00.123456Z").microsecond, 123000)

    def test_missing_invalid_and_zone_less_dates_stay_unknown(self):
        for value in (None, "", 123, "yesterday", "2026-02-29", "2026-02-30T12:00:00Z", "0000-01-01",
                      "2026-13-01", "2026-11-17T12:00:00", "2026-11-17T24:00:00Z", "2026-11-17T12:60:00Z",
                      "2026-11-17T12:00:60Z", "2026-11-17T12:00:00+01:99", "2026-11-17T12:00:00+24:00"):
            with self.subTest(value=value):
                self.assertIsNone(builder.publication_time(value))

    def test_both_orders_use_instants_keep_ties_stable_and_unknown_dates_last(self):
        videos = [video("unknown", checked="2026-11-17"), video("tie-first", "2026-11-17T12:00:00Z"),
                  video("old", "1960-01-01"), video("tie-second", "2026-11-17T15:00:00+03:00"),
                  video("future", "2099-01-01"), video("invalid", "2026-02-30"), video("date-only", "2026-11-16")]
        self.assertEqual([v["id"] for v in builder.sorted_videos(videos)],
                         ["future", "tie-first", "tie-second", "date-only", "old", "unknown", "invalid"])
        self.assertEqual([v["id"] for v in builder.sorted_videos(videos, "oldest")],
                         ["old", "date-only", "tie-first", "tie-second", "future", "unknown", "invalid"])
        self.assertEqual(videos[0]["id"], "unknown")  # No mutation of the featured/data order.


class ChannelTests(unittest.TestCase):
    def test_union_keeps_empty_sources_and_separates_identical_names(self):
        channels = builder.build_channels([video("a"), video("b", url="https://www.youtube.com/@manual")],
                                          [source(), source("empty")])
        self.assertEqual(len(channels), 3)
        self.assertEqual(sorted(c["count"] for c in channels), [0, 1, 1])
        self.assertEqual(len({c["id"] for c in channels}), 3)
        self.assertEqual(len({c["label"] for c in channels}), 3)
        self.assertEqual({v for c in channels for v in c["videoIds"]}, {"a", "b"})
        self.assertEqual(next(c for c in channels if c["id"] == "empty")["videoIds"], [])

    def test_known_aliases_merge_handles_but_do_not_fold_channel_ids(self):
        videos = [video("handle", url="https://m.youtube.com/@ONE/?tracking=1#top"),
                  video("channel", url="https://youtube.com/channel/UCone"),
                  video("different", url="https://youtube.com/channel/UCOne")]
        channels = builder.build_channels(videos, [source()])
        self.assertEqual(next(c for c in channels if c["id"] == "one")["videoIds"], ["handle", "channel"])
        self.assertEqual(len(channels), 2)

    def test_manual_identity_is_stable_and_preserves_the_original_author_url(self):
        url = "https://www.youtube.com/@Manual/?ref=original"
        first = builder.build_channels([video("a", url=url)], [])[0]
        second = builder.build_channels([video("b", url="https://youtube.com/@manual")], [])[0]
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(first["url"], url)

    def test_publisher_identity_only_uses_an_explicitly_configured_host(self):
        publisher = source("journal", name="Publisher", publisherHost="brand.example", verificationUrl="https://brand.example/journal")
        channels = builder.build_channels([video("story", url="https://brand.example/journal/story"),
                                           video("home", url="https://brand.example/"),
                                           video("other", url="https://other.example/")], [publisher])
        self.assertEqual(next(c for c in channels if c["id"] == "journal")["videoIds"], ["story", "home"])
        self.assertEqual(len(channels), 2)

    def test_real_catalogue_contains_every_auto_source_and_manual_author_once(self):
        videos = json.loads((ROOT / "tights-guide/data/videos.json").read_text("utf-8"))
        sources = json.loads((ROOT / "tights-guide/data/video-sources.json").read_text("utf-8"))["sources"]
        channels = builder.build_channels(videos, sources)
        self.assertTrue({s["id"] for s in sources} <= {c["id"] for c in channels})
        assigned = [v for c in channels for v in c["videoIds"]]
        self.assertEqual(len(assigned), len(set(assigned)))
        self.assertEqual(set(assigned), {v["id"] for v in videos})
        self.assertEqual(sum(c["count"] for c in channels), len(videos))
        by_id = {c["id"]: c for c in channels}
        self.assertTrue(any(c["name"] == "Legslavish" for c in channels))
        self.assertIn("oona-linna-youtube", by_id)
        self.assertTrue(set(by_id["legs-by-layla-youtube"]["videoIds"]).isdisjoint(by_id["layla-fashion-youtube"]["videoIds"]))


class StaticBuildTests(unittest.TestCase):
    def test_static_order_dates_channels_and_no_account_feature(self):
        text = (ROOT / "tights-guide/videos.html").read_text("utf-8")
        videos = json.loads((ROOT / "tights-guide/data/videos.json").read_text("utf-8"))
        self.assertEqual(re.findall(r'data-video-card="([^"]+)"', text), [v["id"] for v in builder.sorted_videos(videos)])
        self.assertEqual(len(re.findall(r'data-video-channel="([^"]+)"', text)), len(videos))
        self.assertIn('id="video-screen"><img src="assets/video/snag-motion.jpg"', text)
        for item in videos:
            card = re.search(r'<article[^>]+data-video-card="' + re.escape(item["id"]) + r'".*?</article>', text).group()
            if builder.publication_time(item.get("publishedAt")):
                self.assertIn('datetime="' + item["publishedAt"] + '"', card)
            else:
                self.assertIn("публикации не подтверждена", card)
                self.assertNotIn("datetime=", card)
            self.assertIn('title="Опубликовано за последние 7 дней" hidden>Новое', card)


if __name__ == "__main__":
    unittest.main()
