import React, { useRef, useState } from "react";
import {
  Alert,
  Image,
  ScrollView,
  Text,
  View,
} from "react-native";
import ViewShot from "react-native-view-shot";
import { resolveApiUrl } from "../api/client";
import { shareImageFromUrl } from "../utils/shareImage";
import { shareCapturedImage } from "../utils/shareViewShot";
import { openExternalUrl, getPreferredBuyUrl } from "../utils/openExternalUrl";
import { buildFitInsight, buildFitSummaryForUser, fitColorToHex, fitZoneLabel } from "../utils/fitCopy";
import { SocialLookCard } from "../components/SocialLookCard";
import {
  AppScreen,
  DebugPanel,
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
  const fitSummary = buildFitSummaryForUser(fitZones);
  const sourceInfo = buildPreviewSourceInfo(result);

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
          subtitle="Prévia para visualizar proporção, estilo e pontos de caimento. O tecido, o corte e a foto original podem mudar o resultado real."
        />
        <JourneyStepper activeStep="look" />

        <InfoPill label={sourceInfo.label} tone={sourceInfo.tone} />
        <FashionCard highlighted={sourceInfo.tone === "purple"}>
          <Text style={{ color: fashionColors.text, fontWeight: "900", fontSize: 18 }}>
            {sourceInfo.title}
          </Text>
          <Text style={{ color: fashionColors.textSoft, lineHeight: 22 }}>
            {sourceInfo.message}
          </Text>
        </FashionCard>

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
                    borderLeftColor: fitColorToHex(z.color),
                  }}
                >
                  <Text style={{ color: fashionColors.text, fontWeight: "900" }}>{fitZoneLabel(z.zone)}</Text>
                  <Text style={{ color: fashionColors.textSoft, lineHeight: 20 }}>{buildFitInsight(z)}</Text>
                  <Text style={{ color: fashionColors.textMuted, marginTop: 4 }}>
                    Diferença estimada: {z.difference_cm ?? "-"} cm
                  </Text>
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

        <DebugPanel title="Execução técnica">
          <Text style={{ color: fashionColors.textMuted, lineHeight: 20 }}>
            Provider: {result.provider}{"\n"}
            Modo: {result.mode_requested}{"\n"}
            Fallback: {result.used_fallback ? "sim" : "não"}{"\n"}
            Payload: {payload ? "preparado" : "indisponível"}
          </Text>
        </DebugPanel>
      </ScrollView>
    </AppScreen>
  );
}

function buildPreviewSourceInfo(result: VtonRunResult): {
  label: string;
  title: string;
  message: string;
  tone: "gold" | "purple" | "neutral";
} {
  if (result.render_method === "NEURAL_REALISTIC") {
    return {
      label: "Prévia Realista",
      title: "Prévia realista gerada por IA",
      message: "Conseguimos combinar uma imagem humana compatível com a foto da peça para criar uma referência visual mais próxima do real. Use como guia, não como promessa de caimento perfeito.",
      tone: "purple",
    };
  }

  if (result.render_method === "LOCAL_FIT_DIAGRAM") {
    return {
      label: "Diagrama de Caimento Estimado",
      title: "Diagrama estimado para decidir com segurança",
      message: "A prévia neural não estava disponível ou a imagem não era compatível. Mostramos um diagrama local com proporção, folga e regiões de atenção.",
      tone: "gold",
    };
  }

  const provider = (result.provider || "").toLowerCase();
  const isRealProvider = provider.includes("replicate") || provider.includes("huggingface") || provider.includes("external");

  if (isRealProvider && !result.used_fallback) {
    return {
      label: "Prévia Realista",
      title: "Prévia realista gerada por IA",
      message: "Conseguimos criar uma referência visual realista com a imagem da pessoa e da peça. Ainda assim, considere o resultado uma estimativa.",
      tone: "purple",
    };
  }

  if (result.used_fallback) {
    return {
      label: "Diagrama de Caimento Estimado",
      title: "Usamos o diagrama local para manter o fluxo",
      message: "Tentamos a geração realista primeiro, mas ela não estava disponível para esta imagem. Abaixo está uma leitura estimada de proporção e caimento.",
      tone: "gold",
    };
  }

  return {
    label: "Diagrama de Caimento Estimado",
    title: "Diagrama local de caimento",
    message: "Esta imagem foi gerada pelo motor local do app. Ela ajuda a avaliar proporção, folga e regiões de atenção, sem prometer precisão perfeita.",
    tone: "gold",
  };
}

export default VtonResultScreen;
