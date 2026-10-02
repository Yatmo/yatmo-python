"""Typed models of the Yatmo API answers, built from the wire format with ``from_wire``."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence


class TravelMode(str, Enum):
    """The four travel modes; the value is what the API expects in ``travelMode``."""

    WALKING = "Walking"
    BICYCLING = "Bicycling"
    DRIVING = "Driving"
    TRANSIT = "Transit"

    @property
    def summary_code(self) -> int:
        """Code used inside the summary payload (``td[].tm``)."""
        return {TravelMode.DRIVING: 1, TravelMode.WALKING: 2, TravelMode.BICYCLING: 3, TravelMode.TRANSIT: 4}[self]

    @staticmethod
    def from_summary_code(code: int) -> Optional["TravelMode"]:
        return {1: TravelMode.DRIVING, 2: TravelMode.WALKING, 3: TravelMode.BICYCLING, 4: TravelMode.TRANSIT}.get(code)


class MapStyle(IntEnum):
    """The seven map styles of the web plugins and of the static map endpoint."""

    LIBERTY = 1
    BASIC = 2
    BRIGHT = 3
    THREE_D = 4
    POSITRON = 5
    DARK = 6
    LIBERTY_STONEHEDGE = 7


def _opt_int(value: Any) -> Optional[int]:
    return None if value is None else int(value)


@dataclass(frozen=True)
class TravelData:
    """Distance and travel time of one mode to a place."""

    has_travel_information: bool
    travel_mode: Optional[TravelMode]
    translated_travel_mode: Optional[str]
    distance_meters: Optional[int]
    distance_long_label: Optional[str]
    distance_short_label: Optional[str]
    travel_time_seconds: Optional[int]
    travel_time_long_label: Optional[str]
    travel_time_short_label: Optional[str]
    travel_time_extra_short_label: Optional[str]

    @staticmethod
    def from_wire(w: Mapping[str, Any]) -> "TravelData":
        return TravelData(
            bool(w.get("hti", False)), TravelMode.from_summary_code(int(w.get("tm", 0))), w.get("ttm"),
            _opt_int(w.get("ptdd")), w.get("ptdll"), w.get("ptdsl"),
            _opt_int(w.get("tt")), w.get("ttll"), w.get("ttsl"), w.get("ttesl"),
        )


@dataclass(frozen=True)
class SummaryPlace:
    """A place of the summary, with its travel data per mode."""

    category_id: int
    icon: int
    sub_icon: int
    latitude: float
    longitude: float
    name: str
    specific_data: Optional[str]
    travel_data: Sequence[TravelData]

    def travel(self, mode: TravelMode) -> Optional[TravelData]:
        """The travel data of a mode, when the API computed it."""
        for t in self.travel_data:
            if t.travel_mode is mode and t.has_travel_information:
                return t
        return None


@dataclass(frozen=True)
class SummarySubCategory:
    """A sub-category of the summary (nurseries, high schools, bus stops...)."""

    sub_type: int
    label: str
    singular_label: Optional[str]
    places: Sequence[SummaryPlace]


class SummaryCategory:
    """A category of the summary with its sub-categories."""

    EDUCATION = 1
    TRANSPORT = 2
    SHOPPING = 3
    TOURISM = 7

    def __init__(self, category_type: int, label: str, sub_categories: Sequence[SummarySubCategory]) -> None:
        self.category_type = category_type
        self.label = label
        self.sub_categories = sub_categories


@dataclass(frozen=True)
class CloseCity:
    names: Mapping[str, str]
    travel_data: Sequence[TravelData]
    latitude: Optional[float]
    longitude: Optional[float]


@dataclass(frozen=True)
class PlaceInformation:
    street_name: Optional[str]
    is_locality: bool
    city_name: Optional[str]
    zip_code: Optional[str]
    localized_street_names: Optional[Mapping[str, str]]
    localized_city_names: Optional[Mapping[str, str]]


@dataclass(frozen=True)
class Summary:
    """``/summary``: places by category with travel times, closest cities, reverse-geocoded place."""

    categories: Sequence[SummaryCategory]
    close_cities: Sequence[CloseCity]
    place_information: Optional[PlaceInformation]

    @staticmethod
    def from_wire(w: Mapping[str, Any]) -> "Summary":
        categories = []
        for c in w.get("AvailableCategoriesAroundPosition") or []:
            subs = []
            for s in c.get("sc") or []:
                places = [
                    SummaryPlace(
                        int(d.get("id", 0)), int(d.get("i", 0)), int(d.get("si", 0)), float(d["la"]), float(d["lo"]),
                        str(d.get("n", "")), d.get("sd"), [TravelData.from_wire(t) for t in d.get("td") or []],
                    )
                    for d in s.get("d") or []
                ]
                subs.append(SummarySubCategory(int(s.get("st", 0)), str(s.get("l", "")), s.get("lb"), places))
            categories.append(SummaryCategory(int(c.get("ct", 0)), str(c.get("l", "")), subs))
        cities = [
            CloseCity(
                c.get("n") or {}, [TravelData.from_wire(t) for t in c.get("td") or []],
                float(c["c"]["Latitude"]) if isinstance(c.get("c"), dict) and "Latitude" in c["c"] else None,
                float(c["c"]["Longitude"]) if isinstance(c.get("c"), dict) and "Longitude" in c["c"] else None,
            )
            for c in w.get("CloseCities") or []
        ]
        p = w.get("PlaceInformation")
        place = PlaceInformation(
            p.get("StreetName"), bool(p.get("IsLocality", False)), p.get("CityName"), p.get("ZipCode"),
            p.get("LocalizedStreetNames"), p.get("LocalizedCityNames"),
        ) if isinstance(p, dict) else None
        return Summary(categories, cities, place)

    def sub_categories(self, *category_types: int) -> Iterator[SummarySubCategory]:
        """The sub-categories of the given category types (``SummaryCategory`` constants), every type when empty."""
        for category in self.categories:
            if not category_types or category.category_type in category_types:
                yield from category.sub_categories


@dataclass(frozen=True)
class TextParagraph:
    """One paragraph of the neighbourhood text, in one language; sentences keep the ``[STRONG]`` markers."""

    icon_id: str
    title: str
    title_street: Optional[str]
    title_city: Optional[str]
    sentences: Sequence[str]
    items: Sequence[str]

    @property
    def text(self) -> str:
        return " ".join(self.sentences) + ("\n" + "\n".join("- " + i for i in self.items) if self.items else "")


def _pick_language(localized: Mapping[str, Any], language: str) -> Optional[str]:
    for candidate in (language, "EN"):
        if localized.get(candidate):
            return candidate
    return next(iter(localized), None)


@dataclass(frozen=True)
class SummaryText:
    """``/Summary/text`` resolved to one language."""

    language: str
    paragraphs: Sequence[TextParagraph]

    @staticmethod
    def from_wire(w: Mapping[str, Any], language: str) -> "SummaryText":
        """``w`` is the API answer (every language at once); the requested language, else EN, else the first one."""
        language = language.upper()
        used: Optional[str] = None
        paragraphs = []
        for p in w.get("Paragraphs") or []:
            lang = _pick_language(p.get("Title") or {}, language)
            if lang is None:
                continue
            used = used or lang
            sentences = [s[lang] for s in p.get("Sentences") or [] if isinstance(s, dict) and s.get(lang)]
            items = [s[lang] for s in p.get("List") or [] if isinstance(s, dict) and s.get(lang)]
            if not sentences and not items:
                continue
            paragraphs.append(TextParagraph(
                str(p.get("IconId", "")), str((p.get("Title") or {}).get(lang, "")),
                (p.get("TitleBis") or {}).get(lang), (p.get("TitleTer") or {}).get(lang), sentences, items,
            ))
        return SummaryText(used or language, paragraphs)

    @property
    def text(self) -> str:
        """Every paragraph's text, separated by blank lines, markers included."""
        return "\n\n".join(p.text for p in self.paragraphs)


@dataclass(frozen=True)
class Score:
    key: str
    label: str
    value: float
    icon_id: Optional[int]
    category_type: Optional[int]
    sub_types: Sequence[int]


@dataclass(frozen=True)
class Scores:
    """``/scores``: one 0 to 10 score per category."""

    scores: Sequence[Score]
    language: Optional[str]

    @staticmethod
    def from_wire(w: Mapping[str, Any]) -> "Scores":
        return Scores(
            [Score(str(s.get("k", "")), str(s.get("l", "")), float(s.get("v", 0)), _opt_int(s.get("iconId")), _opt_int(s.get("pt")), s.get("st") or []) for s in w.get("scores") or []],
            w.get("language"),
        )


@dataclass(frozen=True)
class Poi:
    """A point of interest of ``/points``."""

    name: str
    type: str
    latitude: float
    longitude: float
    category_id: str
    icon_ids: Sequence[str]
    sub_icon_ids: Sequence[str]
    grouped: bool
    specific_data: Optional[str]

    @staticmethod
    def from_wire(w: Mapping[str, Any]) -> "Poi":
        split = lambda v: [x for x in str(v or "").split(",") if x]  # noqa: E731
        return Poi(str(w["n"]), str(w.get("t", "")), float(w["la"]), float(w["ln"]), str(w.get("p", "")), split(w.get("i")), split(w.get("si")), bool(w.get("g", False)), w.get("sd"))


@dataclass(frozen=True)
class Place:
    """A geocoded place."""

    name: Optional[str]
    street: Optional[str]
    house_number: Optional[str]
    postcode: Optional[str]
    city: Optional[str]
    country: Optional[str]
    country_code: Optional[str]
    type: Optional[str]
    latitude: float
    longitude: float
    label: str

    @staticmethod
    def from_feature(f: Mapping[str, Any]) -> Optional["Place"]:
        coordinates = (f.get("geometry") or {}).get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            return None
        p = f.get("properties") or {}
        street_line = " ".join(x for x in [p.get("street") or p.get("name"), p.get("housenumber")] if x)
        city_line = " ".join(x for x in [p.get("postcode"), p.get("city")] if x)
        return Place(
            p.get("name"), p.get("street"), p.get("housenumber"), p.get("postcode"), p.get("city"), p.get("country"),
            p.get("countrycode"), p.get("type"), float(coordinates[1]), float(coordinates[0]),
            ", ".join(x for x in [street_line, city_line] if x),
        )


@dataclass(frozen=True)
class RoutePath:
    distance_meters: float
    duration_seconds: int
    geometry: Mapping[str, Any]
    instructions: Optional[List[Any]]


@dataclass(frozen=True)
class Route:
    """``/route``: GraphHopper-style paths."""

    paths: Sequence[RoutePath]
    info: Any = None

    @staticmethod
    def from_wire(w: Mapping[str, Any]) -> "Route":
        return Route(
            [RoutePath(float(p.get("distance", 0)), int(round(int(p.get("time", 0)) / 1000)), p.get("points") or {"type": "LineString", "coordinates": []}, p.get("instructions")) for p in w.get("paths") or []],
            w.get("info"),
        )


@dataclass(frozen=True)
class Isochrone:
    label: str
    geometry: Any


@dataclass(frozen=True)
class CategoryGroup:
    name: str
    poi_type_ids: Sequence[int] = field(default_factory=list)


Wire = Dict[str, Any]
