export type ProductUrlInput = {
  url: string;
};

export type SizeMeasurement = {
  size_label: string;
  chest_cm?: number | null;
  waist_cm?: number | null;
  hip_cm?: number | null;
  length_cm?: number | null;
  shoulder_cm?: number | null;
  sleeve_cm?: number | null;
  biceps_cm?: number | null;
  top_length_cm?: number | null;
  inseam_cm?: number | null;
  thigh_cm?: number | null;
  rise_cm?: number | null;
  wrist_cm?: number | null;
  garment_category?: string | null;
  stretch_level?: string | null;
  additional_measurements?: Record<string, number>;
  is_estimated?: boolean;
  estimated_from_size?: string | null;
  confidence?: number | null;
};

export type FabricAnalysis = {
  raw_text?: string | null;
  stretch_factor: number;
  shrink_risk: number;
  drape_factor: number;
  detected_fibers: string[];
  warnings: string[];
};

export type ProductScrapeResult = {
  source_url: string;
  title: string;
  image_url?: string | null;
  currency?: string | null;
  price?: string | null;
  raw_size_text?: string | null;
  normalized_sizes: SizeMeasurement[];
  fabric_composition_text?: string | null;
  fabric_analysis?: FabricAnalysis | null;
  confidence_score?: number | null;
  extraction_method?: string | null;
  fallback_reason?: string | null;
  blocked_by_antibot?: boolean;
};

export type GarmentUploadResult = {
  filename: string;
  content_type: string;
  original_path: string;
  processed_path?: string | null;
  original_url?: string | null;
  processed_url?: string | null;
  background_removed: boolean;
  message: string;
};

export type FitCheckInput = {
  user_chest_cm: number;
  user_waist_cm: number;
  user_hip_cm: number;
  user_length_cm?: number | null;
  user_sleeve_cm?: number | null;
  user_biceps_cm?: number | null;
  user_top_length_cm?: number | null;
  user_inseam_cm?: number | null;
  user_thigh_cm?: number | null;
  user_shoulder_cm?: number | null;
  user_rise_cm?: number | null;
  user_wrist_cm?: number | null;
  garment_size: SizeMeasurement;
  candidate_sizes?: SizeMeasurement[];
  garment_category?: string | null;
  stretch_level?: string | null;
  fabric_analysis?: FabricAnalysis | null;
  user_ease_modifier?: number;
};

export type FitZone = {
  zone: string;
  difference_cm?: number | null;
  status:
    | "apertado"
    | "justo"
    | "folgado"
    | "sem_informacao"
    | "too_small"
    | "tight"
    | "balanced"
    | "loose"
    | "unknown"
    | string;
  color: "red" | "yellow" | "green" | "blue" | "gray" | string;
  message: string;
  body_cm?: number | null;
  garment_cm?: number | null;
  ease_allowance_cm?: number | null;
  pressure_score?: number | null;
  fabric_warning?: string | null;
};

export type FitSizeOption = {
  size_label: string;
  score: number;
  zones: FitZone[];
  summary: string;
  is_estimated: boolean;
  is_best_match: boolean;
};

export type FitCheckResult = {
  zones: FitZone[];
  summary: string;
  best_size_label?: string | null;
  selected_size_label?: string | null;
  size_options?: FitSizeOption[];
  fabric_warnings?: string[];
  cache_key?: string | null;
  cache_hit?: boolean;
};

export type FitFeedbackInput = {
  user_key?: string;
  predicted_status: string;
  reported_status: string;
  zone?: string | null;
};

export type FitFeedbackResult = {
  user_key: string;
  user_ease_modifier: number;
  message: string;
};
