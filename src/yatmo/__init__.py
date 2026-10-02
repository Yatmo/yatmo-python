"""Real estate maps, points of interest and neighbourhood data: the Python client for the Yatmo API.

    from yatmo import Client, render_html

    yatmo = Client(key="your_backend_key", country="BE", language="FR")
    text = yatmo.summary_text(50.8461, 4.3664)   # the neighbourhood text, every paragraph
    html = render_html(text)                      # headings and paragraphs for a property page
    summary = yatmo.summary(50.8461, 4.3664)      # nearest places by category with travel times

Documentation: https://documentation.yatmo.com/api
"""

from .client import VERSION, Client
from .exceptions import (
    AuthenticationError,
    BadRequestError,
    ForbiddenError,
    QuotaError,
    TransportError,
    YatmoError,
)
from .models import (
    CategoryGroup,
    CloseCity,
    Isochrone,
    MapStyle,
    Place,
    PlaceInformation,
    Poi,
    Route,
    RoutePath,
    Score,
    Scores,
    Summary,
    SummaryCategory,
    SummaryPlace,
    SummarySubCategory,
    SummaryText,
    TextParagraph,
    TravelData,
    TravelMode,
)
from .text import render_html, render_markdown, render_plain, sentence_to_html, strip_markers
from .transport import Transport, UrllibTransport

__all__ = [
    "VERSION", "Client",
    "YatmoError", "BadRequestError", "AuthenticationError", "ForbiddenError", "QuotaError", "TransportError",
    "TravelMode", "MapStyle", "TravelData", "SummaryPlace", "SummarySubCategory", "SummaryCategory", "CloseCity",
    "PlaceInformation", "Summary", "TextParagraph", "SummaryText", "Score", "Scores", "Poi", "Place", "RoutePath",
    "Route", "Isochrone", "CategoryGroup",
    "render_html", "render_markdown", "render_plain", "sentence_to_html", "strip_markers",
    "Transport", "UrllibTransport",
]
