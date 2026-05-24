import { MannequinParams } from "./body";
import { FitZone } from "./product";

export type VtonRunMode = "mock" | "external" | "auto";
export type VtonTaskState = "queued" | "running" | "succeeded" | "failed";
export type VtonRenderMethod = "NEURAL_REALISTIC" | "LOCAL_FIT_DIAGRAM";

export type VtonPrepareInput = {
  mannequin: MannequinParams;
  garment_processed_url?: string | null;
  garment_original_url?: string | null;
  person_image_url?: string | null;
  user_uploaded_person_image_url?: string | null;
  fit_zones: FitZone[];
};

export type VtonPayload = {
  mannequin: MannequinParams;
  garment_processed_url?: string | null;
  garment_original_url?: string | null;
  person_image_url?: string | null;
  user_uploaded_person_image_url?: string | null;
  fit_zones: FitZone[];
  render_mode: string;
  recommended_view_count: number;
  notes: string[];
  api_ready_payload: Record<string, unknown>;
};

export type VtonMockInput = {
  payload: VtonPayload;
};

export type VtonMockResult = {
  result_url: string;
  result_path: string;
  render_method: VtonRenderMethod;
  message: string;
};

export type VtonRunInput = {
  payload: VtonPayload;
  mode: VtonRunMode;
};

export type VtonRunResult = {
  result_url?: string | null;
  result_path?: string | null;
  provider: string;
  mode_requested: VtonRunMode;
  render_method: VtonRenderMethod;
  status?: string | null;
  used_fallback: boolean;
  success: boolean;
  message: string;
  raw_response?: Record<string, unknown> | null;
};

export type VtonTaskCreated = {
  task_id: string;
  state: VtonTaskState;
  poll_after_seconds: number;
  message: string;
};

export type VtonTaskStatusResponse = {
  task_id: string;
  state: VtonTaskState;
  result?: VtonRunResult | null;
  error?: string | null;
  poll_after_seconds: number;
};

export type PersonEphemeralUploadResult = {
  person_image_url: string;
  expires_in_seconds: number;
  message: string;
};
