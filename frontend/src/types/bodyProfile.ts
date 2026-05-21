import { BodyModel, InitialBodyInput, MannequinParams } from "./body";

export type SavedBodyProfile = {
  initial_input: InitialBodyInput;
  selected_model: BodyModel;
  mannequin: MannequinParams;
  updated_at: string;
};
