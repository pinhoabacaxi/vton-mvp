import AsyncStorage from "@react-native-async-storage/async-storage";
import { FitCheckInput, FitCheckResult } from "../types/product";

const PREFIX = "vton_fit_cache_v1:";

export function buildFitCacheKey(input: FitCheckInput): string {
  return PREFIX + stableStringify(input);
}

export async function loadFitCache(key: string): Promise<FitCheckResult | null> {
  const raw = await AsyncStorage.getItem(key);
  if (!raw) return null;

  try {
    return JSON.parse(raw) as FitCheckResult;
  } catch {
    await AsyncStorage.removeItem(key);
    return null;
  }
}

export async function saveFitCache(key: string, result: FitCheckResult): Promise<void> {
  await AsyncStorage.setItem(key, JSON.stringify(result));
}

function stableStringify(value: unknown): string {
  return JSON.stringify(sortValue(value));
}

function sortValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value && typeof value === "object") {
    return Object.keys(value as Record<string, unknown>)
      .sort()
      .reduce<Record<string, unknown>>((acc, key) => {
        acc[key] = sortValue((value as Record<string, unknown>)[key]);
        return acc;
      }, {});
  }
  return value;
}
