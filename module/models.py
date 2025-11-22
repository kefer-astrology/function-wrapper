# Model defintions, data structures

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum


# ─── ENUMS ───

class ChartMode(str, Enum):
    NATAL = "NATAL"
    EVENT = "EVENT"
    HORARY = "HORARY"
    COMPOSITE = "COMPOSITE"
    #PROGRESSED = "PROGRESSED"
    #SYNASTRY = "SYNASTRY"
    #TRANSIT = "TRANSIT"


class HouseSystem(str, Enum):
    PLACIDUS = "Placidus"
    WHOLE_SIGN = "Whole Sign"
    CAMPANUS = "Campanus"
    KOCH = "Koch"
    EQUAL = "Equal"
    REGIOMONTANUS = "Regiomontanus"
    VEHL = "Vehlow"
    PORPHYRY = "Porphyry"
    ALCABITIUS = "Alcabitius"


class ZodiacType(str, Enum):
    TROPICAL = "Tropical"
    SIDEREAL = "Sidereal"


class EngineType(str, Enum):
    SWISSEPH = "swisseph"
    JYOTISH = "jyotish"
    JPL = "jpl"
    CUSTOM = "custom"


class Ayanamsa(str, Enum):
    LAHIRI = "Lahiri"
    RAMAN = "Raman"
    KRISHNAMURTI = "Krishnamurti"
    FAGAN_BRADLEY = "FaganBradley"
    DE_LUCE = "DeLuce"
    USER_DEFINED = "UserDefined"


class ObjectType(str, Enum):
    """Type of observable object in the chart."""
    PLANET = "planet"
    ASTEROID = "asteroid"
    ANGLE = "angle"  # MC, IC, Asc, Desc
    HOUSE_CUSP = "house_cusp"  # House cusps 1-12
    CALCULATED_POINT = "calculated_point"  # Lilith, Chiron, etc.
    LUNAR_NODE = "lunar_node"  # North/South Node
    PART = "part"  # Arabic Parts, etc.


class ViewModuleType(str, Enum):
    WHEEL = "WheelView"
    TIMELINE = "TransitTimeline"
    GRID = "AspectGrid"
    TABLE = "SummaryTable"
    TEXT = "InterpretationText"


class RelationType(str, Enum):
    TRANSIT = "transit"
    SYNASTRY = "synastry"
    PROGRESSION = "progression"
    COMPOSITE = "composite"


class LayoutStyle(str, Enum):
    SINGLE = "single"
    TIMELINE_OVERLAY = "timeline-overlay"
    DUAL_WHEEL = "dual-wheel"
    COMPARISON = "comparison"


class AspectContext(str, Enum):
    """Contexts where an aspect can be used."""
    CHART = "chart"  # Radix/natal charts
    TRANSIT = "transit"  # Transits
    DIRECTION = "direction"  # Directions/progressions
    # Aspects can be used in multiple contexts (e.g., conjunction works in all)


class Element(str, Enum):
    """The four classical elements."""
    FIRE = "Fire"
    EARTH = "Earth"
    AIR = "Air"
    WATER = "Water"


class TimeSystem(str, Enum):
    """Time representation systems."""
    GREGORIAN = "gregorian"  # Standard calendar (default)
    JULIAN_DAY = "julian_day"  # Julian Day Number (JD)
    JULIAN_CALENDAR = "julian_calendar"  # Julian calendar (pre-1582)
    UNIX_TIMESTAMP = "unix_timestamp"  # Unix epoch seconds
    ORDINAL_DATE = "ordinal_date"  # Year-day format (YYYY-DDD)
    ISO_WEEK_DATE = "iso_week_date"  # ISO week format (YYYY-Www-d)
    COMPACT_DATE = "compact_date"  # Compact format (YYYYMMDD)


# ─── VALUE OBJECTS ───

@dataclass(frozen=True)
class Location:
    name: str
    latitude: float
    longitude: float
    timezone: str


@dataclass(frozen=True)
class DateRange:
    start: datetime
    end: datetime


# ─── CORE ENTITIES ───

@dataclass
class ChartSubject:
    id: str
    name: str
    event_time: datetime
    location: Location


@dataclass
class ChartConfig:
    mode: ChartMode
    house_system: HouseSystem
    zodiac_type: ZodiacType
    included_points: List[str]
    aspect_orbs: Dict[str, float]
    display_style: str
    color_theme: str
    override_ephemeris: Optional[str] = None
    model: Optional[str] = None
    engine: Optional[EngineType] = None
    ayanamsa: Optional[Ayanamsa] = None
    # Override observable objects for this chart (extends/overrides workspace defaults)
    observable_objects: Optional[List[str]] = None
    # Time system for input/output (if different from workspace default)
    time_system: Optional[TimeSystem] = None


@dataclass
class ChartInstance:
    id: str
    subject: ChartSubject
    config: ChartConfig
    computed_chart: Optional["Horoscope"] = None
    tags: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class CelestialBody:
    id: str
    definition_id: str
    degree: float
    sign: str
    retrograde: bool
    speed: float


@dataclass(frozen=True)
class House:
    number: int
    cusp_degree: float
    sign: str


@dataclass(frozen=True)
class Aspect:
    type: str
    source_id: str
    target_id: str
    angle: float
    orb: float


@dataclass(frozen=True)
class Horoscope:
    for_time: datetime
    location: Location
    bodies: List[CelestialBody]
    houses: List[House]
    aspects: List[Aspect]


# ─── ASTROMODEL & DEFINITIONS ───

@dataclass(frozen=True)
class BodyDefinition:
    id: str
    glyph: str
    formula: str
    element: Optional[Element]  # Use Element enum instead of string
    avg_speed: float
    max_orb: float
    i18n: Dict[str, str]
    # Observable object metadata
    object_type: Optional[ObjectType] = None
    # Mapping of engine type to computation method/attribute name
    # e.g., {"jpl": "uranus", "swisseph": "uranus", "kerykeion": "uranus"}
    # or {"kerykeion": "asc", "jpl": null} for angles
    computation_map: Dict[str, Optional[str]] = field(default_factory=dict)
    # Whether this object requires location (for angles, houses)
    requires_location: bool = False
    # Whether this object requires house system (for houses, some angles)
    requires_house_system: bool = False


@dataclass(frozen=True)
class AspectDefinition:
    id: str
    glyph: str
    angle: float
    default_orb: float
    i18n: Dict[str, str]
    # Display and importance settings
    color: Optional[str] = None  # Hex color code (e.g., "#FF0000")
    importance: Optional[int] = None  # 1-10 scale, higher = more important
    line_style: Optional[str] = None  # "solid", "dashed", "dotted", etc.
    line_width: Optional[float] = None  # Line thickness for display
    show_label: Optional[bool] = None  # Whether to show aspect label in charts
    # Context where this aspect is applicable
    # If None or empty, aspect is valid for all contexts
    valid_contexts: Optional[List[AspectContext]] = None


@dataclass(frozen=True)
class Sign:
    name: str
    glyph: str
    abbreviation: str
    element: Element  # Use Element enum instead of string
    i18n: Dict[str, str]


@dataclass
class ModelSettings:
    default_house_system: HouseSystem
    default_aspects: List[str]  # Default aspects for charts/radix
    default_bodies: List[str]
    standard_orb: float
    # Context-specific aspect lists (optional, overrides default_aspects for specific contexts)
    default_transit_aspects: Optional[List[str]] = None
    default_direction_aspects: Optional[List[str]] = None
    # Context-specific body lists (optional, for transits/directions)
    default_transit_bodies: Optional[List[str]] = None
    default_direction_bodies: Optional[List[str]] = None


@dataclass
class AstroModel:
    name: str
    body_definitions: List[BodyDefinition]
    aspect_definitions: List[AspectDefinition]
    signs: List[Sign]
    settings: ModelSettings
    engine: Optional[EngineType] = None
    zodiac_type: Optional[ZodiacType] = None
    ayanamsa: Optional[Ayanamsa] = None


# ─── OVERRIDES ───

@dataclass
class OverrideEntry:
    id: str
    glyph: Optional[str] = None
    angle: Optional[float] = None
    default_orb: Optional[float] = None
    only_for: Optional[List[str]] = None
    i18n: Optional[Dict[str, str]] = None
    computed: Optional[bool] = None


@dataclass
class ModelOverrides:
    points: List[OverrideEntry] = field(default_factory=list)
    aspects: List[OverrideEntry] = field(default_factory=list)
    override_orbs: Dict[str, float] = field(default_factory=dict)


# ─── VIEW & LAYOUT ───

@dataclass
class ChartRelation:
    type: RelationType
    source: str
    target: str
    method: str
    time_span: Optional[DateRange] = None


@dataclass
class ViewModule:
    type: ViewModuleType
    config: Dict


@dataclass
class ViewLayout:
    name: str
    layout_style: LayoutStyle
    chart_instances: List[str]
    relations: List[ChartRelation] = field(default_factory=list)
    modules: List[ViewModule] = field(default_factory=list)


# ─── ANNOTATIONS & ATTACHMENTS ───

@dataclass
class Annotation:
    title: str
    content: str
    created: Optional[datetime]
    author: str


@dataclass
class Attachment:
    filename: str
    url: str
    type: str


# ─── WORKSPACE ───

@dataclass
class EphemerisSource:
    name: str
    backend: str


@dataclass
class ChartPreset:
    name: str
    config: ChartConfig


@dataclass
class AspectSettings:
    """Settings for a single aspect definition, including display properties."""
    id: str
    enabled: bool = True
    orb: Optional[float] = None  # Override default_orb if set
    color: Optional[str] = None
    importance: Optional[int] = None
    line_style: Optional[str] = None
    line_width: Optional[float] = None
    show_label: Optional[bool] = None


@dataclass
class ElementColorSettings:
    """Color settings for the four elements."""
    fire: str = "#C00000"  # Default red
    earth: str = "#909030"  # Default brown/olive
    air: str = "#8000FF"  # Default blue/purple
    water: str = "#0000A0"  # Default dark blue


@dataclass
class RadixPointColorSettings:
    """Color settings for radix (natal chart) points/planets.
    
    Maps object IDs to color hex codes. Common objects:
    - sun, moon, mercury, venus, mars, jupiter, saturn, uranus, neptune, pluto
    - asc, mc, ic, desc (angles)
    - north_node, south_node
    - lilith, chiron, etc.
    """
    colors: Dict[str, str] = field(default_factory=dict)  # object_id -> hex_color


@dataclass
class WorkspaceDefaults:
    """Aggregated default settings for a workspace (preferred YAML shape).

    This mirrors the desired manifest structure under the top-level key 'default'.
    """
    ephemeris_engine: Optional[EngineType] = None
    ephemeris_backend: Optional[str] = None
    location_name: Optional[str] = None
    location_latitude: Optional[float] = None
    location_longitude: Optional[float] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    theme: Optional[str] = None
    # Optional overrides to model defaults (when present these take precedence)
    default_house_system: Optional[HouseSystem] = None
    default_bodies: Optional[List[str]] = None
    default_aspects: Optional[List[str]] = None  # Legacy: simple list of aspect IDs
    # Observable objects to include in charts (list of object IDs from BodyDefinition)
    # This extends/overrides model.default_bodies with additional objects like angles, houses, etc.
    observable_objects: Optional[List[str]] = None
    # Aspect settings with full configuration (overrides default_aspects if present)
    aspect_settings: Optional[List[AspectSettings]] = None
    # Color settings
    element_colors: Optional[ElementColorSettings] = None
    radix_point_colors: Optional[RadixPointColorSettings] = None
    # Time system preference
    time_system: Optional[TimeSystem] = None


@dataclass
class Workspace:
    owner: str
    default_ephemeris: EphemerisSource
    active_model: str
    chart_presets: List[ChartPreset]
    subjects: List[ChartSubject]
    charts: List[ChartInstance]
    layouts: List[ViewLayout]
    annotations: List[Annotation]
    model_overrides: Optional[ModelOverrides] = None
    aspects: List[str] = field(default_factory=list)
    default: Optional[WorkspaceDefaults] = None
    # Loaded model catalogs available in this workspace, keyed by name
    models: Dict[str, AstroModel] = field(default_factory=dict)
    # Optional explicit name for active model (preferred over active_model if set)
    active_model_name: Optional[str] = None
