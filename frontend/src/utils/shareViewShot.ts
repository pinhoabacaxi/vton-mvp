import * as Sharing from "expo-sharing";

export async function shareCapturedImage(uri: string): Promise<void> {
  const canShare = await Sharing.isAvailableAsync();

  if (!canShare) {
    throw new Error("Compartilhamento não disponível neste dispositivo.");
  }

  if (!uri) {
    throw new Error("Imagem capturada inválida.");
  }

  await Sharing.shareAsync(uri, {
    mimeType: "image/png",
    dialogTitle: "Compartilhar look",
  });
}
