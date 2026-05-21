import { LookSource } from "./look";
import { GarmentUploadResult } from "./product";

export type ClosetItem = {
  id: string;
  created_at: string;
  title: string;
  garment: GarmentUploadResult;
  source?: LookSource | null;
};

export type SaveClosetItemInput = {
  title?: string;
  garment: GarmentUploadResult;
  source?: LookSource | null;
};

export function createClosetItem(input: SaveClosetItemInput): ClosetItem {
  const created_at = new Date().toISOString();

  return {
    id: String(Date.now()) + "-" + Math.random().toString(36).slice(2, 8),
    created_at,
    title:
      input.title ??
      input.source?.product_title ??
      input.source?.source_name ??
      `Peca ${new Date(created_at).toLocaleString()}`,
    garment: input.garment,
    source: input.source ?? null,
  };
}
