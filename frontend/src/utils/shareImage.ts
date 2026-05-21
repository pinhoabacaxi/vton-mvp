import * as FileSystem from "expo-file-system";
import * as Sharing from "expo-sharing";

function getExtensionFromUrl(url: string): string {
  const m = url.match(/\.([a-zA-Z0-9]{3,4})(?:\?|$)/);
  return m ? m[1].toLowerCase() : "jpg";
}

export async function shareImageFromUrl(imageUrl: string): Promise<void> {
  if (!imageUrl) throw new Error("No image URL provided to share.");

  const available = await Sharing.isAvailableAsync();
  if (!available) throw new Error("Sharing is not available on this device.");

  try {
    const ext = getExtensionFromUrl(imageUrl);
    const filename = `vton_${Date.now()}.${ext}`;
    const localPath = FileSystem.cacheDirectory + filename;

    const downloadRes = await FileSystem.downloadAsync(imageUrl, localPath);
    if (!downloadRes || !downloadRes.uri) {
      throw new Error("Falha ao baixar a imagem para compartilhamento.");
    }

    await Sharing.shareAsync(downloadRes.uri);
  } catch (err) {
    throw err instanceof Error ? err : new Error("Erro ao compartilhar a imagem.");
  }
}
