from pathlib import Path
from datetime import datetime, date, time
from typing import Union, Optional, List, Dict, Iterator, Callable, Tuple, Any
from dataclasses import asdict, is_dataclass
try:
    from module.models import (
        Workspace, ChartPreset, ChartSubject,
        ChartInstance, ViewLayout, Annotation, ChartConfig, Location, HouseSystem, EngineType, WorkspaceDefaults,
        BodyDefinition, ObjectType, AspectDefinition, AstroModel
    )
except ImportError:
    from models import (
        Workspace, ChartPreset, ChartSubject,
        ChartInstance, ViewLayout, Annotation, ChartConfig, Location, HouseSystem, EngineType, WorkspaceDefaults,
        BodyDefinition, ObjectType, AspectDefinition, AstroModel
    )
try:
    from module.utils import (
        read_yaml_file,
        write_yaml_file,
        write_json_file,
        resolve_under_base,
        resolve_user_path,
        _to_primitive,
        load_sfs_models_from_dir,
        parse_sfs_content,
        export_workspace_yaml,
    )
except ImportError:
    from utils import (
        read_yaml_file,
        write_yaml_file,
        write_json_file,
        resolve_under_base,
        resolve_user_path,
        _to_primitive,
        load_sfs_models_from_dir,
        parse_sfs_content,
        export_workspace_yaml,
    )

try:
    from module.services import get_active_model
except ImportError:
    from services import get_active_model

# ─────────────────────
# ⚙️ CONFIGURATION
# ─────────────────────

# Default location
DEFAULT_LOCATION = {
    "name": "Prague",
    "latitude": 50.0875,
    "longitude": 14.4214,
    "timezone": "Europe/Prague"
}

# ──────────────────────────────
# PUBLIC API
# ──────────────────────────────

def load_workspace(workspace_path: str) -> Workspace:
    """Load a modular workspace from a manifest YAML file.
    
    Args:
        workspace_path: Absolute or relative path to `workspace.yaml`.
        
    Returns:
        Workspace dataclass assembled from the manifest and referenced parts.
        
    Raises:
        FileNotFoundError: If workspace file does not exist
        
    Note:
        Paths referenced in the manifest (e.g., `charts/*.yml`) are resolved
        relative to the manifest directory and validated for containment.
    """
    if not Path(workspace_path).exists():
        raise FileNotFoundError(f"Workspace file not found: {workspace_path}")

    base_dir = str(Path(workspace_path).parent)

    manifest = read_yaml_file(workspace_path)

    return _load_workspace_from_manifest(manifest, base_dir)


def save_workspace_flat(workspace: Workspace, path: str, format: str = "yaml") -> None:
    """Save the entire Workspace as a single flat file (debug/export use).
    
    Args:
        workspace: Workspace instance to serialize
        path: Destination file path (YAML or JSON)
        format: "yaml" or "json", defaults to "yaml"
        
    Raises:
        ValueError: If format is not "yaml" or "json"
    """
    data = asdict(workspace)

    if format == "yaml":
        write_yaml_file(path, data, sort_keys=False, allow_unicode=True)
    elif format == "json":
        write_json_file(path, data, indent=2)
    else:
        raise ValueError("Unsupported format: choose 'yaml' or 'json'")


# ──────────────────────────────
# MODULAR LOADER
# ──────────────────────────────

def _safe_engine(val: Any) -> Optional[EngineType]:
    """Safely convert a string/enum value to EngineType or return None.
    
    Args:
        val: EngineType instance, string value (e.g., "jpl"), string name (e.g., "JPL"), or None
        
    Returns:
        EngineType instance if conversion successful, None otherwise
    """
    try:
        if val is None:
            return None
        if isinstance(val, EngineType):
            return val
        s = str(val).strip()
        if not s:
            return None
        # Try by value first (lowercase values like 'jpl')
        try:
            return EngineType(s.lower())
        except Exception:
            pass
        # Then by enum name (uppercase like 'JPL')
        return getattr(EngineType, s.upper(), None)
    except Exception:
        return None


def _load_yaml_file(base_dir: str, path: str) -> dict:
    """Load a YAML file relative to base_dir.
    
    Args:
        base_dir: Base directory for resolving relative paths
        path: Relative path to YAML file
        
    Returns:
        Parsed YAML content as dictionary
        
    Raises:
        ValueError: If path traversal is detected or path is absolute
    """
    full_path = resolve_under_base(base_dir, path)
    return read_yaml_file(full_path)


def _load_many_items(base_dir: str, items: list, cls: type) -> List:
    """Load multiple items from YAML files or dicts.
    
    Args:
        base_dir: Base directory for resolving relative paths
        items: List of file paths (str) or dict objects
        cls: Dataclass class to instantiate items as
        
    Returns:
        List of instantiated objects of type cls
    """
    out = []
    for it in (items or []):
        try:
            if isinstance(it, str):
                data = _load_yaml_file(base_dir, it)
            elif isinstance(it, dict):
                data = it
            else:
                continue
            if isinstance(data, dict):
                out.append(cls(**data))
        except Exception:
            # skip malformed entries
            continue
    return out


def _load_chart_presets(base_dir: str, manifest: dict) -> List[ChartPreset]:
    """Load chart presets from manifest.
    
    Args:
        base_dir: Base directory for resolving relative paths
        manifest: Workspace manifest dictionary
        
    Returns:
        List of ChartPreset objects loaded from manifest
    """
    chart_presets = []
    for p in manifest.get("chart_presets", []) or []:
        try:
            data = _load_yaml_file(base_dir, p) if isinstance(p, str) else (p if isinstance(p, dict) else None)
            if not isinstance(data, dict):
                continue
            cfg = data.get("config")
            if isinstance(cfg, dict):
                data["config"] = ChartConfig(**cfg)
            chart_presets.append(ChartPreset(**data))
        except Exception:
            continue
    return chart_presets


def _load_charts(base_dir: str, manifest: dict) -> List[ChartInstance]:
    """Load charts from manifest.
    
    Args:
        base_dir: Base directory for resolving relative paths
        manifest: Workspace manifest dictionary
        
    Returns:
        List of ChartInstance objects loaded from manifest
    """
    charts = []
    for p in manifest.get("charts", []) or []:
        try:
            data = _load_yaml_file(base_dir, p) if isinstance(p, str) else (p if isinstance(p, dict) else None)
            if not isinstance(data, dict):
                continue
            subj = data.get("subject")
            cfg = data.get("config")
            if isinstance(subj, dict):
                data["subject"] = ChartSubject(**subj)
            if isinstance(cfg, dict):
                data["config"] = ChartConfig(**cfg)
            # Ignore computed_chart on load if present (recomputable)
            data.pop("computed_chart", None)
            charts.append(ChartInstance(**data))
        except Exception:
            continue
    return charts


def _load_annotations(base_dir: str, manifest: dict) -> List[Annotation]:
    """Load annotations from manifest.
    
    Args:
        base_dir: Base directory for resolving relative paths
        manifest: Workspace manifest dictionary
        
    Returns:
        List of Annotation objects loaded from manifest
    """
    annotations = []
    for ann in manifest.get("annotations", []) or []:
        try:
            if isinstance(ann, str):
                full_path = resolve_under_base(base_dir, ann)
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                annotations.append(Annotation(
                    title=Path(ann).stem,
                    content=content,
                    created=None,
                    author="unknown"
                ))
            elif isinstance(ann, dict):
                # Expect keys: title, content, author, created (optional)
                annotations.append(Annotation(
                    title=ann.get("title", "note"),
                    content=ann.get("content", ""),
                    created=None,
                    author=ann.get("author", "unknown")
                ))
        except Exception:
            continue
    return annotations


def _parse_workspace_defaults(manifest: dict) -> WorkspaceDefaults:
    """Parse WorkspaceDefaults from manifest.
    
    Args:
        manifest: Workspace manifest dictionary
        
    Returns:
        WorkspaceDefaults instance with ephemeris, location, and other defaults
    """
    raw_default = manifest.get('default')
    default_block = raw_default if isinstance(raw_default, dict) else {}
    
    # Handle legacy top-level default_ephemeris for backward compatibility
    ephemeris_engine = default_block.get('ephemeris_engine')
    ephemeris_backend = default_block.get('ephemeris_backend')
    
    if not ephemeris_engine or not ephemeris_backend:
        # Try to get from legacy default_ephemeris field
        de = manifest.get("default_ephemeris")
        if isinstance(de, dict):
            if not ephemeris_backend:
                ephemeris_backend = de.get("name", "")
            if not ephemeris_engine:
                ephemeris_engine = de.get("backend", "")
        elif isinstance(de, str) and not ephemeris_engine:
            ephemeris_engine = de
    
    # Parse location if present
    default_location = None
    loc_name = default_block.get('location_name')
    loc_lat = default_block.get('location_latitude')
    loc_lon = default_block.get('location_longitude')
    loc_tz = default_block.get('timezone')
    
    if loc_name and loc_lat is not None and loc_lon is not None and loc_tz:
        default_location = Location(
            name=loc_name,
            latitude=loc_lat,
            longitude=loc_lon,
            timezone=loc_tz
        )
    
    return WorkspaceDefaults(
        ephemeris_engine=_safe_engine(ephemeris_engine),
        ephemeris_backend=ephemeris_backend,
        default_location=default_location,
        language=default_block.get('language'),
        theme=default_block.get('theme'),
        default_house_system=None,  # Will be set from model if needed
        default_bodies=default_block.get('default_bodies'),
        default_aspects=default_block.get('default_aspects'),
        element_colors=default_block.get('element_colors'),
        radix_point_colors=default_block.get('radix_point_colors'),
        time_system=default_block.get('time_system'),
    )


def _load_workspace_from_manifest(manifest: dict, base_dir: str) -> Workspace:
    """Assemble a Workspace from a parsed manifest dict and base directory.
    
    This resolves referenced YAML files (subjects, charts, layouts, presets,
    annotations) relative to `base_dir` while validating paths.
    """
    # Parse model settings
    active_model = manifest.get("active_model")

    # Load all workspace components
    chart_presets = _load_chart_presets(base_dir, manifest)
    subjects = _load_many_items(base_dir, manifest.get("subjects", []), ChartSubject)
    charts = _load_charts(base_dir, manifest)
    layouts = _load_many_items(base_dir, manifest.get("layouts", []), ViewLayout)
    annotations = _load_annotations(base_dir, manifest)

    # Parse aspects
    raw_aspects = manifest.get('aspects')
    if isinstance(raw_aspects, list):
        aspects = list(raw_aspects)
    else:
        # fallback to legacy key if present, else empty list
        aspects = list(manifest.get('default_aspects') or [])

    # Parse workspace defaults (includes ephemeris settings)
    ws_defaults = _parse_workspace_defaults(manifest)

    ws = Workspace(
        owner=manifest.get('owner', ''),
        active_model=active_model,
        chart_presets=chart_presets,
        subjects=subjects,
        charts=charts,
        layouts=layouts,
        annotations=annotations,
        model_overrides=None,
        aspects=aspects or [],
        default=ws_defaults,
    )
    return ws


# ─────────────────────
# 🔭 OBSERVABLE OBJECTS MANAGEMENT
# ─────────────────────
# Note: Custom objects and aspects are now loaded from YAML workspace/model files only.
# SQLite-based functions have been removed from core workspace logic.
# If you need SQLite-based storage, implement it in your UI module (see ui_translations.py).


def get_default_observable_objects() -> Dict[str, BodyDefinition]:
    """Get default observable object definitions.
    
    Returns:
        Dictionary mapping object_id -> BodyDefinition for standard objects
        (planets, angles, lunar nodes, calculated points) that are commonly
        available in kerykeion and can be computed.
    """
    defaults = {}
    
    # Standard planets (available in both JPL and kerykeion)
    planets = [
        ("sun", "☉", "Planet", ObjectType.PLANET, {"jpl": "sun", "swisseph": "sun"}),
        ("moon", "☽", "Planet", ObjectType.PLANET, {"jpl": "moon", "swisseph": "moon"}),
        ("mercury", "☿", "Planet", ObjectType.PLANET, {"jpl": "mercury", "swisseph": "mercury"}),
        ("venus", "♀", "Planet", ObjectType.PLANET, {"jpl": "venus", "swisseph": "venus"}),
        ("mars", "♂", "Planet", ObjectType.PLANET, {"jpl": "mars", "swisseph": "mars"}),
        ("jupiter", "♃", "Planet", ObjectType.PLANET, {"jpl": "jupiter", "swisseph": "jupiter"}),
        ("saturn", "♄", "Planet", ObjectType.PLANET, {"jpl": "saturn", "swisseph": "saturn"}),
        ("uranus", "♅", "Planet", ObjectType.PLANET, {"jpl": "uranus", "swisseph": "uranus"}),
        ("neptune", "♆", "Planet", ObjectType.PLANET, {"jpl": "neptune", "swisseph": "neptune"}),
        ("pluto", "♇", "Planet", ObjectType.PLANET, {"jpl": "pluto", "swisseph": "pluto"}),
    ]
    
    # Angles (kerykeion only, requires location)
    angles = [
        ("asc", "Asc", "Angle", ObjectType.ANGLE, {"swisseph": "asc"}, True, False),
        ("mc", "MC", "Angle", ObjectType.ANGLE, {"swisseph": "mc"}, True, True),
        ("ic", "IC", "Angle", ObjectType.ANGLE, {"swisseph": "ic"}, True, True),
        ("desc", "Desc", "Angle", ObjectType.ANGLE, {"swisseph": "desc"}, True, False),
    ]
    
    # Lunar nodes (kerykeion)
    nodes = [
        ("north_node", "☊", "Lunar Node", ObjectType.LUNAR_NODE, {"swisseph": "north_node"}),
        ("south_node", "☋", "Lunar Node", ObjectType.LUNAR_NODE, {"swisseph": "south_node"}),
    ]
    
    # Calculated points (kerykeion)
    calculated = [
        ("lilith", "⚸", "Calculated Point", ObjectType.CALCULATED_POINT, {"swisseph": "lilith"}),
        ("chiron", "⚷", "Asteroid", ObjectType.ASTEROID, {"swisseph": "chiron"}),
    ]
    
    for planet_data in planets:
        obj_id, glyph, element, obj_type, comp_map = planet_data
        defaults[obj_id] = BodyDefinition(
            id=obj_id,
            glyph=glyph,
            formula=obj_id,
            element=element,
            avg_speed=0.0,
            max_orb=0.0,
            i18n={"Caption": obj_id.capitalize()},
            object_type=obj_type,
            computation_map=comp_map,
            requires_location=False,
            requires_house_system=False,
        )
    
    for angle_data in angles:
        obj_id, glyph, element, obj_type, comp_map, req_loc, req_house = angle_data
        defaults[obj_id] = BodyDefinition(
            id=obj_id,
            glyph=glyph,
            formula=obj_id,
            element=element,
            avg_speed=0.0,
            max_orb=0.0,
            i18n={"Caption": obj_id.upper()},
            object_type=obj_type,
            computation_map=comp_map,
            requires_location=req_loc,
            requires_house_system=req_house,
        )
    
    for calc_data in nodes + calculated:
        obj_id, glyph, element, obj_type, comp_map = calc_data
        defaults[obj_id] = BodyDefinition(
            id=obj_id,
            glyph=glyph,
            formula=obj_id,
            element=element,
            avg_speed=0.0,
            max_orb=0.0,
            i18n={"Caption": obj_id.replace("_", " ").title()},
            object_type=obj_type,
            computation_map=comp_map,
            requires_location=False,
            requires_house_system=False,
        )
    
    return defaults


def get_all_observable_objects(ws: Optional['Workspace'] = None, model: Optional[AstroModel] = None) -> Dict[str, BodyDefinition]:
    """Get all observable objects (defaults + custom from workspace/model YAML).
    
    Args:
        ws: Optional Workspace to load custom objects from
        model: Optional AstroModel to get body definitions from
        
    Returns:
        Dictionary mapping object_id -> BodyDefinition. Custom objects from
        workspace/model override defaults with the same id.
    """
    all_objects = get_default_observable_objects()
    
    # Load custom objects from model (YAML-based)
    if model and hasattr(model, 'body_definitions'):
        for obj in model.body_definitions:
            all_objects[obj.id] = obj
    
    # Load custom objects from workspace model_overrides if present
    if ws and hasattr(ws, 'model_overrides') and ws.model_overrides:
        if hasattr(ws.model_overrides, 'body_definitions'):
            for obj in ws.model_overrides.body_definitions:
                all_objects[obj.id] = obj
    
    return all_objects


# ─────────────────────
# 🔺 ASPECT DEFINITIONS MANAGEMENT
# ─────────────────────
# Note: Custom aspects are now loaded from YAML workspace/model files only.
# SQLite-based functions have been removed from core workspace logic.


def get_default_aspect_definitions() -> Dict[str, AspectDefinition]:
    """Get default aspect definitions.
    
    Returns:
        Dictionary mapping aspect_id -> AspectDefinition for standard aspects
        (conjunction, opposition, trine, square, sextile, etc.)
    """
    defaults: Dict[str, AspectDefinition] = {}
    aspects_path = Path(__file__).with_name("default_aspects.yaml")
    aspects_data = None
    if aspects_path.exists():
        try:
            aspects_data = read_yaml_file(aspects_path)
        except (OSError, ValueError):
            aspects_data = None
    if isinstance(aspects_data, list):
        for item in aspects_data:
            if not isinstance(item, dict):
                continue
            asp_id = item.get("id")
            if not asp_id:
                continue
            defaults[asp_id] = AspectDefinition(
                id=asp_id,
                glyph=item.get("glyph", ""),
                angle=float(item.get("angle", 0.0)),
                default_orb=float(item.get("default_orb", 0.0)),
                i18n={"Caption": asp_id.replace("_", " ").title()},
                color=item.get("color"),
                importance=int(item.get("importance", 0)),
                line_style=item.get("line_style"),
                line_width=float(item.get("line_width", 1.0)),
                show_label=bool(item.get("show_label", False)),
            )
    return defaults


def get_all_aspect_definitions(ws: Optional['Workspace'] = None, model: Optional[AstroModel] = None) -> Dict[str, AspectDefinition]:
    """Get all aspect definitions (defaults + custom from workspace/model YAML).
    
    Args:
        ws: Optional Workspace to load custom aspects from
        model: Optional AstroModel to get aspect definitions from
        
    Returns:
        Dictionary mapping aspect_id -> AspectDefinition. Custom aspects from
        workspace/model override defaults with the same id.
    """
    all_aspects = get_default_aspect_definitions()
    
    # Load custom aspects from model (YAML-based)
    if model and hasattr(model, 'aspect_definitions'):
        for asp in model.aspect_definitions:
            all_aspects[asp.id] = asp
    
    # Load custom aspects from workspace model_overrides if present
    if ws and hasattr(ws, 'model_overrides') and ws.model_overrides:
        if hasattr(ws.model_overrides, 'aspect_definitions'):
            for asp in ws.model_overrides.aspect_definitions:
                all_aspects[asp.id] = asp
    
    return all_aspects


# ──────────────────────────────
# WORKSPACE SCAFFOLDING & MODULAR CRUD
# ──────────────────────────────

def _ensure_dir(p: Path) -> None:
    """Ensure directory exists, creating parent directories if needed."""
    p.mkdir(parents=True, exist_ok=True)


def _safe_filename(name: str) -> str:
    """Sanitize a string for use as a filename.
    
    Converts to lowercase, keeps alphanumeric characters, dashes, and underscores.
    Replaces spaces and other characters with dashes.
    
    Args:
        name: String to sanitize
        
    Returns:
        Sanitized filename-safe string, defaults to "item" if empty
    """
    base = "".join(ch.lower() if ch.isalnum() else ("-" if ch in " -_" else "") for ch in (name or ""))
    return base.strip("-") or "item"


def _dump_yaml(path: Path, data: dict) -> None:
    """Write data to YAML file after converting to primitives.
    
    Args:
        path: Destination file path
        data: Dictionary to write (will be converted to primitives)
    """
    write_yaml_file(path, _to_primitive(data), sort_keys=False, allow_unicode=True)


def _serialize(obj: Any) -> Any:
    """Serialize an object to primitives using utils._to_primitive.
    
    Args:
        obj: Object to serialize
        
    Returns:
        Primitive representation of the object
    """
    return _to_primitive(obj)


def init_workspace(base_dir: Union[str, Path], owner: str, active_model: str, default_ephemeris: Dict[str, str]) -> Path:
    """Initialize a new workspace directory structure and manifest.
    
    Creates subfolders `subjects/`, `charts/`, `layouts/`, `annotations/`, `presets/`
    and a `workspace.yaml` manifest that references none by default.
    
    Returns:
    - Absolute path to the created `workspace.yaml` file.
    """
    # Validate and resolve base directory to prevent path traversal
    base = resolve_user_path(base_dir, base_dir=Path.cwd())
    _ensure_dir(base)
    # subdirs
    subjects_dir = base / "subjects"
    charts_dir = base / "charts"
    layouts_dir = base / "layouts"
    annotations_dir = base / "annotations"
    presets_dir = base / "presets"
    for d in (subjects_dir, charts_dir, layouts_dir, annotations_dir, presets_dir):
        _ensure_dir(d)
    
    # Note: Database initialization removed - custom objects/aspects are YAML-based
    manifest = {
        "owner": owner,
        "active_model": active_model,
        "aspects": [],
        "default": {
            # Ephemeris settings
            "ephemeris_engine": (default_ephemeris.get("backend") or "swisseph"),
            "ephemeris_backend": default_ephemeris.get("name"),
            # Location settings
            "location_name": (DEFAULT_LOCATION.get("name") if isinstance(DEFAULT_LOCATION, dict) else None),
            "location_latitude": (DEFAULT_LOCATION.get("latitude") if isinstance(DEFAULT_LOCATION, dict) else None),
            "location_longitude": (DEFAULT_LOCATION.get("longitude") if isinstance(DEFAULT_LOCATION, dict) else None),
            "timezone": (DEFAULT_LOCATION.get("timezone") if isinstance(DEFAULT_LOCATION, dict) else None),
            # Other settings
            "language": "cs",  # Default language (UI-specific, see ui_translations.py)
            "theme": "default",
            "default_house_system": None,
            "default_bodies": None,
            "default_aspects": None,
        },
        # modular refs
        "chart_presets": [],
        "subjects": [],
        "charts": [],
        "layouts": [],
        "annotations": [],
    }
    manifest_path = base / "workspace.yaml"
    write_yaml_file(manifest_path, manifest, sort_keys=False, allow_unicode=True)
    return manifest_path


def _save_workspace_items(base: Path, items: List, subdir: str, get_name_func) -> List[str]:
    """Save workspace items to YAML files and return relative references.
    
    Args:
        base: Base directory path
        items: List of items to save
        subdir: Subdirectory name (e.g., "presets", "charts")
        get_name_func: Function to get name/id from item for filename
        
    Returns:
        List of relative file paths
    """
    refs = []
    for item in (items or []):
        name = get_name_func(item)
        ref = f"{subdir}/{_safe_filename(name)}.yml"
        _dump_yaml(base / ref, _serialize(item))
        refs.append(ref)
    return refs


def _build_default_block(workspace: Workspace) -> dict:
    """Build the default block for workspace manifest.
    
    Args:
        workspace: Workspace instance to extract defaults from
        
    Returns:
        Dictionary containing default settings for ephemeris, location, language, theme, etc.
    """
    d = workspace.default
    
    # Serialize location if present, otherwise use fallback defaults
    if d.default_location:
        location_name = d.default_location.name
        location_latitude = d.default_location.latitude
        location_longitude = d.default_location.longitude
        timezone = d.default_location.timezone
    else:
        location_name = DEFAULT_LOCATION.get("name") if isinstance(DEFAULT_LOCATION, dict) else None
        location_latitude = DEFAULT_LOCATION.get("latitude") if isinstance(DEFAULT_LOCATION, dict) else None
        location_longitude = DEFAULT_LOCATION.get("longitude") if isinstance(DEFAULT_LOCATION, dict) else None
        timezone = DEFAULT_LOCATION.get("timezone") if isinstance(DEFAULT_LOCATION, dict) else None
    
    return {
        "ephemeris_engine": (getattr(d.ephemeris_engine, 'value', d.ephemeris_engine) if d.ephemeris_engine else None),
        "ephemeris_backend": d.ephemeris_backend,
        "location_name": location_name,
        "location_latitude": location_latitude,
        "location_longitude": location_longitude,
        "timezone": timezone,
        "language": (d.language if d.language is not None else "cs"),  # Default language (UI-specific)
        "theme": (d.theme if d.theme is not None else "default"),
        "default_house_system": (getattr(d.default_house_system, 'value', d.default_house_system) if d.default_house_system else None),
        "default_bodies": (d.default_bodies if d.default_bodies else None),
        "default_aspects": (d.default_aspects if d.default_aspects else None),
    }


def save_workspace_modular(workspace: Workspace, base_dir: Union[str, Path]) -> Path:
    """Persist a Workspace into modular YAML files and update `workspace.yaml`.
    
    Serializes presets, subjects, charts, layouts, and annotations into their
    respective subdirectories under `base_dir`. Writes/overwrites the manifest
    with relative references.
    
    Returns:
    - Absolute path to the updated `workspace.yaml`.
    """
    base = Path(base_dir)
    # Ensure all subdirectories exist
    for subdir in ("subjects", "charts", "layouts", "annotations", "presets"):
        _ensure_dir(base / subdir)

    # Save all workspace components
    preset_refs = _save_workspace_items(base, workspace.chart_presets, "presets", lambda p: p.name)
    subj_refs = _save_workspace_items(base, workspace.subjects, "subjects", 
                                      lambda s: getattr(s, 'id', getattr(s, 'name', 'subject')))
    chart_refs = _save_workspace_items(base, workspace.charts, "charts",
                                       lambda c: getattr(c, 'id', getattr(getattr(c, 'subject', None), 'name', 'chart')))
    layout_refs = _save_workspace_items(base, workspace.layouts, "layouts",
                                        lambda l: getattr(l, 'name', 'layout'))
    annotation_refs = _save_workspace_items(base, workspace.annotations, "annotations",
                                            lambda a: getattr(a, 'title', 'note'))

    # Build manifest
    default_block = _build_default_block(workspace)
    
    # Get active model
    active_model = getattr(workspace, 'active_model', None)
    
    manifest = {
        "owner": workspace.owner,
        "active_model": active_model,
        "aspects": list(getattr(workspace, 'aspects', []) or []),
        "default": default_block,
        # modular refs
        "chart_presets": preset_refs,
        "subjects": subj_refs,
        "charts": chart_refs,
        "layouts": layout_refs,
        "annotations": annotation_refs,
    }

    manifest_path = base / "workspace.yaml"
    write_yaml_file(manifest_path, manifest, sort_keys=False, allow_unicode=True)
    return manifest_path


# ──────────────────────────────
# MODULAR CRUD HELPERS (PUBLIC)
# ──────────────────────────────

def _prune_chart_yaml_payload(data: dict) -> dict:
    """Remove empty/default fields from a chart dict before YAML dump.
    
    Args:
        data: Chart dictionary to prune
        
    Returns:
        Pruned dictionary with empty/default fields removed
        
    Note:
        Drops 'computed_chart', and in 'config' drops any keys with None/empty values
        (e.g., 'model', 'engine', 'ayanamsa', 'color_theme'). Note that 'override_ephemeris'
        is a valid field and will be persisted if set. Also drops top-level keys explicitly
        listed as undesired when empty.
    """
    if not isinstance(data, dict):
        return data
    # Drop computed
    data.pop('computed_chart', None)
    cfg = data.get('config')
    if isinstance(cfg, dict):
        # Remove null/empty values in known optional fields
        # Note: override_ephemeris is a valid field and should be persisted if set
        for k in list(cfg.keys()):
            v = cfg.get(k)
            if v is None or v == '' or (isinstance(v, (list, dict)) and not v):
                # keep only if it's a required key; otherwise drop
                if k in {'model', 'engine', 'ayanamsa', 'color_theme'}:
                    cfg.pop(k, None)
        data['config'] = cfg
    # Also clean any top-level optional strings if empty
    for k in ['color_theme']:
        if data.get(k) in (None, ''):
            data.pop(k, None)
    return data

def add_subject(ws: Workspace, subject: ChartSubject, base_dir: Union[str, Path]) -> str:
    """Add a subject to a Workspace and write its YAML file.
    
    Args:
        ws: Workspace to add subject to
        subject: ChartSubject instance to add
        base_dir: Base directory for workspace files
        
    Returns:
        Relative path (e.g., `subjects/john-doe.yml`) written to disk
        
    Note:
        Caller should re-save the manifest via `save_workspace_modular`.
    """
    rel = f"subjects/{_safe_filename(getattr(subject, 'id', getattr(subject, 'name', 'subject')))}.yml"
    _dump_yaml(resolve_under_base(base_dir, rel), _serialize(subject))
    ws.subjects = (ws.subjects or []) + [subject]
    return rel


def add_chart(ws: Workspace, chart: ChartInstance, base_dir: Union[str, Path]) -> str:
    """Add a chart to a Workspace and write its YAML file.
    
    Args:
        ws: Workspace to add chart to
        chart: ChartInstance to add
        base_dir: Base directory for workspace files
        
    Returns:
        Relative path to chart YAML file
        
    Note:
        Prevents duplicates by checking existing charts. Removes computed_chart
        and ephemeral overrides before serialization.
    """
    base_name = getattr(chart, 'id', None) or (getattr(chart, 'subject', None) and getattr(chart.subject, 'name', None)) or 'chart'
    # Prevent duplicates in memory collection
    identity = base_name
    for existing in (ws.charts or []):
        ex_id = getattr(existing, 'id', None) or (getattr(existing, 'subject', None) and getattr(existing.subject, 'name', None))
        if ex_id and ex_id == identity:
            return f"charts/{_safe_filename(identity)}.yml"

    # Prepare serializable data, removing computed payload and ephemeral overrides
    data = _serialize(chart)
    if isinstance(data, dict):
        data = _prune_chart_yaml_payload(data)

    rel = f"charts/{_safe_filename(base_name)}.yml"
    _dump_yaml(resolve_under_base(base_dir, rel), data)
    ws.charts = (ws.charts or []) + [chart]
    return rel


def update_chart(ws: Workspace, chart_id: str, updater: Callable[[ChartInstance], ChartInstance]) -> bool:
    """Update a chart in-memory by id using a caller-provided updater.
    
    Args:
        ws: Workspace containing the chart
        chart_id: ID of chart to update
        updater: Function that takes ChartInstance and returns updated ChartInstance
        
    Returns:
        True if chart was found and updated, False otherwise
    """
    if not ws.charts:
        return False
    for idx, c in enumerate(ws.charts):
        if getattr(c, 'id', None) == chart_id:
            ws.charts[idx] = updater(c)
            return True
    return False


def remove_chart(ws: Workspace, chart_id: str) -> bool:
    """Remove a chart from the Workspace in-memory by its id.
    
    Args:
        ws: Workspace containing the chart
        chart_id: ID of chart to remove
        
    Returns:
        True if chart was found and removed, False otherwise
    """
    if not ws.charts:
        return False
    before = len(ws.charts)
    ws.charts = [c for c in ws.charts if getattr(c, 'id', None) != chart_id]
    return len(ws.charts) != before


def iter_charts(ws: Workspace) -> Iterator[ChartInstance]:
    """Yield charts from the Workspace (safe for None).
    
    Args:
        ws: Workspace to iterate charts from
        
    Yields:
        ChartInstance objects from workspace
    """
    for c in ws.charts or []:
        yield c


def summarize_chart(chart: ChartInstance) -> Dict[str, Union[str, List[str]]]:
    """Return a lightweight summary dict for a chart.
    
    Args:
        chart: ChartInstance to summarize
        
    Returns:
        Dictionary with keys: id, name, event_time, location, engine,
        zodiac_type, house_system, tags
    """
    subj = getattr(chart, 'subject', None)
    cfg = getattr(chart, 'config', None)
    loc = getattr(subj, 'location', None) if subj else None
    return {
        "id": getattr(chart, 'id', ''),
        "name": getattr(subj, 'name', '') if subj else '',
        "event_time": str(getattr(subj, 'event_time', '')) if subj else '',
        "location": getattr(loc, 'name', '') if loc else '',
        "engine": str(getattr(cfg, 'engine', '')) if cfg else '',
        "zodiac_type": str(getattr(cfg, 'zodiac_type', '')) if cfg else '',
        "house_system": str(getattr(cfg, 'house_system', '')) if cfg else '',
        "tags": list(getattr(chart, 'tags', []) or []),
    }


# Batch recompute
try:
    from module.services import compute_positions_for_chart
except ImportError:
    try:
        from services import compute_positions_for_chart
    except ImportError:
        compute_positions_for_chart = None


def recompute_all(ws: Workspace) -> Dict[str, Dict[str, float]]:
    """Compute positions for all charts in a workspace.
    
    Args:
        ws: Workspace containing charts to recompute
        
    Returns:
        Dictionary mapping chart_id -> positions dict. Charts that fail to
        compute will have empty dict as value.
    """
    results: Dict[str, Dict[str, float]] = {}
    if not ws.charts or compute_positions_for_chart is None:
        return results
    for chart in ws.charts:
        try:
            positions = compute_positions_for_chart(chart)
            results[getattr(chart, 'id', '')] = positions or {}
        except Exception:
            results[getattr(chart, 'id', '')] = {}
    return results


def load_workspace_from_dir(base_dir: Union[str, Path]) -> Workspace:
    """Load a workspace given its base directory.
    
    Args:
        base_dir: Directory containing `workspace.yaml` manifest
        
    Returns:
        Workspace instance loaded from manifest
        
    Raises:
        FileNotFoundError: If directory or workspace.yaml does not exist
    """
    base = Path(base_dir)
    if not base.exists() or not base.is_dir():
        raise FileNotFoundError(f"Workspace directory not found: {base_dir}")
    manifest_path = base / "workspace.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Workspace manifest not found: {manifest_path}")
    return load_workspace(str(manifest_path))


def add_or_update_chart(ws: Workspace, chart: ChartInstance, base_dir: Union[str, Path]) -> str:
    """Add a new chart or update an existing one by id or subject name; persist YAML and manifest.
    
    Returns the relative path to the chart YAML (e.g., `charts/john-doe.yml`).
    """
    identity = getattr(chart, 'id', None) or (getattr(chart, 'subject', None) and getattr(chart.subject, 'name', None)) or 'chart'
    rel = f"charts/{_safe_filename(identity)}.yml"
    # Update in-memory collection (replace if exists)
    replaced = False
    charts = list(ws.charts or [])
    for idx, existing in enumerate(charts):
        ex_id = getattr(existing, 'id', None) or (getattr(existing, 'subject', None) and getattr(existing.subject, 'name', None))
        if ex_id and ex_id == identity:
            charts[idx] = chart
            replaced = True
            break
    if not replaced:
        charts.append(chart)
    ws.charts = charts
    # Prepare serializable data similar to add_chart (drop computed and ephemeral overrides)
    data = _serialize(chart)
    if isinstance(data, dict):
        data = _prune_chart_yaml_payload(data)
    # Write chart YAML and persist manifest
    _dump_yaml(resolve_under_base(base_dir, rel), data)
    save_workspace_modular(ws, base_dir)
    return rel


def remove_chart_by_id(ws: Workspace, chart_id: str, base_dir: Union[str, Path]) -> bool:
    """Remove a chart by id and persist the manifest. Returns True if removed."""
    ok = remove_chart(ws, chart_id)
    if ok:
        save_workspace_modular(ws, base_dir)
    return ok


def scan_workspace_changes(base_dir: Union[str, Path]) -> Dict[str, Dict[str, List[str]]]:
    """Scan the workspace directory for drift relative to the manifest.
    
    Returns:
    - { 'charts': {'new_on_disk': [...], 'missing_on_disk': [...]},
        'subjects': {'new_on_disk': [...], 'missing_on_disk': [...]} }
      where item names are basenames (e.g., `john-doe.yml`).
    """
    base = Path(base_dir)
    manifest_path = base / "workspace.yaml"
    result: Dict[str, Dict[str, List[str]]] = {
        'charts': {'new_on_disk': [], 'missing_on_disk': []},
        'subjects': {'new_on_disk': [], 'missing_on_disk': []},
    }
    try:
        manifest = read_yaml_file(manifest_path)
    except Exception:
        return result

    def _scan(subdir: str, key: str):
        disk = set(p.name for p in (base / subdir).glob("*.yml"))
        refs = set(Path(p).name for p in (manifest.get(key, []) or []))
        new_on_disk = sorted(list(disk - refs))
        missing_on_disk = sorted(list(refs - disk))
        return new_on_disk, missing_on_disk

    charts_new, charts_missing = _scan("charts", "charts")
    subs_new, subs_missing = _scan("subjects", "subjects")
    result['charts']['new_on_disk'] = charts_new
    result['charts']['missing_on_disk'] = charts_missing
    result['subjects']['new_on_disk'] = subs_new
    result['subjects']['missing_on_disk'] = subs_missing
    return result


def sync_workspace(workspace_path: Union[str, Path], auto_import: bool = True, auto_remove: bool = False) -> Dict[str, Any]:
    """Synchronize workspace manifest with files on disk.
    
    This function:
    1. Scans for chart/subject files on disk that aren't in the manifest (new files)
    2. Optionally imports new charts/subjects into the workspace
    3. Optionally removes references to missing files from the manifest
    4. Saves the updated workspace
    
    Args:
        workspace_path: Path to workspace.yaml
        auto_import: If True, automatically import new charts/subjects found on disk
        auto_remove: If True, remove references to missing files from manifest
        
    Returns:
        Dict with sync results:
        - 'changes': Dict from scan_workspace_changes()
        - 'imported_charts': List of chart IDs imported
        - 'imported_subjects': List of subject IDs imported
        - 'removed_charts': List of chart references removed (if auto_remove=True)
        - 'removed_subjects': List of subject references removed (if auto_remove=True)
    """
    workspace_path = Path(workspace_path)
    base_dir = workspace_path.parent
    
    # Load current workspace
    ws = load_workspace(str(workspace_path))
    
    # Scan for changes
    changes = scan_workspace_changes(base_dir)
    
    result = {
        'changes': changes,
        'imported_charts': [],
        'imported_subjects': [],
        'removed_charts': [],
        'removed_subjects': [],
    }
    
    # Import new charts
    if auto_import:
        try:
            from module.utils import import_chart_yaml
        except ImportError:
            from utils import import_chart_yaml
        
        for fname in changes.get('charts', {}).get('new_on_disk', []):
            chart_path = base_dir / 'charts' / fname
            try:
                chart = import_chart_yaml(str(chart_path))
                add_or_update_chart(ws, chart, base_dir=base_dir)
                result['imported_charts'].append(chart.id)
            except Exception:
                continue
    
    # Import new subjects
    if auto_import:
        for fname in changes.get('subjects', {}).get('new_on_disk', []):
            subject_path = base_dir / 'subjects' / fname
            try:
                data = read_yaml_file(str(subject_path))
                if isinstance(data, dict):
                    subj = ChartSubject(**data)
                    add_subject(ws, subj, base_dir=base_dir)
                    result['imported_subjects'].append(subj.id)
            except Exception:
                continue
    
    # Remove missing files from manifest
    if auto_remove:
        prune_result = prune_workspace_manifest(base_dir)
        result['removed_charts'] = prune_result.get('removed_charts', [])
        result['removed_subjects'] = prune_result.get('removed_subjects', [])
        # Reload workspace after pruning
        ws = load_workspace(str(workspace_path))
    
    # Save workspace if we made changes
    if result['imported_charts'] or result['imported_subjects']:
        save_workspace_modular(ws, base_dir)
    
    return result


def prune_workspace_manifest(base_dir: Union[str, Path]) -> Dict[str, List[str]]:
    """Prune workspace.yaml to remove references to modular files that no longer exist.
    
    This function does NOT write any new YAML files. It only removes stale
    entries from the manifest lists (charts, subjects, layouts, annotations,
    chart_presets) when the corresponding files are missing on disk.
    
    Returns a summary dict with keys removed_<section> listing removed refs.
    """
    base = Path(base_dir)
    manifest_path = base / "workspace.yaml"
    summary: Dict[str, List[str]] = {
        'removed_charts': [],
        'removed_subjects': [],
        'removed_layouts': [],
        'removed_annotations': [],
        'removed_presets': [],
    }
    try:
        manifest = read_yaml_file(manifest_path)
    except Exception:
        return summary

    def _filter_existing(key: str, subdir: str, removed_key: str):
        items = manifest.get(key, []) or []
        new_items = []
        removed: List[str] = []
        for it in items:
            # keep embedded dicts as-is
            if isinstance(it, dict):
                new_items.append(it)
                continue
            if isinstance(it, str):
                p = base / it if not it.startswith('/') else Path(it)
                if p.exists():
                    new_items.append(it)
                else:
                    removed.append(it)
        manifest[key] = new_items
        summary[removed_key] = removed

    _filter_existing('charts', 'charts', 'removed_charts')
    _filter_existing('subjects', 'subjects', 'removed_subjects')
    _filter_existing('layouts', 'layouts', 'removed_layouts')
    _filter_existing('annotations', 'annotations', 'removed_annotations')
    _filter_existing('chart_presets', 'presets', 'removed_presets')

    # Write back pruned manifest
    try:
        write_yaml_file(manifest_path, manifest, sort_keys=False, allow_unicode=True)
    except Exception:
        # If write fails, return original summary (nothing else to do)
        return summary
    return summary


# ──────────────────────────────
# WORKSPACE VALIDATION & BUILDING
# ──────────────────────────────

def _collect_ids(seq: List[Any], attr: str) -> List[str]:
    """Collect string IDs from a sequence of objects by attribute name.
    
    Args:
        seq: Sequence of objects to extract IDs from
        attr: Attribute name to extract from each object
        
    Returns:
        List of string IDs extracted from objects
    """
    out: List[str] = []
    for x in seq or []:
        try:
            val = getattr(x, attr)
            if isinstance(val, str):
                out.append(val)
        except Exception:
            continue
    return out


def validate_workspace(ws: Any) -> List[str]:
    """Validate workspace consistency and return a list of human-readable issues.
    
    Args:
        ws: Workspace instance to validate
        
    Returns:
        List of human-readable issue strings (empty if no issues found)
        
    Note:
        Checks:
        - Active model presence and resolution
        - WorkspaceDefaults default_bodies/default_aspects exist in the active model
        - Top-level ws.aspects exist in the active model
        - Each ChartInstance.config included_points exist in the active model bodies
        - Each ChartInstance.config aspect_orbs keys exist in the active model aspects
        - Layout chart references resolve to existing chart IDs
    """
    issues: List[str] = []
    
    model = get_active_model(ws)
    if model is None:
        issues.append("[error] No active model found (ws.models empty or active_model[_name] not set)")
        return issues

    body_ids = set(_collect_ids(getattr(model, 'body_definitions', []) or [], 'id'))
    aspect_ids = set(_collect_ids(getattr(model, 'aspect_definitions', []) or [], 'id'))

    # Workspace default overrides
    d = getattr(ws, 'default', None)
    if d is not None:
        try:
            for b in getattr(d, 'default_bodies', []) or []:
                if b not in body_ids:
                    issues.append(f"[warn] default_bodies contains unknown body id: {b}")
        except Exception:
            pass
        try:
            for a in getattr(d, 'default_aspects', []) or []:
                if a not in aspect_ids:
                    issues.append(f"[warn] default_aspects contains unknown aspect id: {a}")
        except Exception:
            pass

    # Top-level ws.aspects override
    try:
        for a in getattr(ws, 'aspects', []) or []:
            if a not in aspect_ids:
                issues.append(f"[warn] workspace aspects override contains unknown aspect id: {a}")
    except Exception:
        pass

    # Charts consistency
    charts = getattr(ws, 'charts', []) or []
    chart_ids = set()
    for ch in charts:
        try:
            cid = getattr(ch, 'id', None)
            if isinstance(cid, str) and cid:
                chart_ids.add(cid)
        except Exception:
            continue

    for ch in charts:
        try:
            cfg = getattr(ch, 'config', None)
            if cfg is None:
                issues.append(f"[error] Chart has no config: id={getattr(ch, 'id', '(no id)')}")
                continue
            # included_points against model body ids
            for pt in getattr(cfg, 'included_points', []) or []:
                if pt not in body_ids:
                    issues.append(f"[warn] Chart {getattr(ch, 'id', '(no id)')} includes unknown body id: {pt}")
            # aspect_orbs keys against model aspect ids
            for k in (getattr(cfg, 'aspect_orbs', {}) or {}).keys():
                if k not in aspect_ids:
                    issues.append(f"[warn] Chart {getattr(ch, 'id', '(no id)')} aspect_orbs has unknown aspect id: {k}")
        except Exception:
            continue

    # Layout references
    try:
        for lay in getattr(ws, 'layouts', []) or []:
            for ref in getattr(lay, 'chart_instances', []) or []:
                if isinstance(ref, str) and ref not in chart_ids:
                    issues.append(f"[warn] Layout '{getattr(lay, 'name', '(unnamed)')}' references missing chart id: {ref}")
    except Exception:
        pass

    return issues


def validation_report(ws: Any) -> str:
    """Return a multi-line text report from validate_workspace().
    
    Args:
        ws: Workspace instance to validate
        
    Returns:
        Multi-line text report of validation issues, or success message
    """
    issues = validate_workspace(ws)
    if not issues:
        return "Workspace validation passed with no issues."
    return "\n".join(issues)


def populate_workspace_models(ws: Any, dir_path: Union[str, Path]) -> Dict[str, AstroModel]:
    """Load .sfs models from a directory and assign them to workspace.
    
    Args:
        ws: Workspace instance to populate models into
        dir_path: Directory path to scan for .sfs files
        
    Returns:
        Dictionary of loaded models
        
    Note:
        If ws.active_model is not set and any models were loaded,
        sets it to the first key.
    """
    loaded = load_sfs_models_from_dir(dir_path)
    try:
        if hasattr(ws, 'models'):
            ws.models.update(loaded)
        if not getattr(ws, 'active_model', None) and loaded:
            ws.active_model = next(iter(loaded.keys()))
    except Exception:
        pass
    return loaded


def build_workspace_from_sfs(dir_path: Union[str, Path], owner: str = "local",
                             ephemeris_name: str = "local", ephemeris_backend: str = "local") -> Workspace:
    """Create a new Workspace from a directory of .sfs model files.
    
    Args:
        dir_path: Directory path containing .sfs files
        owner: Workspace owner identifier, defaults to "local"
        ephemeris_name: Ephemeris name, defaults to "local"
        ephemeris_backend: Ephemeris backend, defaults to "local"
        
    Returns:
        Workspace instance with loaded models and empty collections
        
    Note:
        Loads all .sfs files into AstroModel catalogs, selects the first model
        as active (if any), and initializes empty collections for charts, presets,
        layouts, and annotations.
    """
    models = load_sfs_models_from_dir(dir_path)
    active_name = next(iter(models.keys())) if models else ""
    ws = Workspace(
        owner=owner,
        active_model=active_name,
        chart_presets=[],
        subjects=[],
        charts=[],
        layouts=[],
        annotations=[],
        default=WorkspaceDefaults(
            ephemeris_engine=_safe_engine(ephemeris_backend),
            ephemeris_backend=ephemeris_name,
        ),
    )
    ws.models.update(models)
    ws.active_model = active_name or None
    return ws


def build_workspace_from_sfs_to_yaml(dir_path: Union[str, Path], out_path: Union[str, Path],
                                     owner: str = "local",
                                     ephemeris_name: str = "local",
                                     ephemeris_backend: str = "local") -> Path:
    """Build a Workspace from .sfs files and save it as YAML.
    
    Args:
        dir_path: Directory containing .sfs files
        out_path: Output YAML file path
        owner: Workspace owner identifier, defaults to "local"
        ephemeris_name: Ephemeris name, defaults to "local"
        ephemeris_backend: Ephemeris backend, defaults to "local"
        
    Returns:
        Path to written YAML file
    """
    ws = build_workspace_from_sfs(dir_path, owner=owner, ephemeris_name=ephemeris_name, ephemeris_backend=ephemeris_backend)
    return export_workspace_yaml(ws, out_path)
