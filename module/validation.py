"""Canonical Python diagnostics matching the Rust validation contract."""

from typing import Iterable, List, Set

try:
    from module.models import (
        AstroModel,
        Diagnostic,
        DiagnosticSeverity,
        EffectiveModelSettings,
    )
except ImportError:
    from models import AstroModel, Diagnostic, DiagnosticSeverity, EffectiveModelSettings


def _normalized(values: Iterable[str]) -> Set[str]:
    return {str(value).strip().lower() for value in values}


def _diagnostic(code: str, message: str, path: str, *, warning: bool = False) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=DiagnosticSeverity.WARNING if warning else DiagnosticSeverity.ERROR,
        message=message,
        path=path,
    )


def validate_model(model: AstroModel, path: str = "model") -> List[Diagnostic]:
    diagnostics: List[Diagnostic] = []
    body_ids: Set[str] = set()
    aspect_ids: Set[str] = set()
    sign_names: Set[str] = set()
    sign_abbreviations: Set[str] = set()

    for index, body in enumerate(model.body_definitions or []):
        item_path = f"{path}.body_definitions[{index}]"
        body_id = str(body.id).strip().lower()
        if not body_id:
            diagnostics.append(_diagnostic("empty_identifier", "body identifier must not be empty", item_path))
        elif body_id in body_ids:
            diagnostics.append(_diagnostic("duplicate_body_id", f"Duplicate body identifier '{body.id}'", item_path))
        body_ids.add(body_id)
        if body.object_type is None:
            diagnostics.append(_diagnostic("body_object_type_missing", f"Body '{body.id}' has no object_type", item_path))
        if not str(body.formula or "").strip():
            diagnostics.append(_diagnostic("body_formula_missing", f"Body '{body.id}' has no formula", item_path, warning=True))
        if not body.computation_map:
            diagnostics.append(_diagnostic("body_computation_map_missing", f"Body '{body.id}' has no engine capability map", item_path))
        elif not any(target is not None and str(target).strip() for target in body.computation_map.values()):
            diagnostics.append(_diagnostic("body_not_computable", f"Body '{body.id}' is unsupported by every declared engine", item_path, warning=True))
        for engine, target in (body.computation_map or {}).items():
            if not str(engine).strip():
                diagnostics.append(_diagnostic("body_engine_id_empty", f"Body '{body.id}' contains an empty engine identifier", item_path))
            if target is not None and not str(target).strip():
                diagnostics.append(_diagnostic("body_engine_target_empty", f"Body '{body.id}' has an empty engine target", item_path))

    for index, aspect in enumerate(model.aspect_definitions or []):
        item_path = f"{path}.aspect_definitions[{index}]"
        aspect_id = str(aspect.id).strip().lower()
        if not aspect_id:
            diagnostics.append(_diagnostic("empty_identifier", "aspect identifier must not be empty", item_path))
        elif aspect_id in aspect_ids:
            diagnostics.append(_diagnostic("duplicate_aspect_id", f"Duplicate aspect identifier '{aspect.id}'", item_path))
        aspect_ids.add(aspect_id)
        if not 0.0 <= float(aspect.angle) <= 360.0:
            diagnostics.append(_diagnostic("invalid_aspect_angle", f"Aspect '{aspect.id}' has invalid angle {aspect.angle}", item_path))
        if float(aspect.default_orb) < 0.0:
            diagnostics.append(_diagnostic("invalid_aspect_orb", f"Aspect '{aspect.id}' has invalid default orb {aspect.default_orb}", item_path))

    for index, sign in enumerate(model.signs or []):
        item_path = f"{path}.signs[{index}]"
        name = str(sign.name).strip().lower()
        abbreviation = str(sign.abbreviation).strip().lower()
        if name in sign_names:
            diagnostics.append(_diagnostic("duplicate_sign_name", f"Duplicate sign name '{sign.name}'", item_path))
        if abbreviation in sign_abbreviations:
            diagnostics.append(_diagnostic("duplicate_sign_abbreviation", f"Duplicate sign abbreviation '{sign.abbreviation}'", item_path))
        sign_names.add(name)
        sign_abbreviations.add(abbreviation)

    settings = model.settings
    if settings is not None:
        _validate_selection(settings.default_bodies, body_ids, "unknown_default_body", f"{path}.settings.default_bodies", diagnostics)
        _validate_selection(settings.default_aspects, aspect_ids, "unknown_default_aspect", f"{path}.settings.default_aspects", diagnostics)
        for values, code, field_name, known in (
            (settings.default_transit_bodies, "unknown_default_transit_body", "default_transit_bodies", body_ids),
            (settings.default_direction_bodies, "unknown_default_direction_body", "default_direction_bodies", body_ids),
            (settings.default_transit_aspects, "unknown_default_transit_aspect", "default_transit_aspects", aspect_ids),
            (settings.default_direction_aspects, "unknown_default_direction_aspect", "default_direction_aspects", aspect_ids),
        ):
            if values is not None:
                _validate_selection(values, known, code, f"{path}.settings.{field_name}", diagnostics)
        if float(settings.degrees_in_circle) <= 0.0:
            diagnostics.append(_diagnostic("invalid_degrees_in_circle", "degrees_in_circle must be greater than zero", f"{path}.settings.degrees_in_circle"))
        if float(settings.coordinate_tolerance) < 0.0:
            diagnostics.append(_diagnostic("invalid_coordinate_tolerance", "coordinate_tolerance must be non-negative", f"{path}.settings.coordinate_tolerance"))

    return diagnostics


def validate_effective_settings(
    model: AstroModel,
    settings: EffectiveModelSettings,
    path: str = "effective_settings",
) -> List[Diagnostic]:
    body_ids = _normalized(body.id for body in model.body_definitions or [])
    aspect_ids = _normalized(aspect.id for aspect in model.aspect_definitions or [])
    diagnostics: List[Diagnostic] = []
    _validate_selection(settings.default_bodies, body_ids, "unknown_selected_body", f"{path}.default_bodies", diagnostics)
    _validate_selection(settings.default_aspects, aspect_ids, "unknown_selected_aspect", f"{path}.default_aspects", diagnostics)
    for aspect_id in settings.aspect_orbs:
        if str(aspect_id).strip().lower() not in aspect_ids:
            diagnostics.append(_diagnostic("unknown_aspect_orb", f"Orb override references unknown aspect '{aspect_id}'", f"{path}.aspect_orbs.{aspect_id}"))
    return diagnostics


def _validate_selection(
    selected: Iterable[str],
    known: Set[str],
    code: str,
    path: str,
    diagnostics: List[Diagnostic],
) -> None:
    seen: Set[str] = set()
    for raw_id in selected or []:
        normalized = str(raw_id).strip().lower()
        if normalized not in known:
            diagnostics.append(_diagnostic(code, f"Selection references unknown identifier '{raw_id}'", path))
        elif normalized in seen:
            diagnostics.append(_diagnostic("duplicate_selection", f"Selection contains duplicate identifier '{raw_id}'", path, warning=True))
        seen.add(normalized)
