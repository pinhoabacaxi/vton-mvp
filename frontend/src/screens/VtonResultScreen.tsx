import React, { useRef, useState } from "react";
import {
  SafeAreaView,
  ScrollView,
  View,
  Text,
  Image,
  TouchableOpacity,
  Alert,
} from "react-native";
import ViewShot from "react-native-view-shot";
import { resolveApiUrl } from "../api/client";
import { shareImageFromUrl } from "../utils/shareImage";
import { shareCapturedImage } from "../utils/shareViewShot";
import { openExternalUrl, getPreferredBuyUrl } from "../utils/openExternalUrl";
import { SocialLookCard } from "../components/SocialLookCard";
import { MannequinParams } from "../types/body";
import { FitZone, GarmentUploadResult } from "../types/product";
import { MannequinRenderResult as MannequinFrontRenderResult } from "../types/mannequin";
import { VtonPayload, VtonRunResult } from "../types/vton";
import { SaveLookInput, createSavedLook, LookSource } from "../types/look";

type Props = {
  mannequin: MannequinParams;
  garment?: GarmentUploadResult | null;
  frontRender?: MannequinFrontRenderResult | null;
  fitZones: FitZone[];
  payload?: VtonPayload | null;
  result: VtonRunResult;
  source?: LookSource | null;
  onSaveLook: (input: SaveLookInput) => void;
  onOpenHistory: () => void;
  onBackToVton: () => void;
};

export function VtonResultScreen({
  mannequin,
  garment,
  frontRender,
  fitZones,
  payload,
  result,
  source,
  onSaveLook,
  onOpenHistory,
  onBackToVton,
}: Props) {
  const [cardReady, setCardReady] = useState(false);
  const resultImageUrl = resolveApiUrl(result.result_url ?? null);
  const cardRef = useRef<ViewShot>(null);

  function InfoCard({ title, children }: { title: string; children: React.ReactNode }) {
    return (
      <View style={{ backgroundColor: "#21102f", borderRadius: 14, padding: 12, gap: 8 }}>
        <Text style={{ color: "white", fontWeight: "800", marginBottom: 6 }}>{title}</Text>
        {children}
      </View>
    );
  }

  function InfoLine({ label, value }: { label: string; value?: string | React.ReactNode }) {
    return (
      <View style={{ flexDirection: "row", justifyContent: "space-between", marginVertical: 4 }}>
        <Text style={{ color: "#d8c7ff", fontWeight: "700" }}>{label}</Text>
        <Text style={{ color: "#c4b5fd" }}>{value ?? "-"}</Text>
      </View>
    );
  }

  function colorToHex(color: string): string {
    switch (color) {
      case "red":
        return "#ef4444";
      case "yellow":
        return "#facc15";
      case "green":
        return "#22c55e";
      case "blue":
        return "#38bdf8";
      case "gray":
        return "#9ca3af";
      default:
        return "#8b5cf6";
    }
  }

  function zoneLabel(zone: string): string {
    switch (zone) {
      case "chest":
        return "Busto/Tórax";
      case "waist":
        return "Cintura";
      case "hip":
        return "Quadril";
      case "length":
        return "Comprimento";
      case "sleeve":
        return "Manga";
      case "biceps":
        return "Bíceps";
      case "top_length":
        return "Comprimento superior";
      case "inseam":
        return "Entrepernas";
      case "thigh":
        return "Coxa";
      case "shoulder":
        return "Ombros";
      default:
        return zone;
    }
  }

  function buildFitSummary(fitZones: FitZone[]): string {
    if (fitZones.length === 0) return "Caimento ainda não avaliado.";

    const tight = fitZones.filter((zone) =>
      zone.status === "apertado" || zone.status === "too_small" || zone.status === "tight" || zone.color === "red"
    ).length;

    const balanced = fitZones.filter((zone) =>
      zone.status === "justo" || zone.status === "balanced" || zone.color === "yellow"
    ).length;

    const loose = fitZones.filter((zone) =>
      zone.status === "folgado" || zone.status === "loose" || zone.color === "green" || zone.color === "blue"
    ).length;

    if (tight > 0) return "Atenção: algumas regiões podem ficar apertadas.";
    if (balanced > 0) return "Caimento próximo ao corpo.";
    if (loose > 0) return "Folga confortável na maior parte da peça.";

    return "Caimento avaliado.";
  }

  async function handleShare() {
    if (!resultImageUrl) {
      Alert.alert("Sem imagem", "Não há imagem VTON para compartilhar.");
      return;
    }

    try {
      await shareImageFromUrl(resultImageUrl);
    } catch (err) {
      Alert.alert("Erro ao compartilhar", err instanceof Error ? err.message : "Erro inesperado");
    }
  }

  async function shareCard() {
    try {
      if (!cardReady) {
        throw new Error("O card social ainda não está pronto para captura.");
      }

      const uri = await cardRef.current?.capture?.();

      if (!uri) {
        throw new Error("Não foi possível capturar o card.");
      }

      await shareCapturedImage(uri);
    } catch (error) {
      Alert.alert(
        "Erro ao compartilhar card",
        error instanceof Error ? error.message : "Erro inesperado"
      );
    }
  }

  const buyUrl = getPreferredBuyUrl(source ?? null);

  async function buy() {
    try {
      if (!buyUrl) throw new Error("URL de compra indisponível.");
      await openExternalUrl(buyUrl);
    } catch (error) {
      Alert.alert(
        "Não foi possível abrir a compra",
        error instanceof Error ? error.message : "Erro inesperado"
      );
    }
  }

  function handleSave() {
    try {
      const lookInput: SaveLookInput = {
        title: `Look ${new Date().toLocaleString()}`,
        mannequin,
        garment: garment ?? null,
        front_render: frontRender ?? null,
        fit_zones: fitZones,
        vton_payload: payload ?? null,
        vton_result: result,
        source: source ?? { product_url: null, affiliate_url: null, source_name: null, product_title: null },
      };

      onSaveLook(lookInput);
      Alert.alert("Salvo", "Look salvo no histórico local.");
    } catch (err) {
      Alert.alert("Erro", err instanceof Error ? err.message : "Erro inesperado");
    }
  }


  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#12071f" }}>
      <ScrollView contentContainerStyle={{ padding: 20, gap: 12 }}>
        <Text style={{ color: "white", fontSize: 26, fontWeight: "800" }}>Resultado VTON</Text>

        {resultImageUrl ? (
          <Image
            source={{ uri: resultImageUrl }}
            style={{ width: "100%", height: 480, borderRadius: 14, backgroundColor: "#170b25" }}
            resizeMode="contain"
          />
        ) : (
          <View style={{ backgroundColor: "#2d1b3a", padding: 24, borderRadius: 12 }}>
            <Text style={{ color: "#d8c7ff" }}>Nenhuma imagem gerada.</Text>
          </View>
        )}

        <InfoCard title="Execução">
          <InfoLine label="Provider" value={result.provider} />
          <InfoLine label="Modo pedido" value={result.mode_requested} />
          <InfoLine label="Fallback usado" value={result.used_fallback ? "sim" : "não"} />
          <InfoLine label="Sucesso" value={result.success ? "sim" : "não"} />
          <InfoLine label="Mensagem" value={result.message} />
        </InfoCard>

        {(source && (source.product_url || source.affiliate_url || source.source_name)) && (
          <InfoCard title="Origem">
            <InfoLine label="Loja / Fonte" value={source.source_name ?? "-"} />
            <InfoLine label="URL" value={source.product_url ?? "-"} />
            <InfoLine label="Affiliate" value={source.affiliate_url ?? "-"} />
          </InfoCard>
        )}

        {(source && (source.product_title || source.product_url || source.affiliate_url)) && (
          <InfoCard title="Produto">
            <InfoLine label="Produto" value={source.product_title ?? "Produto sem título"} />
            <InfoLine label="Loja" value={source.source_name ?? "-"} />
            <InfoLine label="URL original" value={source.product_url ?? "-"} />
            <InfoLine label="URL afiliada" value={source.affiliate_url ?? "-"} />

            <View style={{ marginTop: 8 }}>
              <TouchableOpacity
                onPress={buy}
                disabled={!buyUrl}
                style={{
                  backgroundColor: buyUrl ? "#7c3aed" : "#37303b",
                  padding: 12,
                  borderRadius: 10,
                  alignItems: "center",
                }}
              >
                <Text style={{ color: "white", fontWeight: "800" }}>{buyUrl ? "Comprar" : "Comprar (indisponível)"}</Text>
              </TouchableOpacity>
            </View>
          </InfoCard>
        )}

        <Text style={{ color: "white", fontSize: 20, fontWeight: "800", marginTop: 4 }}>Card social</Text>
        <ViewShot
          ref={cardRef}
          options={{ format: "png", quality: 1, result: "tmpfile" }}
          style={{ width: "100%", alignItems: "center" }}
          onLayout={() => setCardReady(true)}
        >
          <SocialLookCard
            resultImageUrl={resultImageUrl}
            title={source?.product_title ?? "Meu look virtual"}
            sourceName={source?.source_name ?? null}
            productTitle={source?.product_title ?? null}
            fitSummary={buildFitSummary(fitZones)}
            provider={result.provider}
            usedFallback={result.used_fallback}
          />
        </ViewShot>

        <TouchableOpacity onPress={shareCard} style={{ backgroundColor: "#10b981", padding: 14, borderRadius: 12, alignItems: "center" }}>
          <Text style={{ color: "white", fontWeight: "800" }}>Compartilhar card do look</Text>
        </TouchableOpacity>

        <InfoCard title="Resumo de caimento">
          <Text style={{ color: "#d8c7ff", marginBottom: 8 }}>{fitZones.length} zonas avaliadas</Text>

          {fitZones.map((z) => (
            <View key={z.zone} style={{ backgroundColor: "#2d1640", padding: 10, borderRadius: 12, marginBottom: 8, borderLeftWidth: 6, borderLeftColor: colorToHex(z.color) }}>
              <Text style={{ color: "white", fontWeight: "800" }}>{zoneLabel(z.zone)}</Text>
              <Text style={{ color: "#d8c7ff" }}>{z.message}</Text>
            </View>
          ))}
        </InfoCard>

        <View style={{ flexDirection: "row", gap: 8 }}>
          <TouchableOpacity onPress={handleSave} style={{ flex: 1, backgroundColor: "#8b5cf6", padding: 14, borderRadius: 12, alignItems: "center" }}>
            <Text style={{ color: "white", fontWeight: "800" }}>Salvar look</Text>
          </TouchableOpacity>

          <TouchableOpacity onPress={handleShare} style={{ flex: 1, backgroundColor: "#3b82f6", padding: 14, borderRadius: 12, alignItems: "center" }}>
            <Text style={{ color: "white", fontWeight: "800" }}>Compartilhar</Text>
          </TouchableOpacity>
        </View>

        <View style={{ flexDirection: "row", gap: 8 }}>
          <TouchableOpacity onPress={onOpenHistory} style={{ flex: 1, backgroundColor: "#6b7280", padding: 12, borderRadius: 12, alignItems: "center" }}>
            <Text style={{ color: "white", fontWeight: "800" }}>Histórico</Text>
          </TouchableOpacity>

          <TouchableOpacity onPress={onBackToVton} style={{ flex: 1, backgroundColor: "#374151", padding: 12, borderRadius: 12, alignItems: "center" }}>
            <Text style={{ color: "white", fontWeight: "800" }}>Voltar ao VTON</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

export default VtonResultScreen;
