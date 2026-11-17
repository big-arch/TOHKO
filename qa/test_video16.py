"""Release 16: explicit fashion reviews, colour terminology and clean copy."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "qa"))
from video_feed import classify, collect, validate_config
from test_video_feed import NOW, config, feed, embed, store


class FashionReviewTests(unittest.TestCase):
    def test_review_profile_requires_both_subject_and_editorial_title_cue(self):
        for title in (
            "Cecilia de Rafael Ibiza Dotty Tights Try On & Review",
            "FASHION HACK: Nylon Layering!",
            "How to style fishnets for winter",
            "Styling Glossy Black Leggings & Top for a Night Out",
            "Как носить кружевные колготки осенью | Двуслойный лайфхак",
            "Стилизуем колготки под Louboutin",
        ):
            with self.subTest(title=title):
                self.assertTrue(classify(title, profile="fashion-review"))
        for title in (
            "#tights #fashion #nylon", "#nylon #style", "#tights #review", "I love these tights", "Fashion pantyhose… yay or nay?",
            "Would you sit with me?", "Christmas outfit try on", "Leather jacket review",
            "I adore these new pantyhose from Calzedonia! What do you think?",
        ):
            with self.subTest(title=title):
                self.assertEqual(classify(title, "tights review, styling and try on", profile="fashion-review"), [])

    def test_nude_colour_exception_is_narrow_and_opt_in(self):
        for title in ("Layering Sheer Nude Stockings", "Nude-tone tights review", "Nude coloured pantyhose try on"):
            with self.subTest(title=title):
                self.assertTrue(classify(title, profile="fashion-review"))
                self.assertEqual(classify(title, profile="fashion"), [])
        for title in ("Nude model in stockings: styling", "Naked tights try on", "Nude look tights review",
                      "Nude stockings fetish review", "Bikini and tights try on", "Sensual nylon layering"):
            with self.subTest(title=title):
                self.assertEqual(classify(title, profile="fashion-review"), [])
        self.assertEqual(classify("Nude stockings review", "OnlyFans: https://onlyfans.com/example", profile="fashion-review"), [])

    def test_original_profiles_keep_their_previous_topic_scope(self):
        self.assertTrue(classify("#tights #fashion"))
        self.assertEqual(classify("Nylon layering"), [])
        self.assertEqual(classify("ASMR fabric scratching sounds", profile="textile-asmr"), ["asmr"])
        self.assertEqual(classify("ASMR fabric scratching sounds", profile="fashion-review"), [])

    def test_official_title_is_rechecked_and_colour_title_is_preserved(self):
        settings = config()
        settings["sources"][0].update(profile="fashion-review", language="en")
        title = "Layering Sheer Nude Stockings"
        catalog, state = collect(settings, [], {}, lambda url: feed(title=title) if "feeds/" in url else embed(title=title), store, NOW)
        self.assertEqual(state["added"], 1)
        self.assertEqual(catalog[0]["originalTitle"], title)
        self.assertEqual(catalog[0]["language"], "en")
        for replacement in ("#tights #fashion", "Nude model in stockings: styling"):
            with self.subTest(replacement=replacement):
                catalog, state = collect(settings, [], {}, lambda url: feed(title=title) if "feeds/" in url else embed(title=replacement), store, NOW)
                self.assertEqual(catalog, [])
                self.assertEqual(state["sources"][0]["rejected"], 1)

    def test_review_description_does_not_republish_channel_promotions(self):
        settings = config()
        settings["sources"][0]["profile"] = "fashion-review"
        title = "Tights review and styling"
        data = json.loads(embed(title=title))
        data["description"] = "Shop here https://shop.example/; use discount code PROMO25"
        catalog, _state = collect(settings, [], {}, lambda url: feed(title=title) if "feeds/" in url else json.dumps(data).encode(), store, NOW)
        self.assertEqual(len(catalog), 1)
        self.assertNotIn("https://", catalog[0]["description"])
        self.assertNotIn("PROMO25", catalog[0]["description"])
        self.assertIn(catalog[0]["author"], catalog[0]["description"])
        self.assertIn("originalTitle", catalog[0])

    def test_profile_is_valid_configuration(self):
        settings = config()
        settings["sources"][0]["profile"] = "fashion-review"
        validate_config(settings)


if __name__ == "__main__":
    unittest.main()
