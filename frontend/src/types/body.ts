export type InitialBodyInput = {
  height_cm: number;
  weight_kg: number;
  age: number;
};

export type BodyModel = {
  id: string;
  label: string;
  description: string;
  shoulder_ratio: number;
  hip_ratio: number;
  waist_ratio: number;
  muscle_ratio: number;
  fat_ratio: number;
  recommended: boolean;
};

export type BodyRecommendationResponse = {
  input: InitialBodyInput;
  bmi: number;
  models: BodyModel[];
};

export type FineTuneInput = {
  base_model_id: string;
  height_cm: number;
  weight_kg: number;
  age: number;
  chest_cm: number;
  waist_cm: number;
  hip_cm: number;
  skin_tone: string;
};

export type MannequinParams = {
  height_cm: number;
  weight_kg: number;
  age: number;
  chest_cm: number;
  waist_cm: number;
  hip_cm: number;
  skin_tone: string;
  shoulder_scale: number;
  chest_scale: number;
  waist_scale: number;
  hip_scale: number;
  leg_scale: number;
  arm_scale: number;
  base_model_id: string;
};
