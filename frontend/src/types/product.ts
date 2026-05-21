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
};

export type ProductScrapeResult = {
  source_url: string;
  title: string;
  image_url?: string | null;
  currency?: string | null;
  price?: string | null;
  raw_size_text?: string | null;
  normalized_sizes: SizeMeasurement[];
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
  garment_size: SizeMeasurement;
};

export type FitZone = {
  zone: "chest" | "waist" | "hip" | string;
  difference_cm?: number | null;
  status: "too_small" | "tight" | "balanced" | "loose" | "unknown" | string;
  color: "red" | "yellow" | "green" | "gray" | string;
  message: string;
};

export type FitCheckResult = {
  zones: FitZone[];
  summary: string;
};
