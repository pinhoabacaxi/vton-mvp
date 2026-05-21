import React, { useState } from "react";
import {
  ActivityIndicator,
  Image,
  SafeAreaView,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import {
  prepareVton,
  renderMannequinFront,
  resolveApiUrl,
  runVtonTaskWithPolling,
} from "../api/client";
import { CLOUD_COLD_START_MESSAGE } from "../config/api";
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
  onFinish,
  onResultReady,
}: Props) {
  const [loadingMode, setLoadingMode] = useState<VtonRunMode | null>(null);
  const [renderingFront, setRenderingFront] = useState(false);
  const [payload, setPayload] = useState<VtonPayload | null>(null);
  const [runResult, setRunResult] = useState<VtonRunResult | null>(null);
  const [mannequinRender, setMannequinRender] = useState<MannequinRenderResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [taskMessage, setTaskMessage] = useState<string | null>(null);

  const processedGarmentUrl = resolveApiUrl(garment?.processed_url);
  const mannequinRenderUrl = resolveApiUrl(mannequinRender?.image_url);
  const resultImageUrl = resolveApiUrl(runResult?.result_url);

  async function renderFront() {
    try {
      setRenderingFront(true);
      setError(null);

      const rendered = await renderMannequinFront({ mannequin });
      setMannequinRender(rendered);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro inesperado");
    } finally {
      setRenderingFront(false);
    }
  }

  async function run(mode: VtonRunMode) {
    let coldStartTimer: ReturnType<typeof setTimeout> | null = null;

    try {
      setLoadingMode(mode);
      setError(null);
      setTaskMessage("Preparando payload do look...");
      coldStartTimer = setTimeout(() => {
        setTaskMessage(CLOUD_COLD_START_MESSAGE);
      }, 3500);

      const prepared = await prepareVton({
        mannequin,
        garment_processed_url: garment?.processed_url ?? null,
        garment_original_url: garment?.original_url ?? null,
        person_image_url: mannequinRender?.image_url ?? null,
        fit_zones: fitZones,
      });

      setTaskMessage("Enviando tarefa VTON para a fila...");
      const result = await runVtonTaskWithPolling(
        {
          payload: prepared,
          mode,
        },
        (status) => {
          if (status.state === "queued") {
            setTaskMessage("Look na fila. Consultando a cada 2 segundos...");
          } else if (status.state === "running") {
            setTaskMessage("IA gerando o provador virtual. Mantenha o app aberto.");
          } else if (status.state === "succeeded") {
            setTaskMessage("Resultado pronto.");
          } else if (status.state === "failed") {
            setTaskMessage("A tarefa VTON falhou.");
          }
        }
      );

      setPayload(prepared);
      setRunResult(result);
      // notify parent that a result is ready (includes current frontal render if any)
      onResultReady?.({ result, payload: prepared, frontRender: mannequinRender ?? null });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro inesperado");
    } finally {
      if (coldStartTimer) {
        clearTimeout(coldStartTimer);
      }
      setLoadingMode(null);
      setTaskMessage(null);
    }
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#12071f" }}>
      <ScrollView contentContainerStyle={{ padding: 24, gap: 16 }}>
        <Text style={{ color: "white", fontSize: 28, fontWeight: "800" }}>
          VTON Experimental
        </Text>

        <Text style={{ color: "#d8c7ff", fontSize: 15 }}>
          Gere um render frontal do manequim e use-o em payloads VTON de fase 3E.
        </Text>

        <Mannequin3D params={mannequin} fitZones={fitZones} />

        {processedGarmentUrl && (
          <View
            style={{
              backgroundColor: "#f3e8ff",
              borderRadius: 18,
              padding: 12,
              gap: 8,
            }}
          >
            <Text style={{ color: "#2e1065", fontWeight: "800" }}>
              Roupa sem fundo
            </Text>

            <Image
              source={{ uri: processedGarmentUrl }}
              style={{
                width: "100%",
                height: 260,
                borderRadius: 16,
              }}
              resizeMode="contain"
            />
          </View>
        )}

        <View style={{ gap: 10 }}>
          <ActionButton
            label={renderingFront ? "Renderizando manequim..." : "Render frontal do manequim"}
            loading={renderingFront}
            color="#7c3aed"
            onPress={renderFront}
          />

          <ActionButton
            label="Gerar mock local"
            loading={loadingMode === "mock"}
            color="#8b5cf6"
            onPress={() => run("mock")}
          />

          <ActionButton
            label="Auto: API externa ou mock"
            loading={loadingMode === "auto"}
            color="#6d28d9"
            onPress={() => run("auto")}
          />

          <ActionButton
            label="Tentar VTON real experimental"
            loading={loadingMode === "external"}
            color="#3b1c5c"
            onPress={() => run("external")}
          />
        </View>

        {loadingMode && taskMessage && (
          <View
            style={{
              backgroundColor: "#21102f",
              borderRadius: 18,
              padding: 14,
              gap: 8,
              borderWidth: 1,
              borderColor: "#4c2a69",
            }}
          >
            <Text style={{ color: "white", fontWeight: "800", fontSize: 18 }}>
              Processando VTON
            </Text>
            <Text style={{ color: "#d8c7ff" }}>{taskMessage}</Text>
            <Text style={{ color: "#c4b5fd" }}>
              Dica: roupas escuras com fundo claro tendem a preservar melhor barras, mangas e detalhes assimetricos.
            </Text>
          </View>
        )}

        {mannequinRenderUrl && (
          <View
            style={{
              backgroundColor: "#21102f",
              borderRadius: 18,
              padding: 14,
              gap: 10,
              borderWidth: 1,
              borderColor: "#4c2a69",
            }}
          >
            <Text style={{ color: "white", fontSize: 18, fontWeight: "800" }}>
              Render frontal do manequim
            </Text>

            <Image
              source={{ uri: mannequinRenderUrl }}
              style={{
                width: "100%",
                height: 380,
                borderRadius: 18,
                backgroundColor: "#170b25",
              }}
              resizeMode="contain"
            />

            <Text style={{ color: "#d8c7ff" }}>
              {mannequinRender?.message}
            </Text>
          </View>
        )}

        {error && (
          <View
            style={{
              backgroundColor: "#450a0a",
              borderRadius: 16,
              padding: 12,
            }}
          >
            <Text style={{ color: "#fecaca" }}>{error}</Text>
          </View>
        )}

        {runResult && (
          <View
            style={{
              backgroundColor: "#21102f",
              borderRadius: 20,
              padding: 14,
              gap: 10,
              borderWidth: 1,
              borderColor: "#4c2a69",
            }}
          >
            <Text style={{ color: "white", fontSize: 18, fontWeight: "800" }}>
              Resultado
            </Text>

            <Text style={{ color: "#d8c7ff" }}>
              Provider: {runResult.provider}
            </Text>

            <Text style={{ color: "#d8c7ff" }}>
              Modo pedido: {runResult.mode_requested}
            </Text>

            <Text style={{ color: "#d8c7ff" }}>
              Fallback usado: {runResult.used_fallback ? "sim" : "não"}
            </Text>

            <Text style={{ color: "#d8c7ff" }}>
              {runResult.message}
            </Text>

            {resultImageUrl && (
              <Image
                source={{ uri: resultImageUrl }}
                style={{
                  width: "100%",
                  height: 440,
                  borderRadius: 18,
                  backgroundColor: "#170b25",
                }}
                resizeMode="contain"
              />
            )}
          </View>
        )}

        {payload && (
          <View
            style={{
              backgroundColor: "#21102f",
              borderRadius: 20,
              padding: 14,
              gap: 8,
              borderWidth: 1,
              borderColor: "#4c2a69",
            }}
          >
            <Text style={{ color: "white", fontSize: 18, fontWeight: "800" }}>
              Payload preparado
            </Text>

            <Text style={{ color: "#d8c7ff" }}>
              Render: {payload.render_mode}
            </Text>

            <Text style={{ color: "#d8c7ff" }}>
              Ângulos recomendados: {payload.recommended_view_count}
            </Text>

            {payload.notes.map((note, index) => (
              <Text key={index} style={{ color: "#c4b5fd" }}>
                • {note}
              </Text>
            ))}
          </View>
        )}

        <TouchableOpacity
          onPress={onFinish}
          style={{
            backgroundColor: "#3b1c5c",
            padding: 16,
            borderRadius: 18,
            alignItems: "center",
          }}
        >
          <Text style={{ color: "white", fontWeight: "800" }}>
            Finalizar fase 3E
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

function ActionButton(props: {
  label: string;
  loading: boolean;
  color: string;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      onPress={props.onPress}
      disabled={props.loading}
      style={{
        backgroundColor: props.color,
        padding: 16,
        borderRadius: 18,
        alignItems: "center",
      }}
    >
      {props.loading ? (
        <ActivityIndicator color="white" />
      ) : (
        <Text style={{ color: "white", fontWeight: "800" }}>
          {props.label}
        </Text>
      )}
    </TouchableOpacity>
  );
}
