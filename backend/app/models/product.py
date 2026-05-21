from pydantic import BaseModel, Field
from typing import List, Optional


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


class ProductScrapeResult(BaseModel):
    source_url: str
    title: str
    image_url: Optional[str] = None
    currency: Optional[str] = None
    price: Optional[str] = None
    raw_size_text: Optional[str] = None
    normalized_sizes: List[SizeMeasurement] = []


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
    garment_size: SizeMeasurement


class FitZone(BaseModel):
    zone: str
    difference_cm: Optional[float]
    status: str
    color: str
    message: str


class FitCheckResult(BaseModel):
    zones: List[FitZone]
    summary: str
