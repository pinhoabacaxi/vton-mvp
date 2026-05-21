from pydantic import BaseModel, Field
from typing import List, Optional


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

    skin_tone: str = Field(default="medium")


class MannequinParams(BaseModel):
    height_cm: float
    weight_kg: float
    age: int

    chest_cm: float
    waist_cm: float
    hip_cm: float
    skin_tone: str

    shoulder_scale: float
    chest_scale: float
    waist_scale: float
    hip_scale: float
    leg_scale: float
    arm_scale: float

    base_model_id: str
