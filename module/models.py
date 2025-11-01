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
    element: Optional[str]
    avg_speed: float
    max_orb: float
    i18n: Dict[str, str]


@dataclass(frozen=True)
class AspectDefinition:
    id: str
    glyph: str
    angle: float
    default_orb: float
    i18n: Dict[str, str]


@dataclass(frozen=True)
class Sign:
    name: str
    glyph: str
    abbreviation: str
    element: str
    i18n: Dict[str, str]


@dataclass
class ModelSettings:
    default_house_system: HouseSystem
    default_aspects: List[str]
    default_bodies: List[str]
    standard_orb: float


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
