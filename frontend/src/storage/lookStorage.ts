import AsyncStorage from '@react-native-async-storage/async-storage';
import { SavedLook } from '../types/look';

const STORAGE_KEY = '@vton_mvp_saved_looks_v1';

export async function loadSavedLooks(): Promise<SavedLook[]> {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    if (!raw) return [];

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];

    return parsed as SavedLook[];
  } catch (err) {
    return [];
  }
}

export async function saveSavedLooks(looks: SavedLook[]): Promise<void> {
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(looks));
}

export async function addSavedLook(look: SavedLook): Promise<SavedLook[]> {
  const current = await loadSavedLooks();
  const updated = [look, ...current];
  await saveSavedLooks(updated);
  return updated;
}

export async function clearSavedLooks(): Promise<void> {
  await AsyncStorage.removeItem(STORAGE_KEY);
}
