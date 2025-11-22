---

title: workspace Module

description: API documentation for workspace module

weight: 10

---


# `workspace` module

## Functions

### `add_chart`

```python
add_chart(ws: module.models.Workspace, chart: module.models.ChartInstance, base_dir: Union[str, pathlib._local.Path]) -> str
```

Add a chart to a Workspace and write its YAML file.

#### Parameters

- **ws**: Workspace to add chart to

- **chart**: ChartInstance to add

- **base_dir**: Base directory for workspace files


#### Returns

Relative path to chart YAML file


#### Notes

Prevents duplicates by checking existing charts. Removes computed_chart
    and ephemeral overrides before serialization.

### `add_or_update_chart`

```python
add_or_update_chart(ws: module.models.Workspace, chart: module.models.ChartInstance, base_dir: Union[str, pathlib._local.Path]) -> str
```

Add a new chart or update an existing one by id or subject name; persist YAML and manifest.

### `add_subject`

```python
add_subject(ws: module.models.Workspace, subject: module.models.ChartSubject, base_dir: Union[str, pathlib._local.Path]) -> str
```

Add a subject to a Workspace and write its YAML file.

#### Parameters

- **ws**: Workspace to add subject to

- **subject**: ChartSubject instance to add

- **base_dir**: Base directory for workspace files


#### Returns

Relative path (e.g., `subjects/john-doe.yml`) written to disk


#### Notes

Caller should re-save the manifest via `save_workspace_modular`.

### `build_workspace_from_sfs`

```python
build_workspace_from_sfs(dir_path: Union[str, pathlib._local.Path], owner: str = 'local', ephemeris_name: str = 'local', ephemeris_backend: str = 'local') -> module.models.Workspace
```

Create a new Workspace from a directory of .sfs model files.

#### Parameters

- **dir_path**: Directory path containing .sfs files

- **owner**: Workspace owner identifier, defaults to "local"

- **ephemeris_name**: Ephemeris name, defaults to "local"

- **ephemeris_backend**: Ephemeris backend, defaults to "local"


#### Returns

Workspace instance with loaded models and empty collections


#### Notes

Loads all .sfs files into AstroModel catalogs, selects the first model
    as active (if any), and initializes empty collections for charts, presets,
    layouts, and annotations.

### `build_workspace_from_sfs_to_yaml`

```python
build_workspace_from_sfs_to_yaml(dir_path: Union[str, pathlib._local.Path], out_path: Union[str, pathlib._local.Path], owner: str = 'local', ephemeris_name: str = 'local', ephemeris_backend: str = 'local') -> pathlib._local.Path
```

Build a Workspace from .sfs files and save it as YAML.

#### Parameters

- **dir_path**: Directory containing .sfs files

- **out_path**: Output YAML file path

- **owner**: Workspace owner identifier, defaults to "local"

- **ephemeris_name**: Ephemeris name, defaults to "local"

- **ephemeris_backend**: Ephemeris backend, defaults to "local"


#### Returns

Path to written YAML file

### `change_language`

```python
change_language(default: str = 'cz') -> dict
```

Return a simple language mapping from SQLite `language` table.

#### Parameters

- **default**: Column name to use for values, e.g., "cz" or "en", defaults to "cz"


#### Returns

Dictionary mapping language keys to translated values

### `delete_custom_aspect_definition`

```python
delete_custom_aspect_definition(asp_id: str, db_path: Optional[pathlib._local.Path] = None) -> bool
```

Delete a custom aspect definition from SQLite database.

#### Parameters

- **asp_id**: ID of aspect definition to delete

- **db_path**: Optional path to SQLite database, defaults to TRANSLATION_DB


#### Returns

True if successful, False otherwise

### `delete_custom_observable_object`

```python
delete_custom_observable_object(obj_id: str, db_path: Optional[pathlib._local.Path] = None) -> bool
```

Delete a custom observable object definition from SQLite database.

#### Parameters

- **obj_id**: ID of observable object to delete

- **db_path**: Optional path to SQLite database, defaults to TRANSLATION_DB


#### Returns

True if successful, False otherwise

### `get_all_aspect_definitions`

```python
get_all_aspect_definitions(db_path: Optional[pathlib._local.Path] = None) -> Dict[str, module.models.AspectDefinition]
```

Get all aspect definitions (defaults + custom from database).

#### Parameters

- **db_path**: Optional path to SQLite database, defaults to TRANSLATION_DB


#### Returns

Dictionary mapping aspect_id -&gt; AspectDefinition. Custom aspects from
    database override defaults with the same id.

### `get_all_observable_objects`

```python
get_all_observable_objects(db_path: Optional[pathlib._local.Path] = None) -> Dict[str, module.models.BodyDefinition]
```

Get all observable objects (defaults + custom from database).

#### Parameters

- **db_path**: Optional path to SQLite database, defaults to TRANSLATION_DB


#### Returns

Dictionary mapping object_id -&gt; BodyDefinition. Custom objects from
    database override defaults with the same id.

### `get_default_aspect_definitions`

```python
get_default_aspect_definitions() -> Dict[str, module.models.AspectDefinition]
```

Get default aspect definitions.

#### Returns

Dictionary mapping aspect_id -&gt; AspectDefinition for standard aspects
    (conjunction, opposition, trine, square, sextile, etc.)

### `get_default_observable_objects`

```python
get_default_observable_objects() -> Dict[str, module.models.BodyDefinition]
```

Get default observable object definitions.

#### Returns

Dictionary mapping object_id -&gt; BodyDefinition for standard objects
    (planets, angles, lunar nodes, calculated points) that are commonly
    available in kerykeion and can be computed.

### `init_aspect_definitions_db`

```python
init_aspect_definitions_db(db_path: Optional[pathlib._local.Path] = None) -> None
```

Initialize SQLite database schema for custom aspect definitions.

#### Parameters

- **db_path**: Optional path to SQLite database, defaults to TRANSLATION_DB


#### Notes

Creates the 'aspect_definitions' table if it doesn't exist.
    This is optional and won't break if the database doesn't exist.

### `init_observable_objects_db`

```python
init_observable_objects_db(db_path: Optional[pathlib._local.Path] = None) -> None
```

Initialize SQLite database schema for custom observable object definitions.

#### Parameters

- **db_path**: Optional path to SQLite database, defaults to TRANSLATION_DB


#### Notes

Creates the 'observable_objects' table if it doesn't exist.
    This is optional and won't break if the database doesn't exist.

### `init_workspace`

```python
init_workspace(base_dir: Union[str, pathlib._local.Path], owner: str, active_model: str, default_ephemeris: Dict[str, str]) -> pathlib._local.Path
```

Initialize a new workspace directory structure and manifest.

#### Parameters

- **base_dir**: Base directory for workspace files

- **owner**: Workspace owner identifier

- **active_model**: Active model name (deprecated, use active_model_name in Workspace)

- **default_ephemeris**: Dictionary with 'name' and 'backend' keys for ephemeris settings


#### Returns

Path to created workspace.yaml manifest file


#### Notes

The 'active_model' parameter is deprecated. Use 'active_model_name' in the
    Workspace object after creation instead. Creates subdirectories for subjects,
    charts, layouts, annotations, and presets. Initializes database tables.

### `iter_charts`

```python
iter_charts(ws: module.models.Workspace) -> Iterator[module.models.ChartInstance]
```

Yield charts from the Workspace (safe for None).

#### Parameters

- **ws**: Workspace to iterate charts from

### `load_custom_aspect_definitions`

```python
load_custom_aspect_definitions(db_path: Optional[pathlib._local.Path] = None) -> List[module.models.AspectDefinition]
```

Load custom aspect definitions from SQLite database.

#### Parameters

- **db_path**: Optional path to SQLite database, defaults to TRANSLATION_DB


#### Returns

List of AspectDefinition objects for custom aspects defined in the database.
    Returns empty list if database doesn't exist or table is missing.

### `load_custom_observable_objects`

```python
load_custom_observable_objects(db_path: Optional[pathlib._local.Path] = None) -> List[module.models.BodyDefinition]
```

Load custom observable object definitions from SQLite database.

#### Parameters

- **db_path**: Optional path to SQLite database, defaults to TRANSLATION_DB


#### Returns

List of BodyDefinition objects for custom objects defined in the database.
    Returns empty list if database doesn't exist or table is missing.

### `load_workspace`

```python
load_workspace(workspace_path: str) -> module.models.Workspace
```

Load a modular workspace from a manifest YAML file.

#### Parameters

- **workspace_path**: Absolute or relative path to `workspace.yaml`.


#### Returns

Workspace dataclass assembled from the manifest and referenced parts.


#### Notes

Paths referenced in the manifest (e.g., `charts/*.yml`) are resolved
    relative to the manifest directory and validated for containment.


#### Warnings

⚠️ FileNotFoundError: If workspace file does not exist

### `load_workspace_from_dir`

```python
load_workspace_from_dir(base_dir: Union[str, pathlib._local.Path]) -> module.models.Workspace
```

Load a workspace given its base directory.

#### Parameters

- **base_dir**: Directory containing `workspace.yaml` manifest


#### Returns

Workspace instance loaded from manifest


#### Warnings

⚠️ FileNotFoundError: If directory or workspace.yaml does not exist

### `populate_workspace_models`

```python
populate_workspace_models(ws: Any, dir_path: Union[str, pathlib._local.Path]) -> Dict[str, module.models.AstroModel]
```

Load .sfs models from a directory and assign them to workspace.

#### Parameters

- **ws**: Workspace instance to populate models into

- **dir_path**: Directory path to scan for .sfs files


#### Returns

Dictionary of loaded models


#### Notes

If ws.active_model_name is not set and any models were loaded,
    sets it to the first key.

### `prune_workspace_manifest`

```python
prune_workspace_manifest(base_dir: Union[str, pathlib._local.Path]) -> Dict[str, List[str]]
```

Prune workspace.yaml to remove references to modular files that no longer exist.

### `recompute_all`

```python
recompute_all(ws: module.models.Workspace) -> Dict[str, Dict[str, float]]
```

Compute positions for all charts in a workspace.

#### Parameters

- **ws**: Workspace containing charts to recompute


#### Returns

Dictionary mapping chart_id -&gt; positions dict. Charts that fail to
    compute will have empty dict as value.

### `remove_chart`

```python
remove_chart(ws: module.models.Workspace, chart_id: str) -> bool
```

Remove a chart from the Workspace in-memory by its id.

#### Parameters

- **ws**: Workspace containing the chart

- **chart_id**: ID of chart to remove


#### Returns

True if chart was found and removed, False otherwise

### `remove_chart_by_id`

```python
remove_chart_by_id(ws: module.models.Workspace, chart_id: str, base_dir: Union[str, pathlib._local.Path]) -> bool
```

Remove a chart by id and persist the manifest. Returns True if removed.

### `save_custom_aspect_definition`

```python
save_custom_aspect_definition(asp: module.models.AspectDefinition, db_path: Optional[pathlib._local.Path] = None) -> bool
```

Save a custom aspect definition to SQLite database.

#### Parameters

- **asp**: AspectDefinition to save

- **db_path**: Optional path to SQLite database, defaults to TRANSLATION_DB


#### Returns

True if successful, False otherwise

### `save_custom_observable_object`

```python
save_custom_observable_object(obj: module.models.BodyDefinition, db_path: Optional[pathlib._local.Path] = None) -> bool
```

Save a custom observable object definition to SQLite database.

#### Parameters

- **obj**: BodyDefinition to save

- **db_path**: Optional path to SQLite database, defaults to TRANSLATION_DB


#### Returns

True if successful, False otherwise

### `save_workspace_flat`

```python
save_workspace_flat(workspace: module.models.Workspace, path: str, format: str = 'yaml') -> None
```

Save the entire Workspace as a single flat file (debug/export use).

#### Parameters

- **workspace**: Workspace instance to serialize

- **path**: Destination file path (YAML or JSON)

- **format**: "yaml" or "json", defaults to "yaml"


#### Warnings

⚠️ ValueError: If format is not "yaml" or "json"

### `save_workspace_modular`

```python
save_workspace_modular(workspace: module.models.Workspace, base_dir: Union[str, pathlib._local.Path]) -> pathlib._local.Path
```

Persist a Workspace into modular YAML files and update `workspace.yaml`.

#### Returns

- Absolute path to the updated `workspace.yaml`.

### `scan_workspace_changes`

```python
scan_workspace_changes(base_dir: Union[str, pathlib._local.Path]) -> Dict[str, Dict[str, List[str]]]
```

Scan the workspace directory for drift relative to the manifest.

#### Returns

- { 'charts': {'new_on_disk': [...], 'missing_on_disk': [...]},
    'subjects': {'new_on_disk': [...], 'missing_on_disk': [...]} }
  where item names are basenames (e.g., `john-doe.yml`).

### `summarize_chart`

```python
summarize_chart(chart: module.models.ChartInstance) -> Dict[str, Union[str, List[str]]]
```

Return a lightweight summary dict for a chart.

#### Parameters

- **chart**: ChartInstance to summarize


#### Returns

Dictionary with keys: id, name, event_time, location, engine,
    zodiac_type, house_system, tags

### `update_chart`

```python
update_chart(ws: module.models.Workspace, chart_id: str, updater: Callable[[module.models.ChartInstance], module.models.ChartInstance]) -> bool
```

Update a chart in-memory by id using a caller-provided updater.

#### Parameters

- **ws**: Workspace containing the chart

- **chart_id**: ID of chart to update

- **updater**: Function that takes ChartInstance and returns updated ChartInstance


#### Returns

True if chart was found and updated, False otherwise

### `validate_workspace`

```python
validate_workspace(ws: Any) -> List[str]
```

Validate workspace consistency and return a list of human-readable issues.

#### Parameters

- **ws**: Workspace instance to validate


#### Returns

List of human-readable issue strings (empty if no issues found)


#### Notes

Checks:
    - Active model presence and resolution
    - WorkspaceDefaults default_bodies/default_aspects exist in the active model
    - Top-level ws.aspects exist in the active model
    - Each ChartInstance.config included_points exist in the active model bodies
    - Each ChartInstance.config aspect_orbs keys exist in the active model aspects
    - Layout chart references resolve to existing chart IDs

### `validation_report`

```python
validation_report(ws: Any) -> str
```

Return a multi-line text report from validate_workspace().

#### Parameters

- **ws**: Workspace instance to validate


#### Returns

Multi-line text report of validation issues, or success message

## Classes

### class `TranslationBackend` (str, Enum)

### class `TranslationService` 

Provide simple i18n label loading from YAML files or SQLite.

Use `get(domain, key, lang)` for single lookups and `inject_i18n(items, ...)`
to batch-attach translations under `item.i18n` keyed by item id.

#### Methods

- `get(self, domain: str, key: str, lang: Optional[str] = None) -> Optional[str]`
  
  Return translated value for a given domain/key in the selected language.

- `inject_i18n(self, items: List, domain: str, lang: Optional[str] = None)`
  
  Attach translations for `items` in-place under `item.i18n`.
