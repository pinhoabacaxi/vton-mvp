import { create } from "zustand";
import { InitialBodyInput, BodyRecommendationResponse, BodyModel, FineTuneInput, MannequinParams } from "../types/body";
import { GarmentUploadResult, FitCheckResult } from "../types/product";
import { MannequinRenderResult } from "../types/mannequin";
import { VtonPayload, VtonRunResult } from "../types/vton";
import { LookSource } from "../types/look";

export type VtonState = {
  initialInput: InitialBodyInput | null;
  recommendation: BodyRecommendationResponse | null;
  selectedModel: BodyModel | null;
  mannequin: MannequinParams | null;
  productUrl: string | null;
  productSource: LookSource | null;
  garment: GarmentUploadResult | null;
  fitCheckResult: FitCheckResult | null;
  frontRender: MannequinRenderResult | null;
  vtonPayload: VtonPayload | null;
  vtonResult: VtonRunResult | null;
  setInitialInput: (value: InitialBodyInput) => void;
  setRecommendation: (value: BodyRecommendationResponse | null) => void;
  setSelectedModel: (value: BodyModel | null) => void;
  setMannequin: (value: MannequinParams | null) => void;
  setProductUrl: (value: string | null) => void;
  setProductSource: (value: LookSource | null) => void;
  setGarment: (value: GarmentUploadResult | null) => void;
  setFitCheckResult: (value: FitCheckResult | null) => void;
  setFrontRender: (value: MannequinRenderResult | null) => void;
  setVtonPayload: (value: VtonPayload | null) => void;
  setVtonResult: (value: VtonRunResult | null) => void;
  resetFlow: () => void;
};

export const useVtonStore = create<VtonState>()((set) => ({
  initialInput: null,
  recommendation: null,
  selectedModel: null,
  mannequin: null,
  productUrl: null,
  productSource: null,
  garment: null,
  fitCheckResult: null,
  frontRender: null,
  vtonPayload: null,
  vtonResult: null,
  setInitialInput: (value) => set({ initialInput: value }),
  setRecommendation: (value) => set({ recommendation: value }),
  setSelectedModel: (value) => set({ selectedModel: value }),
  setMannequin: (value) => set({ mannequin: value }),
  setProductUrl: (value) => set({ productUrl: value }),
  setProductSource: (value) => set({ productSource: value }),
  setGarment: (value) => set({ garment: value }),
  setFitCheckResult: (value) => set({ fitCheckResult: value }),
  setFrontRender: (value) => set({ frontRender: value }),
  setVtonPayload: (value) => set({ vtonPayload: value }),
  setVtonResult: (value) => set({ vtonResult: value }),
  resetFlow: () =>
    set({
      initialInput: null,
      recommendation: null,
      selectedModel: null,
      mannequin: null,
      productUrl: null,
      productSource: null,
      garment: null,
      fitCheckResult: null,
      frontRender: null,
      vtonPayload: null,
      vtonResult: null,
    }),
}));
