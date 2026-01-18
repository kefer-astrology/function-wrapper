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

### `get_all_aspect_definitions`

```python
get_all_aspect_definitions(ws: Optional[ForwardRef('Workspace')] = None, model: Optional[module.models.AstroModel] = None) -> Dict[str, module.models.AspectDefinition]
```

Get all aspect definitions (defaults + custom from workspace/model YAML).

#### Parameters

- **ws**: Optional Workspace to load custom aspects from

- **model**: Optional AstroModel to get aspect definitions from


#### Returns

Dictionary mapping aspect_id -&gt; AspectDefinition. Custom aspects from
    workspace/model override defaults with the same id.

### `get_all_observable_objects`

```python
get_all_observable_objects(ws: Optional[ForwardRef('Workspace')] = None, model: Optional[module.models.AstroModel] = None) -> Dict[str, module.models.BodyDefinition]
```

Get all observable objects (defaults + custom from workspace/model YAML).

#### Parameters

- **ws**: Optional Workspace to load custom objects from

- **model**: Optional AstroModel to get body definitions from


#### Returns

Dictionary mapping object_id -&gt; BodyDefinition. Custom objects from
    workspace/model override defaults with the same id.

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

### `init_workspace`

```python
init_workspace(base_dir: Union[str, pathlib._local.Path], owner: str, active_model: str, default_ephemeris: Dict[str, str]) -> pathlib._local.Path
```

Initialize a new workspace directory structure and manifest.

#### Returns

- Absolute path to the created `workspace.yaml` file.

### `iter_charts`

```python
iter_charts(ws: module.models.Workspace) -> Iterator[module.models.ChartInstance]
```

Yield charts from the Workspace (safe for None).

#### Parameters

- **ws**: Workspace to iterate charts from

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

If ws.active_model is not set and any models were loaded,
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

### `sync_workspace`

```python
sync_workspace(workspace_path: Union[str, pathlib._local.Path], auto_import: bool = True, auto_remove: bool = False) -> Dict[str, Any]
```

Synchronize workspace manifest with files on disk.

#### Parameters

- **workspace_path**: Path to workspace.yaml

- **auto_import**: If True, automatically import new charts/subjects found on disk

- **auto_remove**: If True, remove references to missing files from manifest


#### Returns

Dict with sync results:
    - 'changes': Dict from scan_workspace_changes()
    - 'imported_charts': List of chart IDs imported
    - 'imported_subjects': List of subject IDs imported
    - 'removed_charts': List of chart references removed (if auto_remove=True)
    - 'removed_subjects': List of subject references removed (if auto_remove=True)

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
