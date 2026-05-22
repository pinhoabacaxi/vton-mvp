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

export type BodyModelPreview = {
  base_model_id: string;
  label: string;
  preview_url: string;
};

export type BodyModelPreviewsResponse = {
  previews: BodyModelPreview[];
};

export type FineTuneInput = {
  base_model_id: string;
  height_cm: number;
  weight_kg: number;
  age: number;
  chest_cm: number;
  waist_cm: number;
  hip_cm: number;
  shoulder_cm?: number | null;
  sleeve_cm?: number | null;
  biceps_cm?: number | null;
  top_length_cm?: number | null;
  inseam_cm?: number | null;
  thigh_cm?: number | null;
  rise_cm?: number | null;
  wrist_cm?: number | null;
  additional_measurements?: Record<string, number>;
  skin_tone: string;
};

export type MannequinParams = {
  height_cm: number;
  weight_kg: number;
  age: number;
  chest_cm: number;
  waist_cm: number;
  hip_cm: number;
  shoulder_cm?: number | null;
  sleeve_cm?: number | null;
  biceps_cm?: number | null;
  top_length_cm?: number | null;
  inseam_cm?: number | null;
  thigh_cm?: number | null;
  rise_cm?: number | null;
  wrist_cm?: number | null;
  additional_measurements?: Record<string, number>;
  estimated_measurements?: Record<string, boolean>;
  skin_tone: string;
  shoulder_scale: number;
  chest_scale: number;
  waist_scale: number;
  hip_scale: number;
  leg_scale: number;
  arm_scale: number;
  biceps_scale?: number;
  thigh_scale?: number;
  base_model_id: string;
};
