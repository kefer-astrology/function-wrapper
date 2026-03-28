from typing import Optional, List

from pydantic import BaseModel, Field


class ComputeChartRequest(BaseModel):
    workspace_path: str
    chart_id: str
    include_physical: bool = False
    include_topocentric: bool = False
    store_in_db: bool = False


class ComputeTransitSeriesRequest(BaseModel):
    workspace_path: str
    source_chart_id: str
    start_datetime: str
    end_datetime: str
    time_step: str = "1 hour"
    transiting_objects: Optional[List[str]] = None
    transited_objects: Optional[List[str]] = None
    aspect_types: Optional[List[str]] = None
    include_physical: bool = False
    include_topocentric: bool = False


class SyncWorkspaceRequest(BaseModel):
    workspace_path: str
    auto_import: bool = True
    auto_remove: bool = False


class ExportParquetRequest(BaseModel):
    workspace_path: str
    chart_id: Optional[str] = None
    output_dir: Optional[str] = None
    partition_by_date: bool = True


class HealthResponse(BaseModel):
    status: str = Field(default="ok")
    service: str = Field(default="kefer-api")

