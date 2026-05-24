# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_ROOT)

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.body_recommender import BASE_MODELS
from app.services.mannequin_renderer import MANNEQUIN_PREVIEW_DIR, render_body_model_preview


def main() -> None:
    MANNEQUIN_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    for body_model in BASE_MODELS:
        render_body_model_preview(body_model.id)
        print((MANNEQUIN_PREVIEW_DIR / f"{body_model.id}.png").as_posix())


if __name__ == "__main__":
    main()
