"""Layered model/settings resolution matching the Rust precedence contract."""

from copy import deepcopy
from typing import Any, Dict, Optional

try:
    from module.model_catalog import builtin_model_settings, builtin_standard_model
    from module.models import (
        Ayanamsa,
        AstroModel,
        ChartConfig,
        CurrentModelReport,
        Diagnostic,
        DiagnosticSeverity,
        EffectiveModelSettings,
        EffectiveSettingsSources,
        EngineType,
        HouseSystem,
        SettingSource,
        SettingsLayer,
        TimeSystem,
        Workspace,
        ZodiacType,
    )
    from module.validation import validate_effective_settings, validate_model
except ImportError:
    from model_catalog import builtin_model_settings, builtin_standard_model
    from models import (
        Ayanamsa,
        AstroModel,
        ChartConfig,
        CurrentModelReport,
        Diagnostic,
        DiagnosticSeverity,
        EffectiveModelSettings,
        EffectiveSettingsSources,
        EngineType,
        HouseSystem,
        SettingSource,
        SettingsLayer,
        TimeSystem,
        Workspace,
        ZodiacType,
    )
    from validation import validate_effective_settings, validate_model


def settings_layer_from_dict(value: Optional[Dict[str, Any]]) -> Optional[SettingsLayer]:
    if value is None:
        return None

    def pick(*names: str) -> Any:
        for name in names:
            if name in value:
                return value[name]
        return None

    return SettingsLayer(
        house_system=_coerce_enum(pick("houseSystem", "house_system"), HouseSystem),
        bodies=_optional_list(pick("bodies")),
        aspects=_optional_list(pick("aspects")),
        aspect_orbs=dict(pick("aspectOrbs", "aspect_orbs") or {}),
        engine=_coerce_enum(pick("engine"), EngineType),
        zodiac_type=_coerce_enum(pick("zodiacType", "zodiac_type"), ZodiacType),
        ayanamsa=_coerce_enum(pick("ayanamsa"), Ayanamsa),
        time_system=_coerce_enum(pick("timeSystem", "time_system"), TimeSystem),
    )


def settings_layer_from_chart_config(config: ChartConfig) -> SettingsLayer:
    bodies = (
        list(config.observable_objects)
        if config.observable_objects is not None
        else (list(config.included_points) if config.included_points else None)
    )
    return SettingsLayer(
        house_system=config.house_system,
        bodies=bodies,
        aspects=list(config.selected_aspects) if config.selected_aspects is not None else None,
        aspect_orbs=dict(config.aspect_orbs or {}),
        engine=config.engine,
        zodiac_type=config.zodiac_type,
        ayanamsa=config.ayanamsa,
        time_system=config.time_system,
    )


def resolve_preset(ws: Workspace, preset_id: Optional[str]) -> Optional[SettingsLayer]:
    requested = str(preset_id or "").strip()
    if not requested:
        return None
    for preset in ws.chart_presets or []:
        if preset.name == requested:
            return settings_layer_from_chart_config(preset.config)
    raise ValueError(f"Chart preset not found: {requested}")


def standalone_model_report(
    chart_config: ChartConfig,
    operation: Optional[SettingsLayer] = None,
) -> CurrentModelReport:
    requested = str(chart_config.model or "").strip() or None
    model = builtin_standard_model(requested or "standard")
    effective = _effective_settings(None, model, None, chart_config, operation)
    warnings = _compatibility_warnings(chart_config)
    diagnostics = validate_model(model)
    diagnostics.extend(validate_effective_settings(model, effective))
    return CurrentModelReport(
        requested_model=requested,
        resolved_model=model.name,
        source="builtin_standard_model",
        available_models=[],
        model=model,
        effective_settings=effective,
        model_overrides=None,
        warnings=warnings,
        diagnostics=diagnostics,
    )


def current_model_report(
    ws: Workspace,
    chart_config: Optional[ChartConfig] = None,
    preset: Optional[SettingsLayer] = None,
    operation: Optional[SettingsLayer] = None,
) -> CurrentModelReport:
    models = ws.models or {}
    available = sorted(models.keys())
    requested = (
        str(chart_config.model or "").strip()
        if chart_config is not None and chart_config.model
        else str(ws.active_model or "").strip()
    ) or None
    warnings = []
    diagnostics: list[Diagnostic] = []

    if requested and requested in models:
        model = deepcopy(models[requested])
        source = "workspace_model"
    elif available:
        fallback = available[0]
        if requested:
            warnings.extend([f"model_not_found: {requested}", f"using_first_available_model: {fallback}"])
            diagnostics.append(Diagnostic(
                code="model_not_found",
                severity=DiagnosticSeverity.WARNING,
                message=f"Requested model '{requested}' was not found; fallback resolution applied",
                path="chart.config.model",
            ))
        else:
            warnings.append(f"active_model_missing_using_first_available: {fallback}")
        model = deepcopy(models[fallback])
        source = "workspace_model_fallback"
    else:
        model = builtin_standard_model(requested or "standard")
        source = "builtin_standard_model"
        if requested:
            warnings.append(f"model_not_found: {requested}")
            diagnostics.append(Diagnostic(
                code="active_model_not_in_catalog",
                severity=DiagnosticSeverity.WARNING,
                message=f"Active model '{requested}' is not present in the workspace model catalog",
                path="workspace.active_model",
            ))
        warnings.append("using_builtin_standard_model")

    model = _merge_model_overrides(model, ws.model_overrides)
    effective = _effective_settings(ws, model, preset, chart_config, operation)
    warnings.extend(_compatibility_warnings(chart_config))
    diagnostics.extend(validate_model(model))
    diagnostics.extend(validate_effective_settings(model, effective))
    return CurrentModelReport(
        requested_model=requested,
        resolved_model=model.name,
        source=source,
        available_models=available,
        model=model,
        effective_settings=effective,
        model_overrides=ws.model_overrides,
        warnings=warnings,
        diagnostics=diagnostics,
    )


def materialize_effective_settings(chart: Any, settings: EffectiveModelSettings) -> Any:
    resolved = deepcopy(chart)
    config = resolved.config
    config.house_system = settings.default_house_system
    config.observable_objects = list(settings.default_bodies)
    config.selected_aspects = list(settings.default_aspects)
    config.aspect_orbs = dict(settings.aspect_orbs)
    config.engine = settings.engine
    if settings.zodiac_type is not None:
        config.zodiac_type = settings.zodiac_type
    config.ayanamsa = settings.ayanamsa
    config.time_system = settings.time_system
    return resolved


def _effective_settings(
    ws: Optional[Workspace],
    model: AstroModel,
    preset: Optional[SettingsLayer],
    chart: Optional[ChartConfig],
    operation: Optional[SettingsLayer],
) -> EffectiveModelSettings:
    baseline = builtin_model_settings()
    model_settings = model.settings or baseline
    settings_source = SettingSource.MODEL if model.settings is not None else SettingSource.APPLICATION

    house = model_settings.default_house_system
    house_source = settings_source if house is not None else None
    bodies = list(model_settings.default_bodies or [])
    bodies_source = settings_source
    aspects = list(model_settings.default_aspects or [])
    aspects_source = settings_source
    engine = model.engine
    engine_source = SettingSource.MODEL if engine is not None else None
    zodiac = model.zodiac_type
    zodiac_source = SettingSource.MODEL if zodiac is not None else None
    ayanamsa = model.ayanamsa
    ayanamsa_source = SettingSource.MODEL if ayanamsa is not None else None
    time_system = None
    time_source = None
    aspect_orbs = {aspect.id: float(aspect.default_orb) for aspect in model.aspect_definitions or []}
    orb_sources = {aspect_id: SettingSource.MODEL for aspect_id in aspect_orbs}

    if ws is not None:
        defaults = ws.default
        if defaults.default_house_system is not None:
            house, house_source = defaults.default_house_system, SettingSource.WORKSPACE
        if defaults.default_bodies is not None:
            bodies, bodies_source = list(defaults.default_bodies), SettingSource.WORKSPACE
        if ws.bodies:
            bodies, bodies_source = list(ws.bodies), SettingSource.WORKSPACE
        if defaults.default_aspects is not None:
            aspects, aspects_source = list(defaults.default_aspects), SettingSource.WORKSPACE
        if ws.aspects:
            aspects, aspects_source = list(ws.aspects), SettingSource.WORKSPACE
        for aspect_id, orb in (defaults.default_aspect_orbs or {}).items():
            aspect_orbs[aspect_id] = float(orb)
            orb_sources[aspect_id] = SettingSource.WORKSPACE
        if defaults.ephemeris_engine is not None:
            engine, engine_source = defaults.ephemeris_engine, SettingSource.WORKSPACE
        if defaults.time_system is not None:
            time_system, time_source = defaults.time_system, SettingSource.WORKSPACE

    state = {
        "house": house, "house_source": house_source,
        "bodies": bodies, "bodies_source": bodies_source,
        "aspects": aspects, "aspects_source": aspects_source,
        "engine": engine, "engine_source": engine_source,
        "zodiac": zodiac, "zodiac_source": zodiac_source,
        "ayanamsa": ayanamsa, "ayanamsa_source": ayanamsa_source,
        "time_system": time_system, "time_source": time_source,
    }
    if preset is not None:
        _apply_layer(state, aspect_orbs, orb_sources, preset, SettingSource.PRESET)
    if chart is not None:
        chart_layer = settings_layer_from_chart_config(chart)
        _apply_layer(state, aspect_orbs, orb_sources, chart_layer, SettingSource.CHART)
    if operation is not None:
        _apply_layer(state, aspect_orbs, orb_sources, operation, SettingSource.OPERATION)

    return EffectiveModelSettings(
        default_house_system=state["house"],
        default_bodies=state["bodies"],
        default_aspects=state["aspects"],
        default_transit_aspects=deepcopy(model_settings.default_transit_aspects),
        default_direction_aspects=deepcopy(model_settings.default_direction_aspects),
        default_transit_bodies=deepcopy(model_settings.default_transit_bodies),
        default_direction_bodies=deepcopy(model_settings.default_direction_bodies),
        aspect_orbs=aspect_orbs,
        standard_orb=float(model_settings.standard_orb),
        engine=state["engine"],
        zodiac_type=state["zodiac"],
        ayanamsa=state["ayanamsa"],
        time_system=state["time_system"],
        degrees_in_circle=float(model_settings.degrees_in_circle),
        obliquity_j2000=float(model_settings.obliquity_j2000),
        coordinate_tolerance=float(model_settings.coordinate_tolerance),
        sources=EffectiveSettingsSources(
            default_house_system=state["house_source"],
            default_bodies=state["bodies_source"],
            default_aspects=state["aspects_source"],
            aspect_orbs=orb_sources,
            standard_orb=settings_source,
            engine=state["engine_source"],
            zodiac_type=state["zodiac_source"],
            ayanamsa=state["ayanamsa_source"],
            time_system=state["time_source"],
            computational_constants=settings_source,
        ),
    )


def _merge_model_overrides(model: AstroModel, overrides: Any) -> AstroModel:
    merged = deepcopy(model)
    if overrides is None:
        return merged
    for entry in overrides.points or []:
        body = next((candidate for candidate in merged.body_definitions if candidate.id == entry.id), None)
        if body is None:
            continue
        # Frozen dataclasses require replacement through object.__setattr__.
        if entry.glyph is not None:
            object.__setattr__(body, "glyph", entry.glyph)
        if entry.i18n is not None:
            object.__setattr__(body, "i18n", dict(entry.i18n))
    for entry in overrides.aspects or []:
        aspect = next((candidate for candidate in merged.aspect_definitions if candidate.id == entry.id), None)
        if aspect is None:
            continue
        for name in ("glyph", "angle", "default_orb", "i18n"):
            value = getattr(entry, name)
            if value is not None:
                object.__setattr__(aspect, name, deepcopy(value))
    for aspect in merged.aspect_definitions:
        if aspect.id in (overrides.override_orbs or {}):
            object.__setattr__(
                aspect,
                "default_orb",
                float(overrides.override_orbs[aspect.id]),
            )
    return merged


def _apply_layer(
    state: Dict[str, Any],
    aspect_orbs: Dict[str, float],
    orb_sources: Dict[str, SettingSource],
    layer: SettingsLayer,
    source: SettingSource,
) -> None:
    for field_name, state_name in (
        ("house_system", "house"),
        ("bodies", "bodies"),
        ("aspects", "aspects"),
        ("engine", "engine"),
        ("zodiac_type", "zodiac"),
        ("ayanamsa", "ayanamsa"),
        ("time_system", "time_system"),
    ):
        value = getattr(layer, field_name)
        if value is not None:
            state[state_name] = list(value) if isinstance(value, list) else value
            state[f"{state_name}_source"] = source
    for aspect_id, orb in layer.aspect_orbs.items():
        aspect_orbs[aspect_id] = float(orb)
        orb_sources[aspect_id] = source


def _compatibility_warnings(chart: Optional[ChartConfig]) -> list[str]:
    if chart is not None and chart.observable_objects is None and chart.included_points:
        return ["included_points_deprecated: use observable_objects"]
    return []


def _optional_list(value: Any) -> Optional[list[str]]:
    if value is None:
        return None
    return [str(item) for item in value]


def _coerce_enum(value: Any, enum_type: Any) -> Any:
    if value is None or isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)
    except (ValueError, TypeError):
        try:
            return enum_type[str(value).strip().upper()]
        except (KeyError, TypeError):
            raise ValueError(f"Invalid {enum_type.__name__}: {value}")
