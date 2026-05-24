import React, { useState } from "react";
import { Image, ScrollView, Text, View } from "react-native";

import {
  createMockVton,
  prepareVton,
  renderMannequinFront,
  resolveApiUrl,
  runVtonTaskWithPolling,
} from "../api/client";
import { CLOUD_COLD_START_MESSAGE } from "../config/api";
import {
  AppScreen,
  FashionCard,
  FriendlyError,
  InfoPill,
  JourneyStepper,
  LoadingState,
  PrimaryButton,
  StepHeader,
  fashionColors,
} from "../components/FashionUI";
import { Mannequin3D } from "../components/Mannequin3D";
import { MannequinParams } from "../types/body";
import { FitZone, GarmentUploadResult } from "../types/product";
import { VtonPayload, VtonRunMode, VtonRunResult } from "../types/vton";
import { MannequinRenderResult } from "../types/mannequin";

type Props = {
  mannequin: MannequinParams;
  fitZones: FitZone[];
  garment?: GarmentUploadResult | null;
  onFinish: () => void;
  onResultReady?: (data: {
    result: VtonRunResult;
    payload: VtonPayload;
    frontRender: MannequinRenderResult | null;
  }) => void;
};

export function VtonPreviewScreen({
  mannequin,
  fitZones,
  garment,
  onResultReady,
}: Props) {
  const [loadingMode, setLoadingMode] = useState<VtonRunMode | null>(null);
  const [mannequinRender, setMannequinRender] = useState<MannequinRenderResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [taskMessage, setTaskMessage] = useState<string | null>(null);

  const hasGarmentImage = Boolean(garment?.processed_url || garment?.original_url);
  const preferredMode: VtonRunMode = hasGarmentImage ? "auto" : "mock";
  const processedGarmentUrl = resolveApiUrl(garment?.processed_url || garment?.original_url);
  const mannequinRenderUrl = resolveApiUrl(mannequinRender?.image_url);

  async function ensureFrontRender(): Promise<MannequinRenderResult | null> {
    if (mannequinRender) return mannequinRender;

    const rendered = await renderMannequinFront({ mannequin });
    setMannequinRender(rendered);
    return rendered;
  }

  async function run(mode: VtonRunMode = preferredMode) {
    let coldStartTimer: ReturnType<typeof setTimeout> | null = null;

    try {
      setLoadingMode(mode);
      setError(null);
      setTaskMessage("Preparando seu look...");
      coldStartTimer = setTimeout(() => {
        setTaskMessage(CLOUD_COLD_START_MESSAGE);
      }, 3500);

      const front = mode === "mock" ? null : await ensureFrontRender();

      const prepared = await prepareVton({
        mannequin,
        garment_processed_url: garment?.processed_url ?? null,
        garment_original_url: garment?.original_url ?? null,
        person_image_url: front?.image_url ?? null,
        fit_zones: fitZones,
      });

      if (mode === "mock") {
        setTaskMessage("Gerando uma prévia estimada do caimento...");
        const mock = await createMockVton({ payload: prepared });
        const result: VtonRunResult = {
          result_url: mock.result_url,
          result_path: mock.result_path,
          provider: "local_mock",
          mode_requested: "mock",
          status: "succeeded",
          used_fallback: false,
          success: true,
          message: mock.message,
          raw_response: null,
        };

        onResultReady?.({ result, payload: prepared, frontRender: null });
        return;
      }

      setTaskMessage("Tentando gerar a versão VTON real primeiro...");
      const result = await runVtonTaskWithPolling(
        {
          payload: prepared,
          mode,
        },
        (status) => {
          if (status.state === "queued") {
            setTaskMessage("Sua prévia entrou na fila. Estamos acompanhando automaticamente.");
          } else if (status.state === "running") {
            setTaskMessage("A imagem está sendo criada. Mantenha o app aberto por mais alguns instantes.");
          } else if (status.state === "succeeded") {
            setTaskMessage("Prévia pronta.");
          } else if (status.state === "failed") {
            setTaskMessage("Não conseguimos concluir essa prévia.");
          }
        }
      );

      onResultReady?.({ result, payload: prepared, frontRender: front ?? null });

    } catch (err) {
      setError(err instanceof Error ? err.message : "Tente novamente em instantes.");
    } finally {
      if (coldStartTimer) {
        clearTimeout(coldStartTimer);
      }
      setLoadingMode(null);
      setTaskMessage(null);
    }
  }

  return (
    <AppScreen>
      <ScrollView contentContainerStyle={{ padding: 24, gap: 16 }}>
        <StepHeader
          eyebrow="Look"
          step="5 de 5"
          title="Prévia do look"
          subtitle="Vamos gerar uma estimativa visual da peça no seu provador. O resultado ajuda a imaginar proporção e estilo, mas não substitui uma prova real."
        />
        <JourneyStepper activeStep="look" />

        <Mannequin3D params={mannequin} fitZones={fitZones} />

        <FashionCard highlighted={hasGarmentImage}>
          <Text style={{ color: fashionColors.text, fontWeight: "900", fontSize: 17 }}>
            {hasGarmentImage ? "Peça escolhida" : "Sem imagem da peça"}
          </Text>
          {processedGarmentUrl ? (
            <Image
              source={{ uri: processedGarmentUrl }}
              style={{
                width: "100%",
                height: 260,
                borderRadius: 16,
                backgroundColor: "#f3e8ff",
              }}
              resizeMode="contain"
            />
          ) : (
            <Text style={{ color: fashionColors.textSoft, lineHeight: 21 }}>
              Podemos gerar uma prévia estimada com molde visual. Para tentar o VTON real, envie uma foto da peça ou use um link que traga a imagem do produto.
            </Text>
          )}
        </FashionCard>

        <FashionCard>
          <InfoPill label={hasGarmentImage ? "Tenta VTON real primeiro" : "Prévia estimada"} tone={hasGarmentImage ? "purple" : "gold"} />
          <Text style={{ color: fashionColors.textSoft, lineHeight: 21, marginTop: 8 }}>
            {hasGarmentImage
              ? "Vamos tentar a API VTON real. Se ela estiver indisponível, o app usa o mock local para você não perder o fluxo."
              : "Como ainda não temos imagem utilizável da peça, esta etapa usa o mock local melhorado."}
          </Text>
        </FashionCard>

        <PrimaryButton
          label={loadingMode ? "Gerando prévia..." : hasGarmentImage ? "Gerar melhor prévia disponível" : "Gerar prévia estimada"}
          loading={Boolean(loadingMode)}
          onPress={() => run(preferredMode)}
        />

        {loadingMode && taskMessage ? (
          <LoadingState
            title="Criando sua prévia"
            message={`${taskMessage} Dica: roupas escuras costumam ficar melhores quando a foto original tem fundo claro.`}
          />
        ) : null}

        {mannequinRenderUrl ? (
          <FashionCard>
            <Text style={{ color: fashionColors.text, fontWeight: "900" }}>
              Base frontal pronta
            </Text>
            <Text style={{ color: fashionColors.textSoft, lineHeight: 21 }}>
              Usamos esta base apenas para criar a prévia visual do look.
            </Text>
          </FashionCard>
        ) : null}

        {error ? (
          <FriendlyError
            title="Não conseguimos gerar a prévia"
            message={error}
          />
        ) : null}
      </ScrollView>
    </AppScreen>
  );
}
