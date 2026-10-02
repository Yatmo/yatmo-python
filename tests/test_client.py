"""Hermetic tests: the transport is faked, the API is never called."""

import json
import unittest

from yatmo import (
    AuthenticationError,
    BadRequestError,
    Client,
    ForbiddenError,
    QuotaError,
    SummaryCategory,
    TransportError,
    TravelMode,
    YatmoError,
    render_html,
    render_markdown,
    render_plain,
)

SUMMARY = {
    "AvailableCategoriesAroundPosition": [
        {"ct": 1, "l": "Education", "sc": [{"st": 4, "l": "Nurseries", "lb": "Nursery", "d": [{"n": "Little Bears", "la": 50.84, "lo": 4.36, "td": [{"hti": True, "tm": 2, "ptdsl": "300 m", "ttsl": "4'"}]}]}]},
        {"ct": 3, "l": "Shopping", "sc": [{"st": 9, "l": "Supermarkets", "lb": "Supermarket", "d": [{"n": "Carrefour", "la": 50.84, "lo": 4.36, "td": []}]}]},
    ],
    "CloseCities": [{"n": {"FR": "Malines", "NL": "Mechelen"}, "td": [], "c": {"Latitude": 51.02, "Longitude": 4.48}}],
    "PlaceInformation": {"StreetName": "Rue de la Loi", "IsLocality": False, "CityName": "Bruxelles", "ZipCode": "1000"},
}
TEXT = {"Paragraphs": [
    {"IconId": "shopping", "Title": {"FR": "Commerces", "EN": "Shops"}, "TitleBis": {"FR": "Commerces près de la Rue de la Loi"}, "TitleTer": {"FR": "Commerces à Bruxelles"},
     "Sentences": [{"FR": "Un [STRONG]Carrefour[/STRONG] à 3 minutes.", "EN": "A [STRONG]Carrefour[/STRONG] 3 minutes away."}], "List": []},
    {"IconId": "education", "Title": {"FR": "Écoles", "EN": "Schools"}, "TitleTer": {"FR": "Écoles à Bruxelles"}, "Sentences": [{"FR": "Deux écoles <b>& plus</b>."}], "List": [{"FR": "Athénée"}]},
    {"IconId": "cities", "Title": {"FR": "Villes"}, "Sentences": [], "List": []},
]}


class FakeTransport:
    """Canned answers keyed by a substring of the URL; records every call. 404 otherwise."""

    def __init__(self, answers=None):
        self.answers = answers or {}
        self.calls = []

    def get(self, url, headers, timeout_seconds):
        self.calls.append((url, dict(headers)))
        for needle, (status, body) in self.answers.items():
            if needle in url:
                if isinstance(body, bytes):
                    return status, body
                return status, (body if isinstance(body, str) else json.dumps(body)).encode("utf-8")
        return 404, b'{"Error":"no canned answer"}'


def client(answers=None, **kwargs):
    transport = FakeTransport(answers)
    return Client("abc123", "BE", "FR", transport=transport, **kwargs), transport


class ClientTests(unittest.TestCase):
    def test_constructor_validation(self):
        with self.assertRaises(YatmoError):
            Client("", "BE")
        with self.assertRaises(YatmoError):
            Client("k", "Belgium")
        self.assertEqual(Client("k", "fr", "nl").url("summary"), "https://fr.yatmo.com/summary?language=NL")
        self.assertEqual(Client("k", "BE", api_base_url="http://localhost:5000/").url("summary"), "http://localhost:5000/summary?language=EN")

    def test_summary_url_headers_and_models(self):
        c, t = client({"/summary?": (200, SUMMARY)})
        summary = c.summary(50.8461, 4.3664)
        self.assertEqual(t.calls[0][0], "https://be.yatmo.com/summary?latitude=50.8461000&longitude=4.3664000&language=FR")
        self.assertEqual(t.calls[0][1]["LicenseKey"], "abc123")
        self.assertTrue(t.calls[0][1]["X-Yatmo-SDK"].startswith("yatmo-python/"))
        self.assertEqual(len(summary.categories), 2)
        self.assertEqual(summary.place_information.street_name, "Rue de la Loi")
        self.assertEqual(summary.close_cities[0].names["FR"], "Malines")
        nursery = summary.categories[0].sub_categories[0].places[0]
        self.assertEqual(nursery.travel(TravelMode.WALKING).travel_time_short_label, "4'")
        self.assertIsNone(nursery.travel(TravelMode.DRIVING))
        self.assertEqual([s.label for s in summary.sub_categories(SummaryCategory.SHOPPING)], ["Supermarkets"])

    def test_errors_are_typed(self):
        for status, cls in [(400, BadRequestError), (401, AuthenticationError), (403, ForbiddenError), (429, QuotaError), (500, YatmoError)]:
            c, _ = client({"/summary?": (status, {"Error": "nope"})})
            with self.assertRaises(cls) as caught:
                c.summary(50.8, 4.3)
            self.assertEqual(caught.exception.status, status)
            self.assertIn("nope", str(caught.exception))
        c, _ = client({"/summary?": (200, b"not json")})
        with self.assertRaises(TransportError):
            c.summary(50.8, 4.3)

        class Broken:
            def get(self, url, headers, timeout_seconds):
                raise OSError("down")

        with self.assertRaises(TransportError) as caught:
            Client("k", "BE", transport=Broken()).summary(50.8, 4.3)
        self.assertEqual(caught.exception.status, 0)

    def test_summary_text_resolves_language_and_renders(self):
        c, t = client({"/Summary/text?": (200, TEXT)})
        text = c.summary_text(50.8461, 4.3664)
        self.assertEqual(text.language, "FR")
        self.assertEqual([p.icon_id for p in text.paragraphs], ["shopping", "education"])
        self.assertEqual(
            render_html(text),
            '<div class="yatmo-text"><h3>Commerces près de la Rue de la Loi</h3><p>Un <strong>Carrefour</strong> à 3 minutes.</p>'
            "<h3>Écoles à Bruxelles</h3><p>Deux écoles &lt;b&gt;&amp; plus&lt;/b&gt;.</p><ul><li>Athénée</li></ul></div>",
        )
        self.assertEqual(render_html(text, heading="h2", titles="city", paragraphs=["education"], css_class="mine"), '<div class="yatmo-text mine"><h2>Écoles à Bruxelles</h2><p>Deux écoles &lt;b&gt;&amp; plus&lt;/b&gt;.</p><ul><li>Athénée</li></ul></div>', "first paragraph in city mode names the city")
        self.assertEqual(render_markdown(text, paragraphs=["shopping"]), "### Commerces près de la Rue de la Loi\n\nUn **Carrefour** à 3 minutes.")
        self.assertEqual(render_plain(text, titles="generic", paragraphs=["shopping"]), "Commerces\nUn Carrefour à 3 minutes.")
        english = c.summary_text(50.8461, 4.3664, "EN")
        self.assertEqual(english.paragraphs[0].title, "Shops")
        self.assertEqual(len(english.paragraphs), 1, "a paragraph without sentences in the picked language is dropped")

    def test_other_endpoints(self):
        c, t = client({
            "/scores?": (200, {"scores": [{"k": "education", "l": "Éducation", "v": 7.5, "pt": 1, "st": [4, 5]}], "language": "FR"}),
            "/points?": (200, [{"n": "Carrefour", "t": "Supermarket", "la": 50.84, "ln": 4.36, "p": "3", "i": "9,10", "si": "", "g": False}]),
            "/SimplifiedCategories?": (200, {"Shopping": [9, 10], "Education": [4, 5]}),
            "/Isochrone/GetMultipleTimes?": (200, [{"label": "5 min", "iso": {"type": "Polygon", "coordinates": []}}]),
            "/isochrone?": (200, {"geometry": {"type": "Polygon", "coordinates": []}}),
            "/route?": (200, {"paths": [{"distance": 1234.5, "time": 600499, "points": {"type": "LineString", "coordinates": [[4.36, 50.84]]}}], "info": {"took": 3}}),
            "/geolocation?": (200, {"features": [{"geometry": {"coordinates": [4.3664, 50.8461]}, "properties": {"street": "Rue de la Loi", "housenumber": "16", "postcode": "1000", "city": "Bruxelles", "countrycode": "BE"}}]}),
            "/Geolocation/GetClose?": (200, {"features": []}),
            "/enrichment?": (200, {"nearestSchool": {"name": "Athénée"}}),
            "/image?": (200, b"\xff\xd8jpeg"),
        })
        scores = c.scores(50.8, 4.3)
        self.assertEqual((scores.scores[0].key, scores.scores[0].value, scores.scores[0].sub_types), ("education", 7.5, [4, 5]))
        pois = c.points(50.8, 4.3, 50.9, 4.4, [9, 10])
        self.assertIn("bound1=50.8000000%2C4.3000000&bound2=50.9000000%2C4.4000000", t.calls[-1][0])
        self.assertIn("poiTypesIds=9%2C10", t.calls[-1][0])
        self.assertEqual((pois[0].name, pois[0].icon_ids), ("Carrefour", ["9", "10"]))
        self.assertEqual([g.name for g in c.simplified_categories()], ["Education", "Shopping"])
        self.assertEqual(c.isochrones(50.8, 4.3, TravelMode.BICYCLING)[0].label, "5 min")
        self.assertIn("travelMode=Bicycling", t.calls[-1][0])
        self.assertEqual(c.isochrone(50.8, 4.3, TravelMode.WALKING, 900)["type"], "Polygon")
        self.assertIn("numberOfSeconds=900", t.calls[-1][0])
        route = c.route(50.8, 4.3, 50.9, 4.4, TravelMode.DRIVING)
        self.assertEqual((route.paths[0].distance_meters, route.paths[0].duration_seconds, route.info), (1234.5, 600, {"took": 3}))
        place = c.geocode(" Rue de la Loi 16 ")[0]
        self.assertEqual((place.latitude, place.longitude, place.label), (50.8461, 4.3664, "Rue de la Loi 16, 1000 Bruxelles"))
        self.assertIn("address=Rue%20de%20la%20Loi%2016", t.calls[-1][0])
        self.assertEqual(c.geocode_near(50.8, 4.3, "Loi"), [])
        self.assertEqual(c.enrichment(50.8, 4.3)["nearestSchool"]["name"], "Athénée")
        self.assertEqual(c.static_map(50.8, 4.3, width=600, map_style=6, three_d=True)[:2], b"\xff\xd8")
        self.assertIn("hexaColor=428BFF&width=600&height=450&mapStyle=6&threeDMode=true", t.calls[-1][0])
        self.assertEqual(t.calls[-1][1]["Accept"], "image/jpeg")


if __name__ == "__main__":
    unittest.main()
