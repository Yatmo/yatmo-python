"""A property page in plain Python: the neighbourhood text and the nearest places, as HTML.

    YATMO_KEY=your_backend_key python examples/property_page.py > listing.html
"""

import html
import os
import sys

from yatmo import Client, SummaryCategory, TravelMode, render_html

key = os.environ.get("YATMO_KEY")
if not key:
    sys.exit("set YATMO_KEY to your backend key")

yatmo = Client(key, "BE", "FR")
lat, lng = 50.8461, 4.3664

summary = yatmo.summary(lat, lng)
places = []
for sub in summary.sub_categories(SummaryCategory.EDUCATION, SummaryCategory.TRANSPORT, SummaryCategory.SHOPPING):
    if not sub.places:
        continue
    place = sub.places[0]
    walk = place.travel(TravelMode.WALKING)
    detail = f" ({walk.distance_short_label}, {walk.travel_time_short_label})" if walk else ""
    places.append(f"<li><strong>{html.escape(sub.singular_label or sub.label)}</strong>: {html.escape(place.name)}{html.escape(detail)}</li>")

text = yatmo.summary_text(lat, lng)

print(f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Appartement, Rue de la Loi</title></head>
<body>
<h1>Appartement 2 chambres, Rue de la Loi</h1>
<iframe src="https://map.yatmo.com/plugin.html?licenseKey=YOUR_FRONTEND_KEY&country=BE&language=FR&latitude={lat}&longitude={lng}&marker=circle&isochrone=right"
        style="width:100%;height:520px;border:0" loading="lazy" title="Carte du quartier"></iframe>
<h2>Autour du bien</h2>
<ul>{''.join(places)}</ul>
<h2>Vivre ici</h2>
{render_html(text, titles="city")}
</body></html>""")
