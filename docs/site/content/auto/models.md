---

title: models Module

description: documentation for models module

weight: 10

---


# `models` module

## Classes

### class `Annotation` 

Annotation(title: str, content: str, created: datetime.datetime | None, author: str)

#### Dataclass fields

- `title: str`
- `content: str`
- `created: Union`
- `author: str`

### class `Aspect` 

Aspect(type: str, source_id: str, target_id: str, angle: float, orb: float)

#### Dataclass fields

- `type: str`
- `source_id: str`
- `target_id: str`
- `angle: float`
- `orb: float`

### class `AspectContext` (str, Enum)

Contexts where an aspect can be used.

### class `AspectDefinition` 

AspectDefinition(id: str, glyph: str, angle: float, default_orb: float, i18n: Dict[str, str], color: str | None = None, importance: int | None = None, line_style: str | None = None, line_width: float | None = None, show_label: bool | None = None, valid_contexts: List[module.models.AspectContext] | None = None)

#### Dataclass fields

- `id: str`
- `glyph: str`
- `angle: float`
- `default_orb: float`
- `i18n: Dict`
- `color: Union`
- `importance: Union`
- `line_style: Union`
- `line_width: Union`
- `show_label: Union`
- `valid_contexts: Union`

### class `AspectSettings` 

Settings for a single aspect definition, including display properties.

#### Dataclass fields

- `id: str`
- `enabled: bool`
- `orb: Union`
- `color: Union`
- `importance: Union`
- `line_style: Union`
- `line_width: Union`
- `show_label: Union`

### class `AstroModel` 

AstroModel(name: str, body_definitions: List[module.models.BodyDefinition], aspect_definitions: List[module.models.AspectDefinition], signs: List[module.models.Sign], settings: module.models.ModelSettings, engine: module.models.EngineType | None = None, zodiac_type: module.models.ZodiacType | None = None, ayanamsa: module.models.Ayanamsa | None = None)

#### Dataclass fields

- `name: str`
- `body_definitions: List`
- `aspect_definitions: List`
- `signs: List`
- `settings: ModelSettings`
- `engine: Union`
- `zodiac_type: Union`
- `ayanamsa: Union`

### class `Attachment` 

Attachment(filename: str, url: str, type: str)

#### Dataclass fields

- `filename: str`
- `url: str`
- `type: str`

### class `Ayanamsa` (str, Enum)

### class `BodyDefinition` 

BodyDefinition(id: str, glyph: str, formula: str, element: module.models.Element | None, avg_speed: float, max_orb: float, i18n: Dict[str, str], object_type: module.models.ObjectType | None = None, computation_map: Dict[str, str | None] = &lt;factory&gt;, requires_location: bool = False, requires_house_system: bool = False)

#### Dataclass fields

- `id: str`
- `glyph: str`
- `formula: str`
- `element: Union`
- `avg_speed: float`
- `max_orb: float`
- `i18n: Dict`
- `object_type: Union`
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

ChartConfig(mode: module.models.ChartMode, house_system: module.models.HouseSystem, zodiac_type: module.models.ZodiacType, included_points: List[str], aspect_orbs: Dict[str, float], display_style: str, color_theme: str, override_ephemeris: str | None = None, model: str | None = None, engine: module.models.EngineType | None = None, ayanamsa: module.models.Ayanamsa | None = None, observable_objects: List[str] | None = None, time_system: module.models.TimeSystem | None = None)

#### Dataclass fields

- `mode: ChartMode`
- `house_system: HouseSystem`
- `zodiac_type: ZodiacType`
- `included_points: List`
- `aspect_orbs: Dict`
- `display_style: str`
- `color_theme: str`
- `override_ephemeris: Union`
- `model: Union`
- `engine: Union`
- `ayanamsa: Union`
- `observable_objects: Union`
- `time_system: Union`

### class `ChartInstance` 

ChartInstance(id: str, subject: module.models.ChartSubject, config: module.models.ChartConfig, computed_chart: ForwardRef('Horoscope') | None = None, tags: List[str] = &lt;factory&gt;)

#### Dataclass fields

- `id: str`
- `subject: ChartSubject`
- `config: ChartConfig`
- `computed_chart: Union`
- `tags: List`

### class `ChartMode` (str, Enum)

### class `ChartPreset` 

ChartPreset(name: str, config: module.models.ChartConfig)

#### Dataclass fields

- `name: str`
- `config: ChartConfig`

### class `ChartRelation` 

ChartRelation(type: module.models.RelationType, source: str, target: str, method: str, time_span: module.models.DateRange | None = None)

#### Dataclass fields

- `type: RelationType`
- `source: str`
- `target: str`
- `method: str`
- `time_span: Union`

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

### class `Element` (str, Enum)

The four classical elements.

### class `ElementColorSettings` 

Color settings for the four elements.

#### Dataclass fields

- `fire: str`
- `earth: str`
- `air: str`
- `water: str`

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

ModelSettings(default_house_system: module.models.HouseSystem, default_aspects: List[str], default_bodies: List[str], standard_orb: float, default_transit_aspects: List[str] | None = None, default_direction_aspects: List[str] | None = None, default_transit_bodies: List[str] | None = None, default_direction_bodies: List[str] | None = None, degrees_in_circle: float = 360.0, obliquity_j2000: float = 23.4392911, coordinate_tolerance: float = 0.0001)

#### Dataclass fields

- `default_house_system: HouseSystem`
- `default_aspects: List`
- `default_bodies: List`
- `standard_orb: float`
- `default_transit_aspects: Union`
- `default_direction_aspects: Union`
- `default_transit_bodies: Union`
- `default_direction_bodies: Union`
- `degrees_in_circle: float`
- `obliquity_j2000: float`
- `coordinate_tolerance: float`

### class `ObjectType` (str, Enum)

Type of observable object in the chart.

### class `OverrideEntry` 

OverrideEntry(id: str, glyph: str | None = None, angle: float | None = None, default_orb: float | None = None, only_for: List[str] | None = None, i18n: Dict[str, str] | None = None, computed: bool | None = None)

#### Dataclass fields

- `id: str`
- `glyph: Union`
- `angle: Union`
- `default_orb: Union`
- `only_for: Union`
- `i18n: Union`
- `computed: Union`

### class `RadixPointColorSettings` 

Color settings for radix (natal chart) points/planets.

Maps object IDs to color hex codes. Common objects:
- sun, moon, mercury, venus, mars, jupiter, saturn, uranus, neptune, pluto
- asc, mc, ic, desc (angles)
- north_node, south_node
- lilith, chiron, etc.

#### Dataclass fields

- `colors: Dict`

### class `RelationType` (str, Enum)

### class `Sign` 

Sign(name: str, glyph: str, abbreviation: str, element: module.models.Element, i18n: Dict[str, str])

#### Dataclass fields

- `name: str`
- `glyph: str`
- `abbreviation: str`
- `element: Element`
- `i18n: Dict`

### class `TimeSystem` (str, Enum)

Time representation systems.

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

Complete workspace container for astrological chart analysis.

A Workspace represents a project or collection of astrological work, containing
all the data, settings, and configurations needed for chart computation and analysis.
It serves as the top-level organizational unit for managing charts, subjects, and
their associated metadata.

Structure:
    - **Identity & Configuration**:
        - owner: Workspace owner/creator identifier
        - active_model: Currently active astrological model (e.g., "western", "vedic")
        - default: Default settings (ephemeris, location, house system, language, theme)
        
    - **Astrological Models**:
        - models: Available astrological model catalogs (planet/aspect definitions, zodiac systems)
        - model_overrides: Custom modifications to model definitions
        
    - **Core Data Collections**:
        - subjects: People or events for which charts can be created
        - charts: Computed chart instances (actual charts with planetary positions)
        - chart_presets: Reusable configuration templates (house system, display settings)
        
    - **Organization & Presentation**:
        - layouts: View configurations for displaying charts (single, dual-wheel, comparison)
        - annotations: Notes, interpretations, and commentary
        - aspects: List of aspect IDs enabled for this workspace
        
Typical Usage:
    1. Load or create a workspace
    2. Add subjects (people/events with birth data)
    3. Create charts using subjects and presets
    4. Apply layouts to visualize charts
    5. Add annotations for interpretation
    
Example:
    ```python
    ws = Workspace(
        owner="astrologer@example.com",
        active_model="western",
        default=WorkspaceDefaults(
            ephemeris_engine=EngineType.SWISSEPH,
            ephemeris_backend=None,
            default_house_system=HouseSystem.PLACIDUS
        ),
        subjects=[...],
        charts=[...]
    )
    ```

#### Dataclass fields

- `owner: str`
- `subjects: List`
- `charts: List`
- `chart_presets: List`
- `layouts: List`
- `annotations: List`
- `active_model: Union`
- `default: WorkspaceDefaults`
- `aspects: List`
- `bodies: List`
- `models: Dict`
- `model_overrides: Union`

### class `WorkspaceDefaults` 

Aggregated default settings for a workspace (preferred YAML shape).

This mirrors the desired manifest structure under the top-level key 'default'.
Provides workspace-wide defaults that can be overridden at the workspace level.

#### Dataclass fields

- `default_house_system: Union`
- `default_bodies: Union`
- `default_aspects: Union`
- `ephemeris_engine: Union`
- `ephemeris_backend: Union`
- `element_colors: Union`
- `radix_point_colors: Union`
- `default_location: Union`
- `language: Union`
- `theme: Union`
- `time_system: Union`

### class `ZodiacType` (str, Enum)
