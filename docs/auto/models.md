---

title: models Module

description: API documentation for models module

weight: 10

---


# `models` module

## Classes

### class `Annotation` 

Annotation(title: str, content: str, created: Optional[datetime.datetime], author: str)

#### Dataclass fields

- `title: str`
- `content: str`
- `created: Optional`
- `author: str`

### class `Aspect` 

Aspect(type: str, source_id: str, target_id: str, angle: float, orb: float)

#### Dataclass fields

- `type: str`
- `source_id: str`
- `target_id: str`
- `angle: float`
- `orb: float`

### class `AspectDefinition` 

AspectDefinition(id: str, glyph: str, angle: float, default_orb: float, i18n: Dict[str, str], color: Optional[str] = None, importance: Optional[int] = None, line_style: Optional[str] = None, line_width: Optional[float] = None, show_label: Optional[bool] = None)

#### Dataclass fields

- `id: str`
- `glyph: str`
- `angle: float`
- `default_orb: float`
- `i18n: Dict`
- `color: Optional`
- `importance: Optional`
- `line_style: Optional`
- `line_width: Optional`
- `show_label: Optional`

### class `AspectSettings` 

Settings for a single aspect definition, including display properties.

#### Dataclass fields

- `id: str`
- `enabled: bool`
- `orb: Optional`
- `color: Optional`
- `importance: Optional`
- `line_style: Optional`
- `line_width: Optional`
- `show_label: Optional`

### class `AstroModel` 

AstroModel(name: str, body_definitions: List[module.models.BodyDefinition], aspect_definitions: List[module.models.AspectDefinition], signs: List[module.models.Sign], settings: module.models.ModelSettings, engine: Optional[module.models.EngineType] = None, zodiac_type: Optional[module.models.ZodiacType] = None, ayanamsa: Optional[module.models.Ayanamsa] = None)

#### Dataclass fields

- `name: str`
- `body_definitions: List`
- `aspect_definitions: List`
- `signs: List`
- `settings: ModelSettings`
- `engine: Optional`
- `zodiac_type: Optional`
- `ayanamsa: Optional`

### class `Attachment` 

Attachment(filename: str, url: str, type: str)

#### Dataclass fields

- `filename: str`
- `url: str`
- `type: str`

### class `Ayanamsa` (str, Enum)

### class `BodyDefinition` 

BodyDefinition(id: str, glyph: str, formula: str, element: Optional[str], avg_speed: float, max_orb: float, i18n: Dict[str, str], object_type: Optional[module.models.ObjectType] = None, computation_map: Dict[str, Optional[str]] = &lt;factory&gt;, requires_location: bool = False, requires_house_system: bool = False)

#### Dataclass fields

- `id: str`
- `glyph: str`
- `formula: str`
- `element: Optional`
- `avg_speed: float`
- `max_orb: float`
- `i18n: Dict`
- `object_type: Optional`
- `computation_map: Dict`
- `requires_location: bool`
- `requires_house_system: bool`

### class `CelestialBody` 

CelestialBody(id: str, definition_id: str, degree: float, sign: str, retrograde: bool, speed: float)

#### Dataclass fields

- `id: str`
- `definition_id: str`
- `degree: float`
- `sign: str`
- `retrograde: bool`
- `speed: float`

### class `ChartConfig` 

ChartConfig(mode: module.models.ChartMode, house_system: module.models.HouseSystem, zodiac_type: module.models.ZodiacType, included_points: List[str], aspect_orbs: Dict[str, float], display_style: str, color_theme: str, override_ephemeris: Optional[str] = None, model: Optional[str] = None, engine: Optional[module.models.EngineType] = None, ayanamsa: Optional[module.models.Ayanamsa] = None, observable_objects: Optional[List[str]] = None)

#### Dataclass fields

- `mode: ChartMode`
- `house_system: HouseSystem`
- `zodiac_type: ZodiacType`
- `included_points: List`
- `aspect_orbs: Dict`
- `display_style: str`
- `color_theme: str`
- `override_ephemeris: Optional`
- `model: Optional`
- `engine: Optional`
- `ayanamsa: Optional`
- `observable_objects: Optional`

### class `ChartInstance` 

ChartInstance(id: str, subject: module.models.ChartSubject, config: module.models.ChartConfig, computed_chart: Optional[ForwardRef('Horoscope')] = None, tags: List[str] = &lt;factory&gt;)

#### Dataclass fields

- `id: str`
- `subject: ChartSubject`
- `config: ChartConfig`
- `computed_chart: Optional`
- `tags: List`

### class `ChartMode` (str, Enum)

### class `ChartPreset` 

ChartPreset(name: str, config: module.models.ChartConfig)

#### Dataclass fields

- `name: str`
- `config: ChartConfig`

### class `ChartRelation` 

ChartRelation(type: module.models.RelationType, source: str, target: str, method: str, time_span: Optional[module.models.DateRange] = None)

#### Dataclass fields

- `type: RelationType`
- `source: str`
- `target: str`
- `method: str`
- `time_span: Optional`

### class `ChartSubject` 

ChartSubject(id: str, name: str, event_time: datetime.datetime, location: module.models.Location)

#### Dataclass fields

- `id: str`
- `name: str`
- `event_time: datetime`
- `location: Location`

### class `DateRange` 

DateRange(start: datetime.datetime, end: datetime.datetime)

#### Dataclass fields

- `start: datetime`
- `end: datetime`

### class `EngineType` (str, Enum)

### class `EphemerisSource` 

EphemerisSource(name: str, backend: str)

#### Dataclass fields

- `name: str`
- `backend: str`

### class `Horoscope` 

Horoscope(for_time: datetime.datetime, location: module.models.Location, bodies: List[module.models.CelestialBody], houses: List[module.models.House], aspects: List[module.models.Aspect])

#### Dataclass fields

- `for_time: datetime`
- `location: Location`
- `bodies: List`
- `houses: List`
- `aspects: List`

### class `House` 

House(number: int, cusp_degree: float, sign: str)

#### Dataclass fields

- `number: int`
- `cusp_degree: float`
- `sign: str`

### class `HouseSystem` (str, Enum)

### class `LayoutStyle` (str, Enum)

### class `Location` 

Location(name: str, latitude: float, longitude: float, timezone: str)

#### Dataclass fields

- `name: str`
- `latitude: float`
- `longitude: float`
- `timezone: str`

### class `ModelOverrides` 

ModelOverrides(points: List[module.models.OverrideEntry] = &lt;factory&gt;, aspects: List[module.models.OverrideEntry] = &lt;factory&gt;, override_orbs: Dict[str, float] = &lt;factory&gt;)

#### Dataclass fields

- `points: List`
- `aspects: List`
- `override_orbs: Dict`

### class `ModelSettings` 

ModelSettings(default_house_system: module.models.HouseSystem, default_aspects: List[str], default_bodies: List[str], standard_orb: float)

#### Dataclass fields

- `default_house_system: HouseSystem`
- `default_aspects: List`
- `default_bodies: List`
- `standard_orb: float`

### class `ObjectType` (str, Enum)

Type of observable object in the chart.

### class `OverrideEntry` 

OverrideEntry(id: str, glyph: Optional[str] = None, angle: Optional[float] = None, default_orb: Optional[float] = None, only_for: Optional[List[str]] = None, i18n: Optional[Dict[str, str]] = None, computed: Optional[bool] = None)

#### Dataclass fields

- `id: str`
- `glyph: Optional`
- `angle: Optional`
- `default_orb: Optional`
- `only_for: Optional`
- `i18n: Optional`
- `computed: Optional`

### class `RelationType` (str, Enum)

### class `Sign` 

Sign(name: str, glyph: str, abbreviation: str, element: str, i18n: Dict[str, str])

#### Dataclass fields

- `name: str`
- `glyph: str`
- `abbreviation: str`
- `element: str`
- `i18n: Dict`

### class `ViewLayout` 

ViewLayout(name: str, layout_style: module.models.LayoutStyle, chart_instances: List[str], relations: List[module.models.ChartRelation] = &lt;factory&gt;, modules: List[module.models.ViewModule] = &lt;factory&gt;)

#### Dataclass fields

- `name: str`
- `layout_style: LayoutStyle`
- `chart_instances: List`
- `relations: List`
- `modules: List`

### class `ViewModule` 

ViewModule(type: module.models.ViewModuleType, config: Dict)

#### Dataclass fields

- `type: ViewModuleType`
- `config: Dict`

### class `ViewModuleType` (str, Enum)

### class `Workspace` 

Workspace(owner: str, default_ephemeris: module.models.EphemerisSource, active_model: str, chart_presets: List[module.models.ChartPreset], subjects: List[module.models.ChartSubject], charts: List[module.models.ChartInstance], layouts: List[module.models.ViewLayout], annotations: List[module.models.Annotation], model_overrides: Optional[module.models.ModelOverrides] = None, aspects: List[str] = &lt;factory&gt;, default: Optional[module.models.WorkspaceDefaults] = None, models: Dict[str, module.models.AstroModel] = &lt;factory&gt;, active_model_name: Optional[str] = None)

#### Dataclass fields

- `owner: str`
- `default_ephemeris: EphemerisSource`
- `active_model: str`
- `chart_presets: List`
- `subjects: List`
- `charts: List`
- `layouts: List`
- `annotations: List`
- `model_overrides: Optional`
- `aspects: List`
- `default: Optional`
- `models: Dict`
- `active_model_name: Optional`

### class `WorkspaceDefaults` 

Aggregated default settings for a workspace (preferred YAML shape).

This mirrors the desired manifest structure under the top-level key 'default'.

#### Dataclass fields

- `ephemeris_engine: Optional`
- `ephemeris_backend: Optional`
- `location_name: Optional`
- `location_latitude: Optional`
- `location_longitude: Optional`
- `timezone: Optional`
- `language: Optional`
- `theme: Optional`
- `default_house_system: Optional`
- `default_bodies: Optional`
- `default_aspects: Optional`
- `observable_objects: Optional`
- `aspect_settings: Optional`

### class `ZodiacType` (str, Enum)
