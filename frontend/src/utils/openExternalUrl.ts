import { Linking } from "react-native";

export function normalizeUrl(url: string): string {
  const trimmed = url.trim();

  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return trimmed;
  }

  return `https://${trimmed}`;
}

export async function openExternalUrl(url?: string | null): Promise<void> {
  if (!url || !url.trim()) {
    throw new Error("URL indisponível.");
  }

  const normalizedUrl = normalizeUrl(url);

  const canOpen = await Linking.canOpenURL(normalizedUrl);

  if (!canOpen) {
    throw new Error("Não foi possível abrir esta URL.");
  }

  await Linking.openURL(normalizedUrl);
}

export function getPreferredBuyUrl(source?: { product_url?: string | null; affiliate_url?: string | null } | null): string | null {
  if (!source) return null;

  return source.affiliate_url || source.product_url || null;
}
