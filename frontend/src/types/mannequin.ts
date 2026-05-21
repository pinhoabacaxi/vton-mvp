import { MannequinParams } from "./body";

export type MannequinRenderInput = {
  mannequin: MannequinParams;
};

export type MannequinRenderResult = {
  image_url: string;
  image_path: string;
  message: string;
};
