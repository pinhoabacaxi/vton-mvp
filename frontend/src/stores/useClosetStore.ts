import { create } from "zustand";
import { ClosetItem } from "../types/closet";
import {
  addClosetItem,
  clearClosetItems,
  loadClosetItems,
} from "../storage/closetStorage";

export type ClosetState = {
  items: ClosetItem[];
  setItems: (items: ClosetItem[]) => void;
  loadCloset: () => Promise<void>;
  addItem: (item: ClosetItem) => Promise<void>;
  clearCloset: () => Promise<void>;
};

export const useClosetStore = create<ClosetState>()((set) => ({
  items: [],
  setItems: (items) => set({ items }),
  loadCloset: async () => {
    const loaded = await loadClosetItems();
    set({ items: loaded });
  },
  addItem: async (item) => {
    const updated = await addClosetItem(item);
    set({ items: updated });
  },
  clearCloset: async () => {
    await clearClosetItems();
    set({ items: [] });
  },
}));
