"""The Yatmo API client: one instance per country, every endpoint as a method, typed answers."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union
from urllib.parse import quote, urlencode

from .exceptions import TransportError, YatmoError
from .models import CategoryGroup, Isochrone, MapStyle, Place, Poi, Route, Scores, Summary, SummaryText, TravelMode
from .transport import Transport, UrllibTransport

VERSION = "1.0.0"


class Client:
    """
    ``Client(key, country, language="EN")``: ``key`` is your BACKEND key (server to server), ``country`` the
    two-letter code of your properties (the API host is ``https://<country>.yatmo.com/``), ``language`` the
    language of labels and texts. Pass a ``transport`` to use requests or httpx, ``api_base_url`` for a proxy.
    """

    def __init__(self, key: str, country: str, language: str = "EN", transport: Optional[Transport] = None, timeout_seconds: float = 15, api_base_url: Optional[str] = None) -> None:
        if not key:
            raise YatmoError(401, "Yatmo: the key is required")
        if not re.fullmatch(r"[A-Za-z]{2}", country or ""):
            raise YatmoError(400, "Yatmo: the country must be a two-letter code")
        self._key = key
        self._country = country.upper()
        self._language = (language or "EN").upper()
        self._transport = transport or UrllibTransport()
        self._timeout = timeout_seconds
        self._base_url = (api_base_url or f"https://{country.lower()}.yatmo.com/").rstrip("/") + "/"

    @property
    def country(self) -> str:
        return self._country

    @property
    def language(self) -> str:
        return self._language

    # ------------------------------------------------------------------ endpoints

    def summary(self, latitude: float, longitude: float) -> Summary:
        """``GET /summary``: nearby places by category with travel times, closest cities, resolved address."""
        return Summary.from_wire(self.summary_raw(latitude, longitude))

    def summary_raw(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """``GET /summary`` as sent by the API (short keys), a plain dict any cache stores."""
        return self._get_json("summary", self._position(latitude, longitude))

    def summary_text_raw(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """``GET /Summary/text`` as sent by the API: every language of the country. Cache it, a location rarely changes."""
        return self._get_json("Summary/text", self._position(latitude, longitude))

    def summary_text(self, latitude: float, longitude: float, language: Optional[str] = None) -> SummaryText:
        """``GET /Summary/text`` resolved to the configured language (or ``language``), markers kept. See ``render_html``."""
        return SummaryText.from_wire(self.summary_text_raw(latitude, longitude), language or self._language)

    def scores(self, latitude: float, longitude: float) -> Scores:
        """``GET /scores``: one 0 to 10 score per category."""
        return Scores.from_wire(self.scores_raw(latitude, longitude))

    def scores_raw(self, latitude: float, longitude: float) -> Dict[str, Any]:
        return self._get_json("scores", self._position(latitude, longitude))

    def enrichment(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """``GET /enrichment``: the nearest place of each category with distances and times for four modes, for listing data."""
        return self._get_json("enrichment", self._position(latitude, longitude))

    def points(self, south_latitude: float, west_longitude: float, north_latitude: float, east_longitude: float, poi_type_ids: Sequence[int] = ()) -> List[Poi]:
        """``GET /points``: the points of interest inside a bounding box, optionally of some types only."""
        query: Dict[str, str] = {
            "bound1": f"{self._coordinate(south_latitude)},{self._coordinate(west_longitude)}",
            "bound2": f"{self._coordinate(north_latitude)},{self._coordinate(east_longitude)}",
            "groupSamePositions": "true",
            "caringForBigResponse": "true",
        }
        if poi_type_ids:
            query["poiTypesIds"] = ",".join(str(i) for i in poi_type_ids)
        return [Poi.from_wire(w) for w in self._get_json("points", query)]

    def simplified_categories(self) -> List[CategoryGroup]:
        """``GET /SimplifiedCategories``: the category groups and their POI type ids, sorted by name."""
        groups = [CategoryGroup(str(name), [int(i) for i in ids]) for name, ids in self._get_json("SimplifiedCategories", {}).items()]
        return sorted(groups, key=lambda g: g.name)

    def isochrones(self, latitude: float, longitude: float, mode: TravelMode) -> List[Isochrone]:
        """``GET /Isochrone/GetMultipleTimes``: the 5, 10 and 20 minute areas of a mode, as GeoJSON geometries."""
        wire = self._get_json("Isochrone/GetMultipleTimes", {**self._position(latitude, longitude), "travelMode": mode.value})
        return [Isochrone(str(item.get("label", "")), item.get("iso")) for item in wire]

    def isochrone(self, latitude: float, longitude: float, mode: TravelMode, seconds: int) -> Any:
        """``GET /isochrone``: the area reachable in ``seconds`` with a mode, as a GeoJSON geometry."""
        wire = self._get_json("isochrone", {**self._position(latitude, longitude), "travelMode": mode.value, "numberOfSeconds": str(seconds)})
        return wire.get("geometry", wire) if isinstance(wire, dict) else wire

    def route(self, from_latitude: float, from_longitude: float, to_latitude: float, to_longitude: float, mode: TravelMode) -> Route:
        """``GET /route``: the route between two points with a mode."""
        return Route.from_wire(self._get_json("route", {
            "travelMode": mode.value,
            "startLatitude": self._coordinate(from_latitude), "startLongitude": self._coordinate(from_longitude),
            "arrivalLatitude": self._coordinate(to_latitude), "arrivalLongitude": self._coordinate(to_longitude),
        }))

    def geocode(self, address: str) -> List[Place]:
        """``GET /geolocation``: an address to coordinates, inside the country. Best match first."""
        return self._places(self._get_json("geolocation", {"address": address.strip()}))

    def geocode_near(self, latitude: float, longitude: float, query: str) -> List[Place]:
        """``GET /Geolocation/GetClose``: address autocomplete near a position."""
        return self._places(self._get_json("Geolocation/GetClose", {**self._position(latitude, longitude), "address": query.strip()}))

    def static_map(self, latitude: float, longitude: float, **options: Any) -> bytes:
        """``GET /image``: a JPEG of the map around the property. Options: see ``static_map_url``."""
        return self._request(self.static_map_url(latitude, longitude, **options), "image/jpeg")

    def static_map_url(self, latitude: float, longitude: float, color: str = "#428BFF", width: int = 800, height: int = 450, map_style: Optional[Union[MapStyle, int]] = None, three_d: bool = False, big_icons: bool = False, multi_borders: bool = False, custom_marker: Optional[Mapping[str, Any]] = None) -> str:
        """The URL of the static map (the key is in the query: use it server side, or with the frontend key)."""
        query: Dict[str, str] = {**self._position(latitude, longitude), "hexaColor": color.lstrip("#"), "width": str(width), "height": str(height)}
        if map_style is not None:
            query["mapStyle"] = str(int(map_style))
        if three_d:
            query["threeDMode"] = "true"
        if big_icons:
            query["bigIcon"] = "true"
        if multi_borders:
            query["multiborders"] = "true"
        if custom_marker:
            query["customMarkerUrl"] = str(custom_marker["url"])
            query["customMarkerWidth"] = str(custom_marker["width"])
            query["customMarkerHeight"] = str(custom_marker["height"])
        return self.url("image", query)

    # ------------------------------------------------------------------ plumbing

    def headers(self, accept: str = "application/json") -> Dict[str, str]:
        return {"LicenseKey": self._key, "X-Yatmo-SDK": f"yatmo-python/{VERSION}", "Accept": accept}

    def url(self, path: str, query: Optional[Mapping[str, str]] = None) -> str:
        """The full URL of an endpoint with its query and the language."""
        params = {**(query or {}), "language": self._language}
        return self._base_url + path + "?" + urlencode(params, quote_via=quote, safe="")

    def _request(self, url: str, accept: str) -> bytes:
        try:
            status, body = self._transport.get(url, self.headers(accept), self._timeout)
        except YatmoError:
            raise
        except Exception as error:  # noqa: BLE001 (any transport failure)
            raise TransportError(0, f"Yatmo API unreachable: {error}") from error
        if status < 200 or status >= 300:
            message: str = body.decode("utf-8", "replace")
            try:
                decoded = json.loads(message)
                if isinstance(decoded, dict) and "Error" in decoded:
                    message = str(decoded["Error"])
            except ValueError:
                pass
            raise YatmoError.from_status(status, f"Yatmo API {status}: {message}")
        return body

    def _get_json(self, path: str, query: Mapping[str, str]) -> Any:
        body = self._request(self.url(path, query), "application/json")
        try:
            decoded = json.loads(body.decode("utf-8"))
        except ValueError as error:
            raise TransportError(0, "Yatmo API: unreadable response") from error
        if not isinstance(decoded, (dict, list)):
            raise TransportError(0, "Yatmo API: unreadable response")
        return decoded

    @staticmethod
    def _places(root: Any) -> List[Place]:
        features = root.get("features") if isinstance(root, dict) else root
        places = [Place.from_feature(f) for f in features or [] if isinstance(f, dict)]
        return [p for p in places if p is not None]

    @staticmethod
    def _coordinate(value: float) -> str:
        return f"{float(value):.7f}"

    def _position(self, latitude: float, longitude: float) -> Dict[str, str]:
        return {"latitude": self._coordinate(latitude), "longitude": self._coordinate(longitude)}
