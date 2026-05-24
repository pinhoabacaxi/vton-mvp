from app.models.body import BodyModel, FineTuneInput, InitialBodyInput, MannequinParams
from app.services.anthropometric_estimator import estimate_missing_measurements


BASE_MODELS = [
    BodyModel(
        id="balanced_soft",
        label="Equilibrado suave",
        description="Proporções equilibradas, cintura suave e volume corporal médio.",
        shoulder_ratio=1.00,
        hip_ratio=1.00,
        waist_ratio=0.82,
        muscle_ratio=0.45,
        fat_ratio=0.55,
    ),
    BodyModel(
        id="wide_shoulder",
        label="Ombros presentes",
        description="Linha de ombros mais marcada, quadril moderado e tronco definido.",
        shoulder_ratio=1.14,
        hip_ratio=0.94,
        waist_ratio=0.78,
        muscle_ratio=0.62,
        fat_ratio=0.38,
    ),
    BodyModel(
        id="wide_hip",
        label="Quadril marcante",
        description="Quadril mais presente, ombros moderados e cintura destacada.",
        shoulder_ratio=0.94,
        hip_ratio=1.16,
        waist_ratio=0.76,
        muscle_ratio=0.42,
        fat_ratio=0.58,
    ),
    BodyModel(
        id="straight_frame",
        label="Estrutura reta",
        description="Ombros, cintura e quadril com pouca variação proporcional.",
        shoulder_ratio=1.00,
        hip_ratio=1.00,
        waist_ratio=0.92,
        muscle_ratio=0.50,
        fat_ratio=0.50,
    ),
    BodyModel(
        id="athletic_compact",
        label="Atlético compacto",
        description="Estrutura compacta, cintura firme e presença muscular relativa.",
        shoulder_ratio=1.08,
        hip_ratio=0.98,
        waist_ratio=0.74,
        muscle_ratio=0.72,
        fat_ratio=0.28,
    ),
    BodyModel(
        id="full_soft",
        label="Curvas suaves",
        description="Volume corporal geral maior, curvas suaves e proporções cheias.",
        shoulder_ratio=1.04,
        hip_ratio=1.08,
        waist_ratio=0.90,
        muscle_ratio=0.35,
        fat_ratio=0.65,
    ),
]


def calculate_bmi(height_cm: float, weight_kg: float) -> float:
    height_m = height_cm / 100
    return round(weight_kg / (height_m * height_m), 2)


def recommend_body_models(user_input: InitialBodyInput):
    """Recommend starting silhouettes from measurements without asking for gender."""

    bmi = calculate_bmi(user_input.height_cm, user_input.weight_kg)
    models = []

    for model in BASE_MODELS:
        recommended = False

        if bmi < 20 and model.id in ["straight_frame", "athletic_compact"]:
            recommended = True
        elif 20 <= bmi < 27 and model.id in ["balanced_soft", "wide_shoulder", "wide_hip"]:
            recommended = True
        elif bmi >= 27 and model.id in ["full_soft", "balanced_soft", "wide_hip"]:
            recommended = True

        models.append(model.model_copy(update={"recommended": recommended}))

    models = sorted(models, key=lambda item: item.recommended, reverse=True)
    return bmi, models


def build_mannequin_params(data: FineTuneInput) -> MannequinParams:
    base = next(
        (model for model in BASE_MODELS if model.id == data.base_model_id),
        BASE_MODELS[0],
    )

    inferred, estimated_flags = estimate_missing_measurements(data)

    chest_scale = data.chest_cm / 95
    waist_scale = data.waist_cm / 80
    hip_scale = data.hip_cm / 98
    height_scale = data.height_cm / 170
    shoulder_scale = inferred["shoulder_cm"] / 42
    biceps_scale = inferred["biceps_cm"] / 32
    thigh_scale = inferred["thigh_cm"] / 58
    inseam_scale = inferred["inseam_cm"] / 78
    sleeve_scale = inferred["sleeve_cm"] / 60

    return MannequinParams(
        height_cm=data.height_cm,
        weight_kg=data.weight_kg,
        age=data.age,
        chest_cm=data.chest_cm,
        waist_cm=data.waist_cm,
        hip_cm=data.hip_cm,
        shoulder_cm=inferred["shoulder_cm"],
        sleeve_cm=inferred["sleeve_cm"],
        biceps_cm=inferred["biceps_cm"],
        top_length_cm=inferred["top_length_cm"],
        inseam_cm=inferred["inseam_cm"],
        thigh_cm=inferred["thigh_cm"],
        rise_cm=inferred["rise_cm"],
        wrist_cm=inferred["wrist_cm"],
        additional_measurements=data.additional_measurements,
        estimated_measurements=estimated_flags,
        skin_tone=data.skin_tone,
        shoulder_scale=round(base.shoulder_ratio * shoulder_scale, 3),
        chest_scale=round(chest_scale, 3),
        waist_scale=round(base.waist_ratio * waist_scale, 3),
        hip_scale=round(base.hip_ratio * hip_scale, 3),
        leg_scale=round((height_scale * 0.45) + (inseam_scale * 0.55), 3),
        arm_scale=round((sleeve_scale * 0.65) + (base.shoulder_ratio * 0.35), 3),
        biceps_scale=round(biceps_scale, 3),
        thigh_scale=round(thigh_scale, 3),
        base_model_id=data.base_model_id,
    )
