"""One real call per endpoint, with the key of YATMO_LIVE_KEY; skipped without it.

    YATMO_LIVE_KEY=your_backend_key python -m unittest tests.test_live
"""

import os
import unittest

from yatmo import Client, TravelMode, render_html

KEY = os.environ.get("YATMO_LIVE_KEY", "")


@unittest.skipUnless(KEY, "YATMO_LIVE_KEY is not set")
class LiveTests(unittest.TestCase):
    def setUp(self):
        self.client = Client(KEY, "BE", "FR")

    def test_brussels(self):
        lat, lng = 50.8461, 4.3664
        summary = self.client.summary(lat, lng)
        self.assertTrue(summary.categories)
        nursery = next(self.client.summary(lat, lng).sub_categories(1)).places[0]
        self.assertIsNotNone(nursery.travel(TravelMode.WALKING))
        text = self.client.summary_text(lat, lng)
        self.assertEqual(text.language, "FR")
        self.assertGreater(len(text.paragraphs), 3)
        html = render_html(text)
        self.assertIn("<strong>", html)
        self.assertTrue(self.client.scores(lat, lng).scores)
        self.assertEqual(self.client.geocode("Rue de la Loi 16, 1000 Bruxelles")[0].postcode, "1000")
        self.assertTrue(self.client.isochrones(lat, lng, TravelMode.WALKING))
        self.assertTrue(self.client.route(lat, lng, 50.8503, 4.3517, TravelMode.WALKING).paths)
        self.assertEqual(self.client.static_map(lat, lng, width=300, height=200)[:2], b"\xff\xd8")
        print("\n" + render_html(text, paragraphs=["shopping"])[:300])


if __name__ == "__main__":
    unittest.main()
