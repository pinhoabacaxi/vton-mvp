import os

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
    ProductUrlInput,
    ProductScrapeResult,
    GarmentUploadResult,
    FitCheckInput,
    FitCheckResult,
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
)
from app.models.mannequin import MannequinRenderInput, MannequinRenderResult
from app.services.body_recommender import (
    recommend_body_models,
    build_mannequin_params,
)

# Avoid importing heavy optional modules (Pillow, rembg, onnxruntime, etc.) at
# startup. We'll import them lazily inside the endpoints that need them so the
# app can start in constrained environments and return a clear error if a
# feature requires additional dependencies.

# Provide a local UPLOAD_DIR for mounting static files. The image processor
# module will create its own directories when imported lazily inside upload
# endpoint.
from pathlib import Path

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv()

app = FastAPI(
    title="VTON MVP Backend",
    version="0.3.2",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/body/recommend", response_model=BodyRecommendationResponse)
def recommend_body(input_data: InitialBodyInput):
    bmi, models = recommend_body_models(input_data)

    return BodyRecommendationResponse(
        input=input_data,
        bmi=bmi,
        models=models,
    )


@app.post("/body/mannequin", response_model=MannequinParams)
def generate_mannequin_params(input_data: FineTuneInput):
    return build_mannequin_params(input_data)


@app.post("/mannequin/render-front", response_model=MannequinRenderResult)
def render_mannequin_front(input_data: MannequinRenderInput):
    try:
        # Lazy import to avoid importing PIL at startup
        from app.services.mannequin_renderer import render_front_mannequin

        return render_front_mannequin(input_data)
    except ImportError as ie:
        raise HTTPException(
            status_code=501,
            detail=f"Feature unavailable: missing dependency for mannequin rendering ({ie}).",
        )
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao renderizar manequim frontal: {error}",
        )


@app.post("/product/scrape", response_model=ProductScrapeResult)
async def scrape_product(input_data: ProductUrlInput):
    try:
        # Lazy import to avoid heavy deps at startup
        from app.services.product_scraper import scrape_product_page

        return await scrape_product_page(input_data.url)
    except ImportError as ie:
        raise HTTPException(
            status_code=501,
            detail=f"Feature unavailable: missing dependency for product scraping ({ie}).",
        )
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Não foi possível analisar a URL: {error}",
        )


@app.post("/garment/upload", response_model=GarmentUploadResult)
async def upload_garment(file: UploadFile = File(...)):
    try:
        # Lazy import image processing utilities which may require heavy
        # dependencies (Pillow/rembg). Importing lazily allows the API to run
        # in environments where these optional dependencies are not installed.
        from app.services.image_processor import save_garment_upload, remove_background, public_file_url

        filename, original_path = await save_garment_upload(file)
        processed_filename, processed_path = remove_background(original_path)
        background_removed = os.getenv("DISABLE_REMBG", "").strip().lower() != "true"

        return GarmentUploadResult(
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
                else "Imagem recebida e otimizada sem rembg."
            ),
        )

    except ImportError as ie:
        raise HTTPException(
            status_code=501,
            detail=f"Feature unavailable: missing dependency for image processing ({ie}).",
        )
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao processar imagem: {error}",
        )


@app.post("/fit/check", response_model=FitCheckResult)
def check_fit(input_data: FitCheckInput):
    try:
        from app.services.size_normalizer import evaluate_fit

        return evaluate_fit(input_data)
    except ImportError as ie:
        raise HTTPException(
            status_code=501,
            detail=f"Feature unavailable: missing dependency for fit check ({ie}).",
        )


@app.post("/vton/prepare", response_model=VtonPayload)
def prepare_vton(input_data: VtonPrepareInput):
    try:
        from app.services.vton_service import prepare_vton_payload

        return prepare_vton_payload(input_data)
    except ImportError as ie:
        raise HTTPException(
            status_code=501,
            detail=f"Feature unavailable: missing dependency for VTON payload preparation ({ie}).",
        )


@app.post("/vton/mock", response_model=VtonMockResult)
def mock_vton(input_data: VtonMockInput):
    try:
        from app.services.vton_service import create_mock_vton_result

        return create_mock_vton_result(input_data)
    except ImportError as ie:
        raise HTTPException(
            status_code=501,
            detail=f"Feature unavailable: missing dependency for VTON mock ({ie}).",
        )
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao gerar VTON mock: {error}",
        )


@app.post("/vton/run", response_model=VtonRunResult)
async def run_vton_endpoint(input_data: VtonRunInput):
    try:
        from app.services.vton_service import run_vton

        return await run_vton(input_data)
    except ImportError as ie:
        raise HTTPException(
            status_code=501,
            detail=f"Feature unavailable: missing dependency for VTON run ({ie}).",
        )
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao executar VTON: {error}",
        )


@app.post("/vton/tasks", response_model=VtonTaskCreated)
async def create_vton_task_endpoint(input_data: VtonRunInput):
    try:
        from app.services.vton_service import create_vton_task

        return create_vton_task(input_data)
    except ImportError as ie:
        raise HTTPException(
            status_code=501,
            detail=f"Feature unavailable: missing dependency for VTON task ({ie}).",
        )
    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail=f"Nao foi possivel iniciar a tarefa VTON: {error}",
        )


@app.get("/vton/tasks/{task_id}", response_model=VtonTaskStatusResponse)
def get_vton_task_endpoint(task_id: str):
    try:
        from app.services.vton_service import get_vton_task

        task = get_vton_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Tarefa VTON nao encontrada.")

        return task
    except HTTPException:
        raise
    except ImportError as ie:
        raise HTTPException(
            status_code=501,
            detail=f"Feature unavailable: missing dependency for VTON task status ({ie}).",
        )
