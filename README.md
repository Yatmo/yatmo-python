# yatmo

Add real estate maps, points of interest and neighbourhood data to Python applications.
`yatmo` is the official Python client for the [Yatmo](https://yatmo.com) API: the written neighbourhood text of
a property (rendered as HTML on the server, so search engines index it), the nearest schools, nurseries,
supermarkets and public transport with real travel times, scores, listing enrichment, isochrones, routes,
geocoding and static map images, in 25 countries and 23 languages. Works with Django, Flask, FastAPI, notebooks
and scripts, Python 3.9 and later, no dependency.

```bash
pip install yatmo
```

```python
from yatmo import Client, TravelMode, render_html

yatmo = Client(key="your_backend_key", country="BE", language="FR")

# The neighbourhood text as HTML, to write into the property page.
text = yatmo.summary_text(50.8461, 4.3664)
print(render_html(text))
# <div class="yatmo-text"><h3>Commerces près de la Rue de la Loi</h3><p>Un <strong>Carrefour</strong> à 3 minutes...

# The nearest places by category with walking times.
summary = yatmo.summary(50.8461, 4.3664)
for sub in summary.sub_categories():
    place = sub.places[0] if sub.places else None
    walk = place.travel(TravelMode.WALKING) if place else None
    print(sub.label, ":", place.name if place else "-", walk.travel_time_short_label if walk else "")
```

<p align="center">
  <img src="https://raw.githubusercontent.com/Yatmo/.github/main/profile/img/neighbourhood-text.png" width="720" alt="The Yatmo neighbourhood text on a property page">
</p>

## Install in 5 minutes

1. Get a Yatmo licence key at [yatmo.com](https://yatmo.com) and use the **backend** key on the server
   ([keys explained](https://documentation.yatmo.com/license)).
2. `pip install yatmo`.
3. Create one `Client` per country, call `summary_text()` and `summary()` for each property, cache the answers
   (a neighbourhood rarely changes; `summary_text_raw()` and `summary_raw()` return plain dicts for that) and
   write the HTML into the page.

Runnable example: [examples/property_page.py](examples/property_page.py). The interactive map itself is an iframe
with your frontend key, no Python needed: [iframe plugin](https://documentation.yatmo.com/plugins/iframe).

## Client

```python
yatmo = Client(
    key="your_backend_key",
    country="BE",                 # the API host is https://be.yatmo.com/
    language="FR",                # labels and texts, default EN
    transport=None,               # optional: any object with get(url, headers, timeout_seconds) -> (status, body)
    timeout_seconds=15,
)
```

| Method | Endpoint | Returns |
|---|---|---|
| `summary(lat, lng)` | `/summary` | `Summary`: places by category with distances and travel times (walking, bicycling, driving, transit), closest cities, reverse-geocoded place |
| `summary_text(lat, lng, language=None)` | `/Summary/text` | `SummaryText` in one language, paragraphs with `[STRONG]` markers; see the renderers |
| `summary_text_raw(lat, lng)`, `summary_raw(lat, lng)`, `scores_raw(lat, lng)` | | The API answers as plain dicts, to cache; rebuild with `SummaryText.from_wire(raw, language)`, `Summary.from_wire(raw)`, `Scores.from_wire(raw)` |
| `scores(lat, lng)` | `/scores` | `Scores`: one 0 to 10 score per category |
| `enrichment(lat, lng)` | `/enrichment` | Ready-made listing attributes (nearest place per category, four travel modes), as a dict |
| `points(south, west, north, east, poi_type_ids=())` | `/points` | `Poi` list inside a bounding box |
| `simplified_categories()` | `/SimplifiedCategories` | `CategoryGroup` list (name, POI type ids) |
| `isochrones(lat, lng, mode)` | `/Isochrone/GetMultipleTimes` | 5, 10 and 20 minute areas, GeoJSON geometries |
| `isochrone(lat, lng, mode, seconds)` | `/isochrone` | One area, GeoJSON geometry |
| `route(from_lat, from_lng, to_lat, to_lng, mode)` | `/route` | `Route` with paths (distance, duration, LineString) |
| `geocode(address)` | `/geolocation` | `Place` list, best match first |
| `geocode_near(lat, lng, query)` | `/Geolocation/GetClose` | Address autocomplete around a point |
| `static_map(lat, lng, **options)` | `/image` | JPEG bytes; `static_map_url()` gives the URL (`color`, `width`, `height`, `map_style`, `three_d`, `big_icons`, `multi_borders`, `custom_marker`) |

Errors are typed: `BadRequestError` (400, position outside the country), `AuthenticationError` (401),
`ForbiddenError` (403, country or endpoint not in the licence), `QuotaError` (429), `TransportError`
(unreachable), all subclasses of `YatmoError` with a `status`.

## Rendering the text

```python
render_html(text, heading="h3", titles="street-city", paragraphs=None, strong=True, css_class="")
render_markdown(text, titles="street-city", paragraphs=None, strong=True)
render_plain(text, titles="street-city", paragraphs=None)
```

`titles`: the first heading names the street and the second the city (`"street-city"`), the city only
(`"city"`, for discreet listings) or neither (`"generic"`). `paragraphs` keeps some icon ids only among
`education`, `shopping`, `publictransports`, `transports`, `tourism`, `cities`.

## Django, Flask, FastAPI

```python
# Django view
from django.core.cache import cache

def listing(request, pk):
    listing = Listing.objects.get(pk=pk)
    key = f"yatmo-text-{listing.latitude:.6f}-{listing.longitude:.6f}"
    raw = cache.get(key)
    if raw is None:
        raw = yatmo.summary_text_raw(listing.latitude, listing.longitude)
        cache.set(key, raw, 30 * 86400)
    neighbourhood = render_html(SummaryText.from_wire(raw, request.LANGUAGE_CODE))
    return render(request, "listing.html", {"listing": listing, "neighbourhood": neighbourhood})
```

In the template: `{{ neighbourhood|safe }}` below the map iframe.

## Tests

```bash
python -m unittest discover tests                       # hermetic, the API is faked
YATMO_LIVE_KEY=your_backend_key python -m unittest tests.test_live   # one real call per endpoint
```

## Links

- [Yatmo](https://yatmo.com) and its [documentation](https://documentation.yatmo.com/api)
- Same client for other stacks: [JavaScript](https://www.npmjs.com/package/@yatmo/sdk), [PHP](https://packagist.org/packages/yatmo/yatmo-php), [.NET](https://www.nuget.org/packages/Yatmo.Client)
- [WordPress plugin](https://wordpress.org/plugins/yatmo-map/), [Odoo module](https://apps.odoo.com/apps/modules/20.0/yatmo_map), [Drupal module](https://www.drupal.org/project/yatmo_map), [MCP server for AI assistants](https://github.com/Yatmo/yatmo-mcp)
- [More examples](https://github.com/Yatmo/yatmo-examples)

MIT licence. Yatmo is a paid service for real estate portals, agency networks and developers; a licence key is required.
