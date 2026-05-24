import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { InitialBodyInput, BodyRecommendationResponse, BodyModel, MannequinParams } from "../types/body";
import { GarmentUploadResult, FitCheckResult, ProductScrapeResult } from "../types/product";
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
  productDetails: ProductScrapeResult | null;
  garment: GarmentUploadResult | null;
  fitCheckResult: FitCheckResult | null;
  frontRender: MannequinRenderResult | null;
  vtonPayload: VtonPayload | null;
  vtonResult: VtonRunResult | null;
  setInitialInput: (value: InitialBodyInput | null) => void;
  setRecommendation: (value: BodyRecommendationResponse | null) => void;
  setSelectedModel: (value: BodyModel | null) => void;
  setMannequin: (value: MannequinParams | null) => void;
  setProductUrl: (value: string | null) => void;
  setProductSource: (value: LookSource | null) => void;
  setProductDetails: (value: ProductScrapeResult | null) => void;
  setGarment: (value: GarmentUploadResult | null) => void;
  setFitCheckResult: (value: FitCheckResult | null) => void;
  setFrontRender: (value: MannequinRenderResult | null) => void;
  setVtonPayload: (value: VtonPayload | null) => void;
  setVtonResult: (value: VtonRunResult | null) => void;
  resetFlow: () => void;
};

const emptyFlow = {
  initialInput: null,
  recommendation: null,
  selectedModel: null,
  mannequin: null,
  productUrl: null,
  productSource: null,
  productDetails: null,
  garment: null,
  fitCheckResult: null,
  frontRender: null,
  vtonPayload: null,
  vtonResult: null,
};

export const useVtonStore = create<VtonState>()(
  persist(
    (set) => ({
      ...emptyFlow,
      setInitialInput: (value) => set({ initialInput: value }),
      setRecommendation: (value) => set({ recommendation: value }),
      setSelectedModel: (value) => set({ selectedModel: value }),
      setMannequin: (value) => set({ mannequin: value }),
      setProductUrl: (value) => set({ productUrl: value }),
      setProductSource: (value) => set({ productSource: value }),
      setProductDetails: (value) => set({ productDetails: value }),
      setGarment: (value) => set({ garment: value }),
      setFitCheckResult: (value) => set({ fitCheckResult: value }),
      setFrontRender: (value) => set({ frontRender: value }),
      setVtonPayload: (value) => set({ vtonPayload: value }),
      setVtonResult: (value) => set({ vtonResult: value }),
      resetFlow: () => set({ ...emptyFlow }),
    }),
    {
      name: "vton-flow-state-v2",
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({
        initialInput: state.initialInput,
        recommendation: state.recommendation,
        selectedModel: state.selectedModel,
        mannequin: state.mannequin,
        productUrl: state.productUrl,
        productSource: state.productSource,
        productDetails: state.productDetails,
        garment: state.garment,
        fitCheckResult: state.fitCheckResult,
        frontRender: state.frontRender,
        vtonPayload: state.vtonPayload,
        vtonResult: state.vtonResult,
      }),
    }
  )
);
