import AsyncStorage from "@react-native-async-storage/async-storage";
import { ClosetItem } from "../types/closet";

const STORAGE_KEY = "@vton_mvp_closet_items_v1";

export async function loadClosetItems(): Promise<ClosetItem[]> {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    if (!raw) return [];

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];

    return parsed as ClosetItem[];
  } catch (error) {
    return [];
  }
}

export async function saveClosetItems(items: ClosetItem[]): Promise<void> {
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

export async function addClosetItem(item: ClosetItem): Promise<ClosetItem[]> {
  const current = await loadClosetItems();
  const updated = [item, ...current];
  await saveClosetItems(updated);
  return updated;
}

export async function clearClosetItems(): Promise<void> {
  await AsyncStorage.removeItem(STORAGE_KEY);
}
