import { create } from "zustand";
import { SavedLook } from "../types/look";
import { loadSavedLooks, addSavedLook, clearSavedLooks } from "../storage/lookStorage";

export type HistoryState = {
  looks: SavedLook[];
  setLooks: (looks: SavedLook[]) => void;
  loadHistory: () => Promise<void>;
  addLook: (look: SavedLook) => Promise<void>;
  clearHistory: () => Promise<void>;
};

export const useHistoryStore = create<HistoryState>()((set) => ({
  looks: [],
  setLooks: (looks) => set({ looks }),
  loadHistory: async () => {
    const loaded = await loadSavedLooks();
    set({ looks: loaded });
  },
  addLook: async (look) => {
    const updated = await addSavedLook(look);
    set({ looks: updated });
  },
  clearHistory: async () => {
    await clearSavedLooks();
    set({ looks: [] });
  },
}));
