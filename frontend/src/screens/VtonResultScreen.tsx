import React, { useRef, useState } from "react";
import {
  Alert,
  Image,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import ViewShot from "react-native-view-shot";
import { resolveApiUrl } from "../api/client";
import { shareImageFromUrl } from "../utils/shareImage";
import { shareCapturedImage } from "../utils/shareViewShot";
import { openExternalUrl, getPreferredBuyUrl } from "../utils/openExternalUrl";
import { SocialLookCard } from "../components/SocialLookCard";
import {
  AppScreen,
  FashionCard,
  InfoPill,
  JourneyStepper,
  PrimaryButton,
  SecondaryButton,
  StepHeader,
  fashionColors,
} from "../components/FashionUI";
import { MannequinParams } from "../types/body";
import { FitZone, GarmentUploadResult } from "../types/product";
import { MannequinRenderResult as MannequinFrontRenderResult } from "../types/mannequin";
import { VtonPayload, VtonRunResult } from "../types/vton";
import { SaveLookInput, LookSource } from "../types/look";

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
  const buyUrl = getPreferredBuyUrl(source ?? null);
  const fitSummary = buildFitSummary(fitZones);

  async function handleShare() {
    if (!resultImageUrl) {
      Alert.alert("Sem imagem para compartilhar", "Gere uma nova prévia do look e tente novamente.");
      return;
    }

    try {
      await shareImageFromUrl(resultImageUrl);
    } catch (err) {
      Alert.alert("Não foi possível compartilhar", err instanceof Error ? err.message : "Tente novamente em instantes.");
    }
  }

  async function shareCard() {
    try {
      if (!cardReady) {
        throw new Error("O card ainda está sendo preparado.");
      }

      const uri = await cardRef.current?.capture?.();

      if (!uri) {
        throw new Error("Não conseguimos capturar o card.");
      }

      await shareCapturedImage(uri);
    } catch (error) {
      Alert.alert(
        "Não foi possível compartilhar o card",
        error instanceof Error ? error.message : "Tente novamente em instantes."
      );
    }
  }

  async function buy() {
    try {
      if (!buyUrl) throw new Error("Link de compra indisponível.");
      await openExternalUrl(buyUrl);
    } catch (error) {
      Alert.alert(
        "Não foi possível abrir a compra",
        error instanceof Error ? error.message : "Tente novamente em instantes."
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
    } catch (err) {
      Alert.alert("Não foi possível salvar", err instanceof Error ? err.message : "Tente novamente em instantes.");
    }
  }

  return (
    <AppScreen>
      <ScrollView contentContainerStyle={{ padding: 20, gap: 14 }}>
        <StepHeader
          eyebrow="Resultado"
          title="Seu look virtual"
          subtitle="Prévia estimada para visualizar proporção, estilo e pontos de caimento. O tecido, o corte e a foto original podem mudar o resultado real."
        />
        <JourneyStepper activeStep="look" />

        <InfoPill label="Prévia estimada" tone="gold" />

        {resultImageUrl ? (
          <Image
            source={{ uri: resultImageUrl }}
            style={{ width: "100%", height: 480, borderRadius: 18, backgroundColor: "#170b25" }}
            resizeMode="contain"
          />
        ) : (
          <FashionCard>
            <Text style={{ color: fashionColors.textSoft }}>Nenhuma imagem foi gerada para este look.</Text>
          </FashionCard>
        )}

        <FashionCard highlighted>
          <Text style={{ color: fashionColors.text, fontWeight: "900", fontSize: 18 }}>
            Resumo do caimento
          </Text>
          <Text style={{ color: fashionColors.textSoft, lineHeight: 22 }}>
            {fitSummary}
          </Text>

          {fitZones.length > 0 ? (
            <View style={{ gap: 8 }}>
              {fitZones.map((z) => (
                <View
                  key={z.zone}
                  style={{
                    backgroundColor: "#2d1640",
                    padding: 10,
                    borderRadius: 12,
                    borderLeftWidth: 6,
                    borderLeftColor: colorToHex(z.color),
                  }}
                >
                  <Text style={{ color: fashionColors.text, fontWeight: "900" }}>{zoneLabel(z.zone)}</Text>
                  <Text style={{ color: fashionColors.textSoft, lineHeight: 20 }}>{humanizeZoneMessage(z)}</Text>
                </View>
              ))}
            </View>
          ) : (
            <Text style={{ color: fashionColors.textMuted }}>
              Caimento ainda não avaliado para esta peça.
            </Text>
          )}
        </FashionCard>

        {source && (source.product_title || source.source_name || buyUrl) ? (
          <FashionCard>
            <Text style={{ color: fashionColors.text, fontWeight: "900", fontSize: 18 }}>
              Peça
            </Text>
            <Text style={{ color: fashionColors.textSoft, lineHeight: 21 }}>
              {source.product_title ?? "Produto sem título"}
              {source.source_name ? `\n${source.source_name}` : ""}
            </Text>
            <PrimaryButton label={buyUrl ? "Ver na loja" : "Link indisponível"} onPress={buy} disabled={!buyUrl} />
          </FashionCard>
        ) : null}

        <Text style={{ color: fashionColors.text, fontSize: 20, fontWeight: "900", marginTop: 4 }}>
          Card para compartilhar
        </Text>
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
            fitSummary={fitSummary}
          />
        </ViewShot>

        <View style={{ flexDirection: "row", gap: 10 }}>
          <View style={{ flex: 1 }}>
            <PrimaryButton label="Salvar look" onPress={handleSave} />
          </View>
          <View style={{ flex: 1 }}>
            <PrimaryButton label="Compartilhar" onPress={handleShare} tone="secondary" />
          </View>
        </View>

        <PrimaryButton label="Compartilhar card" onPress={shareCard} tone="success" />

        <View style={{ flexDirection: "row", gap: 10 }}>
          <View style={{ flex: 1 }}>
            <SecondaryButton label="Histórico" onPress={onOpenHistory} />
          </View>
          <View style={{ flex: 1 }}>
            <SecondaryButton label="Experimentar outra prévia" onPress={onBackToVton} />
          </View>
        </View>
      </ScrollView>
    </AppScreen>
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
      return "Busto/tórax";
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
  if (fitZones.length === 0) return "Ainda não avaliamos o caimento desta peça.";

  const lowEase = fitZones.filter((zone) =>
    zone.status === "apertado" || zone.status === "too_small" || zone.status === "tight" || zone.color === "red"
  ).length;

  const close = fitZones.filter((zone) =>
    zone.status === "justo" || zone.status === "balanced" || zone.color === "yellow"
  ).length;

  const relaxed = fitZones.filter((zone) =>
    zone.status === "folgado" || zone.status === "loose" || zone.color === "green" || zone.color === "blue"
  ).length;

  if (lowEase > 0) return "Algumas regiões podem ter pouca folga. Vale conferir tecido, elasticidade e sua preferência de caimento.";
  if (close > 0) return "A peça tende a ficar mais próxima ao corpo em algumas regiões.";
  if (relaxed > 0) return "A peça tende a ter folga confortável na maior parte do look.";

  return "Caimento estimado com as medidas disponíveis.";
}

function humanizeZoneMessage(zone: FitZone): string {
  if (zone.color === "red") return "Pode ter pouca folga nessa região.";
  if (zone.color === "yellow") return "Deve ficar mais próximo ao corpo.";
  if (zone.color === "green") return "Tende a ter folga confortável.";
  if (zone.color === "blue") return "Tende a ficar mais solto.";
  if (zone.color === "gray") return "A loja não informou medida suficiente para esta região.";
  return zone.message;
}

export default VtonResultScreen;
