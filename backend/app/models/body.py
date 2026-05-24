# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class InitialBodyInput(BaseModel):
    height_cm: float = Field(..., ge=120, le=230)
    weight_kg: float = Field(..., ge=30, le=250)
    age: int = Field(..., ge=13, le=100)


class BodyModel(BaseModel):
    id: str
    label: str
    description: str

    shoulder_ratio: float
    hip_ratio: float
    waist_ratio: float
    muscle_ratio: float
    fat_ratio: float

    recommended: bool = False


class BodyRecommendationResponse(BaseModel):
    input: InitialBodyInput
    bmi: float
    models: List[BodyModel]


class FineTuneInput(BaseModel):
    base_model_id: str
    height_cm: float = Field(..., ge=120, le=230)
    weight_kg: float = Field(..., ge=30, le=250)
    age: int = Field(..., ge=13, le=100)

    chest_cm: float = Field(..., ge=50, le=180)
    waist_cm: float = Field(..., ge=40, le=180)
    hip_cm: float = Field(..., ge=50, le=200)
    shoulder_cm: Optional[float] = Field(default=None, ge=25, le=80)
    sleeve_cm: Optional[float] = Field(default=None, ge=20, le=100)
    biceps_cm: Optional[float] = Field(default=None, ge=15, le=80)
    top_length_cm: Optional[float] = Field(default=None, ge=20, le=130)
    inseam_cm: Optional[float] = Field(default=None, ge=35, le=130)
    thigh_cm: Optional[float] = Field(default=None, ge=25, le=110)
    rise_cm: Optional[float] = Field(default=None, ge=10, le=60)
    wrist_cm: Optional[float] = Field(default=None, ge=10, le=40)
    additional_measurements: Dict[str, float] = Field(default_factory=dict)

    skin_tone: str = Field(default="medium")


class UserBodyMeasurements(BaseModel):
    chest_cm: float = Field(..., ge=40, le=220)
    waist_cm: float = Field(..., ge=35, le=220)
    hip_cm: float = Field(..., ge=40, le=240)
    length_cm: Optional[float] = Field(default=None, ge=20, le=180)
    sleeve_cm: Optional[float] = Field(default=None, ge=20, le=120)
    biceps_cm: Optional[float] = Field(default=None, ge=15, le=90)
    top_length_cm: Optional[float] = Field(default=None, ge=20, le=150)
    inseam_cm: Optional[float] = Field(default=None, ge=35, le=140)
    thigh_cm: Optional[float] = Field(default=None, ge=25, le=120)
    shoulder_cm: Optional[float] = Field(default=None, ge=25, le=90)
    rise_cm: Optional[float] = Field(default=None, ge=10, le=70)
    wrist_cm: Optional[float] = Field(default=None, ge=10, le=50)
    additional_measurements: Dict[str, float] = Field(default_factory=dict)


class MannequinParams(BaseModel):
    height_cm: float
    weight_kg: float
    age: int

    chest_cm: float
    waist_cm: float
    hip_cm: float
    shoulder_cm: Optional[float] = None
    sleeve_cm: Optional[float] = None
    biceps_cm: Optional[float] = None
    top_length_cm: Optional[float] = None
    inseam_cm: Optional[float] = None
    thigh_cm: Optional[float] = None
    rise_cm: Optional[float] = None
    wrist_cm: Optional[float] = None
    additional_measurements: Dict[str, float] = Field(default_factory=dict)
    estimated_measurements: Dict[str, bool] = Field(default_factory=dict)
    skin_tone: str

    shoulder_scale: float
    chest_scale: float
    waist_scale: float
    hip_scale: float
    leg_scale: float
    arm_scale: float
    biceps_scale: float = 1.0
    thigh_scale: float = 1.0

    base_model_id: str
