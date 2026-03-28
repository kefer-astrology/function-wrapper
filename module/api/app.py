from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Query

try:
    from module.cli import (
        cmd_compute_chart,
        cmd_compute_transit_series,
        cmd_export_parquet,
        cmd_get_chart,
        cmd_get_workspace_settings,
        cmd_list_charts,
        cmd_sync_workspace,
    )
    from module.api.schemas import (
        ComputeChartRequest,
        ComputeTransitSeriesRequest,
        ExportParquetRequest,
        HealthResponse,
        SyncWorkspaceRequest,
    )
except ImportError:
    from cli import (
        cmd_compute_chart,
        cmd_compute_transit_series,
        cmd_export_parquet,
        cmd_get_chart,
        cmd_get_workspace_settings,
        cmd_list_charts,
        cmd_sync_workspace,
    )
    from api.schemas import (
        ComputeChartRequest,
        ComputeTransitSeriesRequest,
        ExportParquetRequest,
        HealthResponse,
        SyncWorkspaceRequest,
    )


def _raise_for_error(result: Dict[str, Any]) -> Dict[str, Any]:
    """Translate CLI-style error payloads to HTTP errors."""
    if "error" not in result:
        return result

    error_type = result.get("type", "InternalError")
    message = result.get("error", "Unknown error")

    status_by_type = {
        "InvalidArgument": 400,
        "ChartNotFound": 404,
        "LoadError": 400,
        "SyncError": 400,
        "StorageNotAvailable": 503,
        "StorageNotFound": 404,
        "ExportError": 500,
        "ComputationError": 500,
    }
    raise HTTPException(
        status_code=status_by_type.get(error_type, 500),
        detail={"type": error_type, "message": message},
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="Kefer Astrology API",
        version="0.1.0",
        description="FastAPI adapter around the Kefer Astrology Python package.",
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/workspace/settings")
    def get_workspace_settings(workspace_path: str = Query(..., description="Path to workspace.yaml")):
        return _raise_for_error(cmd_get_workspace_settings({"workspace_path": workspace_path}))

    @app.get("/charts")
    def list_charts(workspace_path: str = Query(..., description="Path to workspace.yaml")):
        return _raise_for_error(cmd_list_charts({"workspace_path": workspace_path}))

    @app.get("/charts/{chart_id}")
    def get_chart(chart_id: str, workspace_path: str = Query(..., description="Path to workspace.yaml")):
        return _raise_for_error(cmd_get_chart({"workspace_path": workspace_path, "chart_id": chart_id}))

    @app.post("/charts/compute")
    def compute_chart(payload: ComputeChartRequest):
        return _raise_for_error(cmd_compute_chart(payload.model_dump()))

    @app.post("/transits/compute-series")
    def compute_transit_series(payload: ComputeTransitSeriesRequest):
        return _raise_for_error(cmd_compute_transit_series(payload.model_dump()))

    @app.post("/workspace/sync")
    def sync_workspace(payload: SyncWorkspaceRequest):
        return _raise_for_error(cmd_sync_workspace(payload.model_dump()))

    @app.post("/storage/export-parquet")
    def export_parquet(payload: ExportParquetRequest):
        return _raise_for_error(cmd_export_parquet(payload.model_dump()))

    return app


app = create_app()

