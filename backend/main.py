# -*- coding: utf-8 -*-
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.models.body import (
    InitialBodyInput,
    BodyRecommendationResponse,
    FineTuneInput,
    MannequinParams,
)
from app.models.product import (
    FitCheckInput,
    FitCheckResult,
    FitFeedbackInput,
    FitFeedbackResult,
    GarmentUploadResult,
    ProductScrapeResult,
    ProductUrlInput,
)
from app.models.vton import (
    VtonPrepareInput,
    VtonPayload,
    VtonMockInput,
    VtonMockResult,
    VtonRunInput,
    VtonRunResult,
    VtonTaskCreated,
    VtonTaskStatusResponse,
    PersonEphemeralUploadResult,
)
from app.models.mannequin import MannequinRenderInput, MannequinRenderResult
from app.services.body_recommender import (
    recommend_body_models,
    build_mannequin_params,
)

load_dotenv()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def absolute_url(path_or_url: str | None) -> str | None:
    """
    Converts local upload paths like /uploads/file.png into public URLs when
    PUBLIC_BACKEND_URL is configured.

    This is important for:
    - Android app image rendering.
    - Replicate/external VTON providers that must fetch images through HTTPS.
    """
    if not path_or_url:
        return path_or_url

    if path_or_url.startswith(("http://", "https://")):
        return path_or_url

    public_backend_url = os.getenv("PUBLIC_BACKEND_URL", "").strip()

    if not public_backend_url:
        return path_or_url

    return f"{public_backend_url.rstrip('/')}/{path_or_url.lstrip('/')}"


def absolutize_model_urls(model: Any, fields: list[str]) -> Any:
    """
    Returns a Pydantic model copy with selected URL fields converted to absolute
    URLs when those fields exist.

    Compatible with Pydantic v2 model_copy().
    """
    updates: dict[str, Any] = {}

    for field in fields:
        if hasattr(model, field):
            value = getattr(model, field)
            if isinstance(value, str) or value is None:
                updates[field] = absolute_url(value)

    if updates and hasattr(model, "model_copy"):
        return model.model_copy(update=updates)

    return model


app = FastAPI(
    title="VTON MVP Backend",
    version="0.3.3",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOAD_DIR)),
    name="uploads",
)


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "VTON MVP Backend",
    }


@app.get("/health")
def health():
    return {
        "ok": True,
    }


@app.post("/body/recommend", response_model=BodyRecommendationResponse)
def recommend_body(input_data: InitialBodyInput):
    bmi, models = recommend_body_models(input_data)

    return BodyRecommendationResponse(
        input=input_data,
        bmi=bmi,
        models=models,
    )


@app.get("/body/model-previews")
def get_body_model_previews():
    try:
        from app.services.body_recommender import BASE_MODELS
        from app.services.mannequin_renderer import render_body_model_preview

        return {
            "previews": [
                {
                    "base_model_id": body_model.id,
                    "label": body_model.label,
                    "preview_url": render_body_model_preview(body_model.id),
                }
                for body_model in BASE_MODELS
            ]
        }

    except ImportError as error:
        raise HTTPException(
            status_code=501,
            detail=(
                "Recurso indisponível: dependência ausente para previews "
                f"dos biotipos ({error})."
            ),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao gerar previews dos biotipos: {error}",
        ) from error


@app.post("/body/mannequin", response_model=MannequinParams)
def generate_mannequin_params(input_data: FineTuneInput):
    return build_mannequin_params(input_data)


@app.post("/mannequin/render-front", response_model=MannequinRenderResult)
def render_mannequin_front(input_data: MannequinRenderInput):
    try:
        # Lazy import to avoid importing Pillow at startup.
        from app.services.mannequin_renderer import render_front_mannequin

        result = render_front_mannequin(input_data)

        return absolutize_model_urls(
            result,
            fields=[
                "image_url",
            ],
        )

    except ImportError as error:
        raise HTTPException(
            status_code=501,
            detail=(
                "Recurso indisponível: dependência ausente para renderização "
                f"do manequim ({error})."
            ),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao renderizar manequim frontal: {error}",
        ) from error


@app.post("/product/scrape", response_model=ProductScrapeResult)
async def scrape_product(input_data: ProductUrlInput):
    try:
        from app.services.product_scraper import AntiBotChallengeError, scrape_product_page

        return await scrape_product_page(input_data.url)

    except AntiBotChallengeError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error

    except ImportError as error:
        raise HTTPException(
            status_code=501,
            detail=(
                "Recurso indisponível: dependência ausente para análise de "
                f"produto ({error})."
            ),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Não foi possível analisar a URL: {error}",
        ) from error


@app.post("/product/ocr-size-chart", response_model=ProductScrapeResult)
async def ocr_size_chart(file: UploadFile = File(...)):
    try:
        from app.services.vision_ocr_service import extract_size_chart_from_image

        result = await extract_size_chart_from_image(file)
        return absolutize_model_urls(result, fields=["image_url"])

    except ImportError as error:
        raise HTTPException(
            status_code=501,
            detail=(
                "Leitura automática por imagem indisponível neste ambiente. "
                "Você ainda pode preencher as medidas manualmente."
            ),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Não foi possível ler a tabela pela imagem: {error}",
        ) from error


@app.post("/garment/upload", response_model=GarmentUploadResult)
async def upload_garment(file: UploadFile = File(...)):
    try:
        # Lazy import because image processing can depend on heavier libraries.
        from app.services.image_processor import (
            save_garment_upload,
            remove_background,
            public_file_url,
        )

        filename, original_path = await save_garment_upload(file)
        processed_filename, processed_path = remove_background(original_path)

        background_removed = processed_filename.endswith("_nobg.png")

        result = GarmentUploadResult(
            filename=filename,
            content_type=file.content_type or "application/octet-stream",
            original_path=original_path,
            processed_path=processed_path,
            original_url=public_file_url(original_path),
            processed_url=public_file_url(processed_path),
            background_removed=background_removed,
            message=(
                "Imagem recebida e fundo removido com sucesso."
                if background_removed
                else "Imagem recebida e otimizada sem remoção de fundo."
            ),
        )

        return absolutize_model_urls(
            result,
            fields=[
                "original_url",
                "processed_url",
            ],
        )

    except ImportError as error:
        raise HTTPException(
            status_code=501,
            detail=(
                "Recurso indisponível: dependência ausente para processamento "
                f"de imagem ({error})."
            ),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao processar imagem: {error}",
        ) from error


@app.post("/person/upload-ephemeral", response_model=PersonEphemeralUploadResult)
async def upload_ephemeral_person(file: UploadFile = File(...)):
    try:
        from app.services.person_image_store import save_ephemeral_person_upload

        reference, expires_in_seconds = await save_ephemeral_person_upload(file)
        return PersonEphemeralUploadResult(
            person_image_url=reference,
            expires_in_seconds=expires_in_seconds,
            message=(
                "Foto recebida para esta sessão. Ela será removida do servidor "
                "automaticamente após a geração da prévia ou ao expirar."
            ),
        )

    except ImportError as error:
        raise HTTPException(
            status_code=501,
            detail=(
                "Recurso indisponível: dependência ausente para preparar "
                f"foto de pessoa ({error})."
            ),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Não foi possível preparar a foto: {error}",
        ) from error


@app.post("/fit/check", response_model=FitCheckResult)
def check_fit(input_data: FitCheckInput):
    try:
        from app.services.size_normalizer import evaluate_fit

        return evaluate_fit(input_data)

    except ImportError as error:
        raise HTTPException(
            status_code=501,
            detail=(
                "Recurso indisponível: dependência ausente para análise de "
                f"caimento ({error})."
            ),
        ) from error


@app.post("/fit/feedback", response_model=FitFeedbackResult)
def fit_feedback(input_data: FitFeedbackInput):
    try:
        from app.services.fit_feedback import record_fit_feedback

        return record_fit_feedback(input_data)

    except ImportError as error:
        raise HTTPException(
            status_code=501,
            detail=(
                "Recurso indisponível: dependência ausente para feedback de "
                f"caimento ({error})."
            ),
        ) from error


@app.post("/vton/prepare", response_model=VtonPayload)
def prepare_vton(input_data: VtonPrepareInput):
    try:
        from app.services.vton_service import prepare_vton_payload

        result = prepare_vton_payload(input_data)

        return absolutize_model_urls(
            result,
            fields=[
                "garment_processed_url",
                "garment_original_url",
                "person_image_url",
            ],
        )

    except ImportError as error:
        raise HTTPException(
            status_code=501,
            detail=(
                "Recurso indisponível: dependência ausente para preparação "
                f"do VTON ({error})."
            ),
        ) from error


@app.post("/vton/mock", response_model=VtonMockResult)
def mock_vton(input_data: VtonMockInput):
    try:
        from app.services.vton_service import create_mock_vton_result

        result = create_mock_vton_result(input_data)

        return absolutize_model_urls(
            result,
            fields=[
                "result_url",
            ],
        )

    except ImportError as error:
        raise HTTPException(
            status_code=501,
            detail=(
                "Recurso indisponível: dependência ausente para VTON mock "
                f"({error})."
            ),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao gerar VTON mock: {error}",
        ) from error


@app.post("/vton/run", response_model=VtonRunResult)
async def run_vton_endpoint(input_data: VtonRunInput):
    try:
        from app.services.vton_service import run_vton

        result = await run_vton(input_data)

        return absolutize_model_urls(
            result,
            fields=[
                "result_url",
            ],
        )

    except ImportError as error:
        raise HTTPException(
            status_code=501,
            detail=(
                "Recurso indisponível: dependência ausente para executar "
                f"VTON ({error})."
            ),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao executar VTON: {error}",
        ) from error


@app.post("/vton/tasks", response_model=VtonTaskCreated)
async def create_vton_task_endpoint(input_data: VtonRunInput):
    try:
        from app.services.vton_service import create_vton_task

        return create_vton_task(input_data)

    except ImportError as error:
        raise HTTPException(
            status_code=501,
            detail=(
                "Recurso indisponível: dependência ausente para criar tarefa "
                f"VTON ({error})."
            ),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail=f"Não foi possível iniciar a tarefa VTON: {error}",
        ) from error


@app.get("/vton/tasks/{task_id}", response_model=VtonTaskStatusResponse)
def get_vton_task_endpoint(task_id: str):
    try:
        from app.services.vton_service import get_vton_task

        task = get_vton_task(task_id)

        if not task:
            raise HTTPException(
                status_code=404,
                detail="Tarefa VTON não encontrada.",
            )

        if task.result:
            task = task.model_copy(
                update={
                    "result": absolutize_model_urls(
                        task.result,
                        fields=[
                            "result_url",
                        ],
                    )
                }
            )

        return task

    except HTTPException:
        raise

    except ImportError as error:
        raise HTTPException(
            status_code=501,
            detail=(
                "Recurso indisponível: dependência ausente para consultar "
                f"status da tarefa VTON ({error})."
            ),
        ) from error
