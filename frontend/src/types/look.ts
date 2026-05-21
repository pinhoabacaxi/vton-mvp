import { MannequinParams } from "./body";
import { FitZone, GarmentUploadResult } from "./product";
import { MannequinRenderResult as MannequinFrontRenderResult } from "./mannequin";
import { VtonPayload, VtonRunResult } from "./vton";

export type LookSource = {
  product_url?: string | null;
  affiliate_url?: string | null;
  source_name?: string | null;
  product_title?: string | null;
};

export type SavedLook = {
  id: string;
  created_at: string;
  title: string;
  mannequin: MannequinParams;
  garment?: GarmentUploadResult | null;
  front_render?: MannequinFrontRenderResult | null;
  fit_zones: FitZone[];
  vton_payload?: VtonPayload | null;
  vton_result: VtonRunResult;
  source?: LookSource | null;
};

export type SaveLookInput = {
  title?: string;
  mannequin: MannequinParams;
  garment?: GarmentUploadResult | null;
  front_render?: MannequinFrontRenderResult | null;
  fit_zones: FitZone[];
  vton_payload?: VtonPayload | null;
  vton_result: VtonRunResult;
  source?: LookSource | null;
};

export function createSavedLook(input: SaveLookInput): SavedLook {
  const id = String(Date.now()) + "-" + Math.random().toString(36).slice(2, 8);
  const created_at = new Date().toISOString();
  const title = input.title ?? `Look ${new Date(created_at).toLocaleString()}`;

  return {
    id,
    created_at,
    title,
    mannequin: input.mannequin,
    garment: input.garment ?? null,
    front_render: input.front_render ?? null,
    fit_zones: input.fit_zones,
    vton_payload: input.vton_payload ?? null,
    vton_result: input.vton_result,
    source: input.source ?? null,
  };
}
