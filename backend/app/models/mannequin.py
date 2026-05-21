from pydantic import BaseModel

from app.models.body import MannequinParams


class MannequinRenderInput(BaseModel):
    mannequin: MannequinParams


class MannequinRenderResult(BaseModel):
    image_url: str
    image_path: str
    message: str
