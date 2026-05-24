# -*- coding: utf-8 -*-
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Literal

from app.models.body import MannequinParams
from app.models.product import FitZone


VtonRunMode = Literal["mock", "external", "auto"]
VtonTaskState = Literal["queued", "running", "succeeded", "failed"]
VtonRenderMethod = Literal["NEURAL_REALISTIC", "LOCAL_FIT_DIAGRAM"]


class VtonPrepareInput(BaseModel):
    mannequin: MannequinParams
    garment_processed_url: Optional[str] = None
    garment_original_url: Optional[str] = None
    person_image_url: Optional[str] = None
    user_uploaded_person_image_url: Optional[str] = None
    fit_zones: List[FitZone] = []


class VtonPayload(BaseModel):
    mannequin: MannequinParams
    garment_processed_url: Optional[str]
    garment_original_url: Optional[str]
    person_image_url: Optional[str] = None
    user_uploaded_person_image_url: Optional[str] = None
    fit_zones: List[FitZone]
    render_mode: str
    recommended_view_count: int
    notes: List[str]
    api_ready_payload: Dict[str, Any]


class VtonMockInput(BaseModel):
    payload: VtonPayload


class VtonMockResult(BaseModel):
    result_url: str
    result_path: str
    render_method: VtonRenderMethod = "LOCAL_FIT_DIAGRAM"
    message: str


class VtonRunInput(BaseModel):
    payload: VtonPayload
    mode: VtonRunMode = "auto"


class VtonRunResult(BaseModel):
    result_url: Optional[str] = None
    result_path: Optional[str] = None
    provider: str
    mode_requested: VtonRunMode
    render_method: VtonRenderMethod
    status: Optional[str] = None
    used_fallback: bool
    success: bool
    message: str
    raw_response: Optional[Dict[str, Any]] = None


class VtonTaskCreated(BaseModel):
    task_id: str
    state: VtonTaskState
    poll_after_seconds: int = 2
    message: str


class VtonTaskStatusResponse(BaseModel):
    task_id: str
    state: VtonTaskState
    result: Optional[VtonRunResult] = None
    error: Optional[str] = None
    poll_after_seconds: int = 2


class PersonEphemeralUploadResult(BaseModel):
    person_image_url: str
    expires_in_seconds: int
    enhanced: bool = True
    message: str
