from pydantic import BaseModel, Field
from typing import Dict, List, Optional

from app.models.body import UserBodyMeasurements


class ProductUrlInput(BaseModel):
    url: str = Field(..., min_length=8)


class SizeMeasurement(BaseModel):
    size_label: str
    chest_cm: Optional[float] = None
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    length_cm: Optional[float] = None
    shoulder_cm: Optional[float] = None
    sleeve_cm: Optional[float] = None
    biceps_cm: Optional[float] = None
    top_length_cm: Optional[float] = None
    inseam_cm: Optional[float] = None
    thigh_cm: Optional[float] = None
    rise_cm: Optional[float] = None
    wrist_cm: Optional[float] = None
    garment_category: Optional[str] = None
    stretch_level: Optional[str] = None
    additional_measurements: Dict[str, float] = Field(default_factory=dict)
    is_estimated: bool = False
    estimated_from_size: Optional[str] = None
    confidence: Optional[float] = None


class GarmentMeasurements(SizeMeasurement):
    pass


class FabricAnalysis(BaseModel):
    raw_text: Optional[str] = None
    stretch_factor: float = 0.0
    shrink_risk: float = 0.0
    drape_factor: float = 0.5
    detected_fibers: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ProductScrapeResult(BaseModel):
    source_url: str
    title: str
    image_url: Optional[str] = None
    currency: Optional[str] = None
    price: Optional[str] = None
    raw_size_text: Optional[str] = None
    normalized_sizes: List[SizeMeasurement] = Field(default_factory=list)
    fabric_composition_text: Optional[str] = None
    fabric_analysis: Optional[FabricAnalysis] = None
    confidence_score: Optional[float] = None
    extraction_method: Optional[str] = None
    fallback_reason: Optional[str] = None
    blocked_by_antibot: bool = False


class GarmentUploadResult(BaseModel):
    filename: str
    content_type: str
    original_path: str
    processed_path: Optional[str] = None
    original_url: Optional[str] = None
    processed_url: Optional[str] = None
    background_removed: bool = False
    message: str


class FitCheckInput(BaseModel):
    user_chest_cm: float = Field(..., ge=40, le=220)
    user_waist_cm: float = Field(..., ge=35, le=220)
    user_hip_cm: float = Field(..., ge=40, le=240)
    user_length_cm: Optional[float] = Field(default=None, ge=20, le=180)
    user_sleeve_cm: Optional[float] = Field(default=None, ge=20, le=120)
    user_biceps_cm: Optional[float] = Field(default=None, ge=15, le=90)
    user_top_length_cm: Optional[float] = Field(default=None, ge=20, le=150)
    user_inseam_cm: Optional[float] = Field(default=None, ge=35, le=140)
    user_thigh_cm: Optional[float] = Field(default=None, ge=25, le=120)
    user_shoulder_cm: Optional[float] = Field(default=None, ge=25, le=90)
    user_rise_cm: Optional[float] = Field(default=None, ge=10, le=70)
    user_wrist_cm: Optional[float] = Field(default=None, ge=10, le=50)
    user_measurements: Optional[UserBodyMeasurements] = None
    garment_size: SizeMeasurement
    candidate_sizes: List[SizeMeasurement] = Field(default_factory=list)
    garment_category: Optional[str] = None
    stretch_level: Optional[str] = None
    fabric_analysis: Optional[FabricAnalysis] = None
    user_ease_modifier: float = Field(default=0.0, ge=-6, le=6)


class FitZone(BaseModel):
    zone: str
    difference_cm: Optional[float]
    status: str
    color: str
    message: str
    body_cm: Optional[float] = None
    garment_cm: Optional[float] = None
    ease_allowance_cm: Optional[float] = None
    pressure_score: Optional[float] = None
    fabric_warning: Optional[str] = None


class FitSizeOption(BaseModel):
    size_label: str
    score: float
    zones: List[FitZone]
    summary: str
    is_estimated: bool = False
    is_best_match: bool = False


class FitCheckResult(BaseModel):
    zones: List[FitZone]
    summary: str
    best_size_label: Optional[str] = None
    selected_size_label: Optional[str] = None
    size_options: List[FitSizeOption] = Field(default_factory=list)
    fabric_warnings: List[str] = Field(default_factory=list)
    cache_key: Optional[str] = None
    cache_hit: bool = False


class FitFeedbackInput(BaseModel):
    user_key: str = Field(default="local-device", min_length=3)
    predicted_status: str
    reported_status: str
    zone: Optional[str] = None


class FitFeedbackResult(BaseModel):
    user_key: str
    user_ease_modifier: float
    message: str
