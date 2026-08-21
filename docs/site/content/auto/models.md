---

title: models Module

description: documentation for models module

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

### class `AspectContext` (str, Enum)

Contexts where an aspect can be used.

### class `AspectDefinition` 

AspectDefinition(id: str, glyph: str, angle: float, default_orb: float, i18n: Dict[str, str], color: Optional[str] = None, importance: Optional[int] = None, line_style: Optional[str] = None, line_width: Optional[float] = None, show_label: Optional[bool] = None, valid_contexts: Optional[List[module.models.AspectContext]] = None)

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
- `valid_contexts: Optional`

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

AstroModel(name: str, body_definitions: List[module.models.BodyDefinition], aspect_definitions: List[module.models.AspectDefinition], signs: List[module.models.Sign], settings: Optional[module.models.ModelSettings], engine: Optional[module.models.EngineType] = None, zodiac_type: Optional[module.models.ZodiacType] = None, ayanamsa: Optional[module.models.Ayanamsa] = None)

#### Dataclass fields

- `name: str`
- `body_definitions: List`
- `aspect_definitions: List`
- `signs: List`
- `settings: Optional`
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

BodyDefinition(id: str, glyph: str, formula: str, element: Optional[module.models.Element], avg_speed: float, max_orb: float, i18n: Dict[str, str], object_type: Optional[module.models.ObjectType] = None, computation_map: Dict[str, Optional[str]] = &lt;factory&gt;, requires_location: bool = False, requires_house_system: bool = False)

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

### class `ChartAxes` 

ChartAxes(asc: float, desc: float, mc: float, ic: float)

#### Dataclass fields

- `asc: float`
- `desc: float`
- `mc: float`
- `ic: float`

### class `ChartCalculation` 

ChartCalculation(positions: Dict[str, Any], motion: Dict[str, Any], aspects: List[Dict[str, Any]], axes: Dict[str, float], house_cusps: List[float], moon_details: Optional[Dict[str, Any]], chart_id: str, backend_used: str, fallback_used: bool, ephemeris_source: Optional[str], warnings: List[str])

#### Dataclass fields

- `positions: Dict`
- `motion: Dict`
- `aspects: List`
- `axes: Dict`
- `house_cusps: List`
- `moon_details: Optional`
- `chart_id: str`
- `backend_used: str`
- `fallback_used: bool`
- `ephemeris_source: Optional`
- `warnings: List`

### class `ChartConfig` 

ChartConfig(mode: module.models.ChartMode, house_system: Optional[module.models.HouseSystem], zodiac_type: module.models.ZodiacType, included_points: List[str], aspect_orbs: Dict[str, float], display_style: str, color_theme: str, selected_aspects: Optional[List[str]] = None, override_ephemeris: Optional[str] = None, model: Optional[str] = None, engine: Optional[module.models.EngineType] = None, ayanamsa: Optional[module.models.Ayanamsa] = None, observable_objects: Optional[List[str]] = None, time_system: Optional[module.models.TimeSystem] = None)

#### Dataclass fields

- `mode: ChartMode`
- `house_system: Optional`
- `zodiac_type: ZodiacType`
- `included_points: List`
- `aspect_orbs: Dict`
- `display_style: str`
- `color_theme: str`
- `selected_aspects: Optional`
- `override_ephemeris: Optional`
- `model: Optional`
- `engine: Optional`
- `ayanamsa: Optional`
- `observable_objects: Optional`
- `time_system: Optional`

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

ChartSubject(id: str, name: str, event_time: Optional[datetime.datetime], location: module.models.Location)

#### Dataclass fields

- `id: str`
- `name: str`
- `event_time: Optional`
- `location: Location`

### class `ComputedAspect` 

ComputedAspect(from_id: str, to_id: str, type: str, angle: float, orb: float, exact_angle: float, applying: bool = False, separating: bool = False)

#### Dataclass fields

- `from_id: str`
- `to_id: str`
- `type: str`
- `angle: float`
- `orb: float`
- `exact_angle: float`
- `applying: bool`
- `separating: bool`

### class `CurrentModelReport` 

CurrentModelReport(requested_model: Optional[str], resolved_model: str, source: str, available_models: List[str], model: module.models.AstroModel, effective_settings: module.models.EffectiveModelSettings, model_overrides: Optional[module.models.ModelOverrides], warnings: List[str], diagnostics: List[module.models.Diagnostic])

#### Dataclass fields

- `requested_model: Optional`
- `resolved_model: str`
- `source: str`
- `available_models: List`
- `model: AstroModel`
- `effective_settings: EffectiveModelSettings`
- `model_overrides: Optional`
- `warnings: List`
- `diagnostics: List`

### class `DateRange` 

DateRange(start: datetime.datetime, end: datetime.datetime)

#### Dataclass fields

- `start: datetime`
- `end: datetime`

### class `Diagnostic` 

Diagnostic(code: str, severity: module.models.DiagnosticSeverity, message: str, path: Optional[str] = None)

#### Dataclass fields

- `code: str`
- `severity: DiagnosticSeverity`
- `message: str`
- `path: Optional`

### class `DiagnosticSeverity` (str, Enum)

### class `EffectiveModelSettings` 

EffectiveModelSettings(default_house_system: Optional[module.models.HouseSystem], default_bodies: List[str], default_aspects: List[str], default_transit_aspects: Optional[List[str]], default_direction_aspects: Optional[List[str]], default_transit_bodies: Optional[List[str]], default_direction_bodies: Optional[List[str]], aspect_orbs: Dict[str, float], standard_orb: float, engine: Optional[module.models.EngineType], zodiac_type: Optional[module.models.ZodiacType], ayanamsa: Optional[module.models.Ayanamsa], time_system: Optional[module.models.TimeSystem], degrees_in_circle: float, obliquity_j2000: float, coordinate_tolerance: float, sources: module.models.EffectiveSettingsSources)

#### Dataclass fields

- `default_house_system: Optional`
- `default_bodies: List`
- `default_aspects: List`
- `default_transit_aspects: Optional`
- `default_direction_aspects: Optional`
- `default_transit_bodies: Optional`
- `default_direction_bodies: Optional`
- `aspect_orbs: Dict`
- `standard_orb: float`
- `engine: Optional`
- `zodiac_type: Optional`
- `ayanamsa: Optional`
- `time_system: Optional`
- `degrees_in_circle: float`
- `obliquity_j2000: float`
- `coordinate_tolerance: float`
- `sources: EffectiveSettingsSources`

### class `EffectiveSettingsSources` 

EffectiveSettingsSources(default_house_system: Optional[module.models.SettingSource], default_bodies: module.models.SettingSource, default_aspects: module.models.SettingSource, aspect_orbs: Dict[str, module.models.SettingSource], standard_orb: module.models.SettingSource, engine: Optional[module.models.SettingSource], zodiac_type: Optional[module.models.SettingSource], ayanamsa: Optional[module.models.SettingSource], time_system: Optional[module.models.SettingSource], computational_constants: module.models.SettingSource)

#### Dataclass fields

- `default_house_system: Optional`
- `default_bodies: SettingSource`
- `default_aspects: SettingSource`
- `aspect_orbs: Dict`
- `standard_orb: SettingSource`
- `engine: Optional`
- `zodiac_type: Optional`
- `ayanamsa: Optional`
- `time_system: Optional`
- `computational_constants: SettingSource`

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

### class `LoadedWorkspace` 

LoadedWorkspace(manifest: Dict[str, Any], workspace: module.models.Workspace, diagnostics: List[ForwardRef('Diagnostic')])

#### Methods

- `validation_report(self) -> module.models.WorkspaceValidationReport`

#### Dataclass fields

- `manifest: Dict`
- `workspace: Workspace`
- `diagnostics: List`

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

ModelSettings(default_house_system: module.models.HouseSystem, default_aspects: List[str], default_bodies: List[str], standard_orb: float, default_transit_aspects: Optional[List[str]] = None, default_direction_aspects: Optional[List[str]] = None, default_transit_bodies: Optional[List[str]] = None, default_direction_bodies: Optional[List[str]] = None, degrees_in_circle: float = 360.0, obliquity_j2000: float = 23.4392911, coordinate_tolerance: float = 0.0001)

#### Dataclass fields

- `default_house_system: HouseSystem`
- `default_aspects: List`
- `default_bodies: List`
- `standard_orb: float`
- `default_transit_aspects: Optional`
- `default_direction_aspects: Optional`
- `default_transit_bodies: Optional`
- `default_direction_bodies: Optional`
- `degrees_in_circle: float`
- `obliquity_j2000: float`
- `coordinate_tolerance: float`

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

### class `SettingSource` (str, Enum)

### class `SettingsLayer` 

SettingsLayer(house_system: Optional[module.models.HouseSystem] = None, bodies: Optional[List[str]] = None, aspects: Optional[List[str]] = None, aspect_orbs: Dict[str, float] = &lt;factory&gt;, engine: Optional[module.models.EngineType] = None, zodiac_type: Optional[module.models.ZodiacType] = None, ayanamsa: Optional[module.models.Ayanamsa] = None, time_system: Optional[module.models.TimeSystem] = None)

#### Dataclass fields

- `house_system: Optional`
- `bodies: Optional`
- `aspects: Optional`
- `aspect_orbs: Dict`
- `engine: Optional`
- `zodiac_type: Optional`
- `ayanamsa: Optional`
- `time_system: Optional`

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

### class `TransitSeriesCalculation` 

TransitSeriesCalculation(source_chart_id: str, time_range: Dict[str, str], time_step: str, results: List[module.models.TransitSeriesStep], backend_used: str, fallback_used: bool, ephemeris_source: Optional[str], warnings: List[str])

#### Dataclass fields

- `source_chart_id: str`
- `time_range: Dict`
- `time_step: str`
- `results: List`
- `backend_used: str`
- `fallback_used: bool`
- `ephemeris_source: Optional`
- `warnings: List`

### class `TransitSeriesStep` 

TransitSeriesStep(datetime: str, transit_positions: Dict[str, Any], aspects: List[Dict[str, Any]])

#### Dataclass fields

- `datetime: str`
- `transit_positions: Dict`
- `aspects: List`

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
- `active_model: Optional`
- `default: WorkspaceDefaults`
- `aspects: List`
- `bodies: List`
- `models: Dict`
- `model_overrides: Optional`

### class `WorkspaceDefaults` 

Aggregated default settings for a workspace (preferred YAML shape).

This mirrors the desired manifest structure under the top-level key 'default'.
Provides workspace-wide defaults that can be overridden at the workspace level.

#### Dataclass fields

- `default_house_system: Optional`
- `default_bodies: Optional`
- `default_aspects: Optional`
- `default_aspect_orbs: Optional`
- `default_aspect_colors: Optional`
- `ephemeris_engine: Optional`
- `ephemeris_backend: Optional`
- `element_colors: Optional`
- `radix_point_colors: Optional`
- `default_location: Optional`
- `language: Optional`
- `theme: Optional`
- `time_system: Optional`

### class `WorkspaceEntityCounts` 

WorkspaceEntityCounts(subjects: int, charts: int, chart_presets: int, layouts: int, annotations: int)

#### Dataclass fields

- `subjects: int`
- `charts: int`
- `chart_presets: int`
- `layouts: int`
- `annotations: int`

### class `WorkspaceValidationReport` 

WorkspaceValidationReport(owner: str, active_model: Optional[str], valid: bool, counts: module.models.WorkspaceEntityCounts, diagnostics: List[ForwardRef('Diagnostic')])

#### Dataclass fields

- `owner: str`
- `active_model: Optional`
- `valid: bool`
- `counts: WorkspaceEntityCounts`
- `diagnostics: List`

### class `ZodiacType` (str, Enum)
