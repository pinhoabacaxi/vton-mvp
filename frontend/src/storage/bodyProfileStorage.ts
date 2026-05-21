import AsyncStorage from "@react-native-async-storage/async-storage";
import { SavedBodyProfile } from "../types/bodyProfile";

const STORAGE_KEY = "@vton_mvp_body_profile_v1";

function isSavedBodyProfile(value: unknown): value is SavedBodyProfile {
  if (!value || typeof value !== "object") return false;

  const profile = value as Partial<SavedBodyProfile>;
  return Boolean(
    profile.initial_input &&
      profile.selected_model &&
      profile.mannequin &&
      profile.updated_at
  );
}

export async function loadSavedBodyProfile(): Promise<SavedBodyProfile | null> {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw);
    return isSavedBodyProfile(parsed) ? parsed : null;
  } catch (error) {
    return null;
  }
}

export async function saveSavedBodyProfile(
  profile: SavedBodyProfile
): Promise<void> {
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
}

export async function clearSavedBodyProfile(): Promise<void> {
  await AsyncStorage.removeItem(STORAGE_KEY);
}
