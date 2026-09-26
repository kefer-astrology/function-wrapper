---

title: models Module

description: documentation for models module

weight: 10

---


# `models` module

## Classes

### class `AnalysisInput`

AnalysisInput(role: str | None = None, chart_id: str | None = None, inline_subject: module.models.ChartSubject | None = None, derivations: List[module.models.DerivedChartStep] = &lt;factory&gt;)

#### Dataclass fields

- `role: Union`
- `chart_id: Union`
- `inline_subject: Union`
- `derivations: List`

### class `AnalysisInstance`

AnalysisInstance(id: str, name: str, method: module.models.AnalysisMethod, inputs: List[module.models.AnalysisInput], version: int = 1, parameters: Dict[str, Any] = &lt;factory&gt;, tags: List[str] = &lt;factory&gt;)

#### Dataclass fields

- `id: str`
- `name: str`
- `method: AnalysisMethod`
- `inputs: List`
- `version: int`
- `parameters: Dict`
- `tags: List`

### class `AnalysisMethod` (str, Enum)

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

AspectDefinition(id: str, glyph: str, angle: float, default_orb: float, i18n: Dict[str, str], enabled: bool = True, color: str | None = None, importance: int | None = None, line_style: str | None = None, line_width: float | None = None, show_label: bool | None = None, valid_contexts: List[module.models.AspectContext] | None = None, interpretation_weight: float | None = None)

#### Dataclass fields

- `id: str`
- `glyph: str`
- `angle: float`
- `default_orb: float`
- `i18n: Dict`
- `enabled: bool`
- `color: Union`
- `importance: Union`
- `line_style: Union`
- `line_width: Union`
- `show_label: Union`
- `valid_contexts: Union`
- `interpretation_weight: Union`

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

AstroModel(name: str, body_definitions: List[module.models.BodyDefinition], aspect_definitions: List[module.models.AspectDefinition], signs: List[module.models.Sign], settings: module.models.ModelSettings | None, engine: module.models.EngineType | None = None, zodiac_type: module.models.ZodiacType | None = None, ayanamsa: module.models.Ayanamsa | None = None, school: str | None = None, version: int = 1)

#### Dataclass fields

- `name: str`
- `body_definitions: List`
- `aspect_definitions: List`
- `signs: List`
- `settings: Union`
- `engine: Union`
- `zodiac_type: Union`
- `ayanamsa: Union`
- `school: Union`
- `version: int`

### class `AstrologySchool`

AstrologySchool(id: str, default_model: str, extends: str | None = None)

#### Dataclass fields

- `id: str`
- `default_model: str`
- `extends: Union`

### class `Attachment`

Attachment(filename: str, url: str, type: str)

#### Dataclass fields

- `filename: str`
- `url: str`
- `type: str`

### class `Ayanamsa` (str, Enum)

### class `BaseChartPurpose` (str, Enum)

### class `BodyDefinition`

BodyDefinition(id: str, glyph: str, formula: str, element: module.models.Element | None, avg_speed: float, max_orb: float, i18n: Dict[str, str], enabled: bool = True, object_type: module.models.ObjectType | None = None, computation_map: Dict[str, str | None] = &lt;factory&gt;, requires_location: bool = False, requires_house_system: bool = False)

#### Dataclass fields

- `id: str`
- `glyph: str`
- `formula: str`
- `element: Union`
- `avg_speed: float`
- `max_orb: float`
- `i18n: Dict`
- `enabled: bool`
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

### class `ChartAxes`

ChartAxes(asc: float, desc: float, mc: float, ic: float)

#### Dataclass fields

- `asc: float`
- `desc: float`
- `mc: float`
- `ic: float`

### class `ChartCalculation`

ChartCalculation(positions: Dict[str, Any], motion: Dict[str, Any], aspects: List[Dict[str, Any]], axes: Dict[str, float], house_cusps: List[float], moon_details: Dict[str, Any] | None, chart_id: str, backend_used: str, fallback_used: bool, ephemeris_source: str | None, warnings: List[str])

#### Dataclass fields

- `positions: Dict`
- `motion: Dict`
- `aspects: List`
- `axes: Dict`
- `house_cusps: List`
- `moon_details: Union`
- `chart_id: str`
- `backend_used: str`
- `fallback_used: bool`
- `ephemeris_source: Union`
- `warnings: List`

### class `ChartConfig`

ChartConfig(definition: module.models.ChartDefinition, house_system: module.models.HouseSystem | None, zodiac_type: module.models.ZodiacType, aspect_orbs: Dict[str, float], selected_aspects: List[str] | None = None, override_ephemeris: str | None = None, model: str | None = None, engine: module.models.EngineType | None = None, position_mode: module.models.PositionMode | None = None, ayanamsa: module.models.Ayanamsa | None = None, observable_objects: List[str] | None = None, time_system: module.models.TimeSystem | None = None, model_overrides: ForwardRef('ModelOverrides') | None = None)

#### Dataclass fields

- `definition: ChartDefinition`
- `house_system: Union`
- `zodiac_type: ZodiacType`
- `aspect_orbs: Dict`
- `selected_aspects: Union`
- `override_ephemeris: Union`
- `model: Union`
- `engine: Union`
- `position_mode: Union`
- `ayanamsa: Union`
- `observable_objects: Union`
- `time_system: Union`
- `model_overrides: Union`

### class `ChartDefinition`

ChartDefinition(kind: str, purpose: module.models.BaseChartPurpose | None = None, method: module.models.DerivedChartMethod | None = None, inputs: List[str] = &lt;factory&gt;, parameters: Dict[str, Any] = &lt;factory&gt;)

#### Dataclass fields

- `kind: str`
- `purpose: Union`
- `method: Union`
- `inputs: List`
- `parameters: Dict`

### class `ChartInstance`

ChartInstance(id: str, subject: module.models.ChartSubject, config: module.models.ChartConfig, computed_chart: ForwardRef('Horoscope') | None = None, tags: List[str] = &lt;factory&gt;, tag_colors: Dict[str, str] = &lt;factory&gt;, roden_rating: str | None = None)

#### Dataclass fields

- `id: str`
- `subject: ChartSubject`
- `config: ChartConfig`
- `computed_chart: Union`
- `tags: List`
- `tag_colors: Dict`
- `roden_rating: Union`

### class `ChartPreset`

ChartPreset(name: str, config: module.models.ChartConfig)

#### Dataclass fields

- `name: str`
- `config: ChartConfig`

### class `ChartSubject`

ChartSubject(id: str, name: str, event_time: datetime.datetime | None, location: module.models.Location)

#### Dataclass fields

- `id: str`
- `name: str`
- `event_time: Union`
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

CurrentModelReport(requested_school: str | None, resolved_school: str | None, requested_model: str | None, resolved_model: str, source: str, available_models: List[str], model: module.models.AstroModel, effective_settings: module.models.EffectiveModelSettings, model_overrides: module.models.ModelOverrides | None, warnings: List[str], diagnostics: List[module.models.Diagnostic])

#### Dataclass fields

- `requested_school: Union`
- `resolved_school: Union`
- `requested_model: Union`
- `resolved_model: str`
- `source: str`
- `available_models: List`
- `model: AstroModel`
- `effective_settings: EffectiveModelSettings`
- `model_overrides: Union`
- `warnings: List`
- `diagnostics: List`

### class `DateRange`

DateRange(start: datetime.datetime, end: datetime.datetime)

#### Dataclass fields

- `start: datetime`
- `end: datetime`

### class `DerivedChartMethod` (str, Enum)

### class `DerivedChartStep`

DerivedChartStep(method: module.models.DerivedChartMethod, parameters: Dict[str, Any] = &lt;factory&gt;)

#### Dataclass fields

- `method: DerivedChartMethod`
- `parameters: Dict`

### class `Diagnostic`

Diagnostic(code: str, severity: module.models.DiagnosticSeverity, message: str, path: str | None = None)

#### Dataclass fields

- `code: str`
- `severity: DiagnosticSeverity`
- `message: str`
- `path: Union`

### class `DiagnosticSeverity` (str, Enum)

### class `EffectiveModelSettings`

EffectiveModelSettings(default_house_system: module.models.HouseSystem | None, default_bodies: List[str], default_aspects: List[str], default_transit_aspects: List[str] | None, default_direction_aspects: List[str] | None, default_transit_bodies: List[str] | None, default_direction_bodies: List[str] | None, aspect_orbs: Dict[str, float], standard_orb: float, engine: module.models.EngineType | None, position_mode: module.models.PositionMode, zodiac_type: module.models.ZodiacType | None, ayanamsa: module.models.Ayanamsa | None, time_system: module.models.TimeSystem | None, degrees_in_circle: float, obliquity_j2000: float, coordinate_tolerance: float, sources: module.models.EffectiveSettingsSources)

#### Dataclass fields

- `default_house_system: Union`
- `default_bodies: List`
- `default_aspects: List`
- `default_transit_aspects: Union`
- `default_direction_aspects: Union`
- `default_transit_bodies: Union`
- `default_direction_bodies: Union`
- `aspect_orbs: Dict`
- `standard_orb: float`
- `engine: Union`
- `position_mode: PositionMode`
- `zodiac_type: Union`
- `ayanamsa: Union`
- `time_system: Union`
- `degrees_in_circle: float`
- `obliquity_j2000: float`
- `coordinate_tolerance: float`
- `sources: EffectiveSettingsSources`

### class `EffectiveSettingsSources`

EffectiveSettingsSources(default_house_system: module.models.SettingSource | None, default_bodies: module.models.SettingSource, default_aspects: module.models.SettingSource, aspect_orbs: Dict[str, module.models.SettingSource], standard_orb: module.models.SettingSource, engine: module.models.SettingSource | None, position_mode: module.models.SettingSource, zodiac_type: module.models.SettingSource | None, ayanamsa: module.models.SettingSource | None, time_system: module.models.SettingSource | None, computational_constants: module.models.SettingSource)

#### Dataclass fields

- `default_house_system: Union`
- `default_bodies: SettingSource`
- `default_aspects: SettingSource`
- `aspect_orbs: Dict`
- `standard_orb: SettingSource`
- `engine: Union`
- `position_mode: SettingSource`
- `zodiac_type: Union`
- `ayanamsa: Union`
- `time_system: Union`
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

Location(name: str, latitude: float, longitude: float, timezone: str, utc_offset: str | None = None, location_mode: str | None = None, timezone_mode: str | None = None)

#### Dataclass fields

- `name: str`
- `latitude: float`
- `longitude: float`
- `timezone: str`
- `utc_offset: Union`
- `location_mode: Union`
- `timezone_mode: Union`

### class `ModelOverrides`

ModelOverrides(points: List[module.models.OverrideEntry] = &lt;factory&gt;, aspects: List[module.models.OverrideEntry] = &lt;factory&gt;, override_orbs: Dict[str, float] = &lt;factory&gt;)

#### Dataclass fields

- `points: List`
- `aspects: List`
- `override_orbs: Dict`

### class `ModelSettings`

ModelSettings(default_house_system: module.models.HouseSystem, position_mode: module.models.PositionMode, default_aspects: List[str], default_bodies: List[str], standard_orb: float, default_transit_aspects: List[str] | None = None, default_direction_aspects: List[str] | None = None, default_transit_bodies: List[str] | None = None, default_direction_bodies: List[str] | None = None, degrees_in_circle: float = 360.0, obliquity_j2000: float = 23.4392911, coordinate_tolerance: float = 0.0001)

#### Dataclass fields

- `default_house_system: HouseSystem`
- `position_mode: PositionMode`
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

OverrideEntry(id: str, glyph: str | None = None, angle: float | None = None, default_orb: float | None = None, only_for: List[str] | None = None, i18n: Dict[str, str] | None = None, computed: bool | None = None, enabled: bool | None = None, valid_contexts: List[module.models.AspectContext] | None = None, interpretation_weight: float | None = None)

#### Dataclass fields

- `id: str`
- `glyph: Union`
- `angle: Union`
- `default_orb: Union`
- `only_for: Union`
- `i18n: Union`
- `computed: Union`
- `enabled: Union`
- `valid_contexts: Union`
- `interpretation_weight: Union`

### class `PositionMode` (str, Enum)

### class `RadixPointColorSettings`

Color settings for radix (natal chart) points/planets.

Maps object IDs to color hex codes. Common objects:
- sun, moon, mercury, venus, mars, jupiter, saturn, uranus, neptune, pluto
- asc, mc, ic, desc (angles)
- north_node, south_node
- lilith, chiron, etc.

#### Dataclass fields

- `colors: Dict`

### class `SettingSource` (str, Enum)

### class `SettingsLayer`

SettingsLayer(house_system: module.models.HouseSystem | None = None, bodies: List[str] | None = None, aspects: List[str] | None = None, aspect_orbs: Dict[str, float] = &lt;factory&gt;, engine: module.models.EngineType | None = None, position_mode: module.models.PositionMode | None = None, zodiac_type: module.models.ZodiacType | None = None, ayanamsa: module.models.Ayanamsa | None = None, time_system: module.models.TimeSystem | None = None, model_overrides: module.models.ModelOverrides | None = None)

#### Dataclass fields

- `house_system: Union`
- `bodies: Union`
- `aspects: Union`
- `aspect_orbs: Dict`
- `engine: Union`
- `position_mode: Union`
- `zodiac_type: Union`
- `ayanamsa: Union`
- `time_system: Union`
- `model_overrides: Union`

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

TransitSeriesCalculation(source_chart_id: str, time_range: Dict[str, str], time_step: str, results: List[module.models.TransitSeriesStep], backend_used: str, fallback_used: bool, ephemeris_source: str | None, warnings: List[str])

#### Dataclass fields

- `source_chart_id: str`
- `time_range: Dict`
- `time_step: str`
- `results: List`
- `backend_used: str`
- `fallback_used: bool`
- `ephemeris_source: Union`
- `warnings: List`

### class `TransitSeriesStep`

TransitSeriesStep(datetime: str, transit_positions: Dict[str, Any], aspects: List[Dict[str, Any]])

#### Dataclass fields

- `datetime: str`
- `transit_positions: Dict`
- `aspects: List`

### class `TransitSetup`

TransitSetup(version: int, source_chart_id: str, transit_type: str, period_mode: str, from_date: str, from_time: str, to_date: str, to_time: str, time_step_seconds: int, transiting_bodies: List[str], transited_bodies: List[str], aspect_types: List[str], house_transitions: bool, sign_transitions: bool, transit_limits: bool, precession_correction: bool, aspect_orbs: Dict[str, float] = &lt;factory&gt;, school: str | None = None, model: str | None = None, model_overrides: module.models.ModelOverrides | None = None, exact_hits: bool = False, station_events: bool = False)

#### Dataclass fields

- `version: int`
- `source_chart_id: str`
- `transit_type: str`
- `period_mode: str`
- `from_date: str`
- `from_time: str`
- `to_date: str`
- `to_time: str`
- `time_step_seconds: int`
- `transiting_bodies: List`
- `transited_bodies: List`
- `aspect_types: List`
- `house_transitions: bool`
- `sign_transitions: bool`
- `transit_limits: bool`
- `precession_correction: bool`
- `aspect_orbs: Dict`
- `school: Union`
- `model: Union`
- `model_overrides: Union`
- `exact_hits: bool`
- `station_events: bool`

### class `ViewLayout`

ViewLayout(name: str, layout_style: module.models.LayoutStyle, chart_instances: List[str], analyses: List[str] = &lt;factory&gt;, modules: List[module.models.ViewModule] = &lt;factory&gt;)

#### Dataclass fields

- `name: str`
- `layout_style: LayoutStyle`
- `chart_instances: List`
- `analyses: List`
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
- `analyses: List`
- `default: WorkspaceDefaults`
- `aspects: List`
- `bodies: List`
- `models: Dict`
- `model_overrides: Union`
- `schema_version: int`
- `active_school: Union`
- `schools: Dict`
- `presentation: WorkspacePresentation`
- `transit_analyses: List`

### class `WorkspaceDefaults`

Aggregated default settings for a workspace (preferred YAML shape).

This mirrors the desired manifest structure under the top-level key 'default'.
Provides workspace-wide defaults that can be overridden at the workspace level.

#### Dataclass fields

- `default_house_system: Union`
- `default_bodies: Union`
- `default_aspects: Union`
- `default_aspect_orbs: Union`
- `default_aspect_colors: Union`
- `ephemeris_engine: Union`
- `position_mode: Union`
- `ephemeris_backend: Union`
- `element_colors: Union`
- `radix_point_colors: Union`
- `default_location: Union`
- `language: Union`
- `theme: Union`
- `time_system: Union`

### class `WorkspaceEntityCounts`

WorkspaceEntityCounts(subjects: int, charts: int, analyses: int, chart_presets: int, transit_analyses: int, layouts: int, annotations: int)

#### Dataclass fields

- `subjects: int`
- `charts: int`
- `analyses: int`
- `chart_presets: int`
- `transit_analyses: int`
- `layouts: int`
- `annotations: int`

### class `WorkspacePresentation`

WorkspacePresentation(theme: str | None = None, language: str | None = None, glyph_set: str | None = None, element_colors: module.models.ElementColorSettings | None = None, radix_point_colors: module.models.RadixPointColorSettings | None = None, aspect_colors: Dict[str, str] | None = None, aspect_line_tier_style: Dict[str, float] | None = None)

#### Dataclass fields

- `theme: Union`
- `language: Union`
- `glyph_set: Union`
- `element_colors: Union`
- `radix_point_colors: Union`
- `aspect_colors: Union`
- `aspect_line_tier_style: Union`

### class `WorkspaceValidationReport`

WorkspaceValidationReport(owner: str, active_model: str | None, valid: bool, counts: module.models.WorkspaceEntityCounts, diagnostics: List[ForwardRef('Diagnostic')])

#### Dataclass fields

- `owner: str`
- `active_model: Union`
- `valid: bool`
- `counts: WorkspaceEntityCounts`
- `diagnostics: List`

### class `ZodiacType` (str, Enum)
