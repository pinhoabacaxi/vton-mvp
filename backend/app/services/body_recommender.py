from app.models.body import InitialBodyInput, BodyModel, FineTuneInput, MannequinParams


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
        label="Ombros largos",
        description="Ombros mais presentes, quadril moderado e tronco definido.",
        shoulder_ratio=1.14,
        hip_ratio=0.94,
        waist_ratio=0.78,
        muscle_ratio=0.62,
        fat_ratio=0.38,
    ),
    BodyModel(
        id="wide_hip",
        label="Quadril amplo",
        description="Quadril mais amplo, ombros moderados e cintura destacada.",
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
        description="Mais massa muscular relativa e cintura firme.",
        shoulder_ratio=1.08,
        hip_ratio=0.98,
        waist_ratio=0.74,
        muscle_ratio=0.72,
        fat_ratio=0.28,
    ),
    BodyModel(
        id="full_soft",
        label="Volume macio",
        description="Maior volume corporal geral, curvas suaves e proporções cheias.",
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

        models.append(
            model.model_copy(
                update={
                    "recommended": recommended
                }
            )
        )

    models = sorted(models, key=lambda item: item.recommended, reverse=True)

    return bmi, models


def build_mannequin_params(data: FineTuneInput) -> MannequinParams:
    base = next(
        (model for model in BASE_MODELS if model.id == data.base_model_id),
        BASE_MODELS[0],
    )

    chest_scale = data.chest_cm / 95
    waist_scale = data.waist_cm / 80
    hip_scale = data.hip_cm / 98

    height_scale = data.height_cm / 170

    return MannequinParams(
        height_cm=data.height_cm,
        weight_kg=data.weight_kg,
        age=data.age,
        chest_cm=data.chest_cm,
        waist_cm=data.waist_cm,
        hip_cm=data.hip_cm,
        skin_tone=data.skin_tone,
        shoulder_scale=round(base.shoulder_ratio * chest_scale, 3),
        chest_scale=round(chest_scale, 3),
        waist_scale=round(base.waist_ratio * waist_scale, 3),
        hip_scale=round(base.hip_ratio * hip_scale, 3),
        leg_scale=round(height_scale, 3),
        arm_scale=round(height_scale * base.shoulder_ratio, 3),
        base_model_id=data.base_model_id,
    )
