import React, { useEffect, useState } from "react";
import { Image, ScrollView, Text, View } from "react-native";
import * as ImagePicker from "expo-image-picker";
import * as ImageManipulator from "expo-image-manipulator";

import {
  createMockVton,
  prepareVton,
  renderMannequinFront,
  resolveApiUrl,
  runVtonTaskWithPolling,
  uploadEphemeralPersonImage,
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
  SecondaryButton,
  StepHeader,
  fashionColors,
} from "../components/FashionUI";
import { Mannequin3D } from "../components/Mannequin3D";
import { MannequinParams } from "../types/body";
import { FitZone, GarmentUploadResult } from "../types/product";
import { PersonEphemeralUploadResult, VtonPayload, VtonRunMode, VtonRunResult } from "../types/vton";
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

const ROTATING_LOADING_MESSAGES = [
  "Analisando caimento...",
  "Ajustando iluminação...",
  "Processando a imagem da peça...",
  "Preparando a melhor prévia disponível...",
];

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
  const [personConsentAccepted, setPersonConsentAccepted] = useState(false);
  const [showPersonGuide, setShowPersonGuide] = useState(false);
  const [personPhotoUri, setPersonPhotoUri] = useState<string | null>(null);
  const [personUpload, setPersonUpload] = useState<PersonEphemeralUploadResult | null>(null);
  const [personUploading, setPersonUploading] = useState(false);

  const hasGarmentImage = Boolean(garment?.processed_url || garment?.original_url);
  const preferredMode: VtonRunMode = hasGarmentImage ? "auto" : "mock";
  const processedGarmentUrl = resolveApiUrl(garment?.processed_url || garment?.original_url);
  const mannequinRenderUrl = resolveApiUrl(mannequinRender?.image_url);

  useEffect(() => {
    if (!loadingMode) return undefined;

    let index = 0;
    const interval = setInterval(() => {
      index = (index + 1) % ROTATING_LOADING_MESSAGES.length;
      setTaskMessage(ROTATING_LOADING_MESSAGES[index]);
    }, 5200);

    return () => clearInterval(interval);
  }, [loadingMode]);

  async function ensureFrontRender(): Promise<MannequinRenderResult | null> {
    if (mannequinRender) return mannequinRender;

    const rendered = await renderMannequinFront({ mannequin });
    setMannequinRender(rendered);
    return rendered;
  }

  async function pickPersonPhoto(source: "camera" | "library") {
    const permission =
      source === "camera"
        ? await ImagePicker.requestCameraPermissionsAsync()
        : await ImagePicker.requestMediaLibraryPermissionsAsync();

    if (!permission.granted) {
      setError("Autorize o acesso para enviar sua foto com segurança.");
      return;
    }

    const options: ImagePicker.ImagePickerOptions = {
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [3, 4],
      quality: 0.9,
      exif: false,
    };

    const picked =
      source === "camera"
        ? await ImagePicker.launchCameraAsync(options)
        : await ImagePicker.launchImageLibraryAsync(options);

    if (picked.canceled || !picked.assets?.[0]) {
      return;
    }

    try {
      setPersonUploading(true);
      setError(null);

      const compressed = await ImageManipulator.manipulateAsync(
        picked.assets[0].uri,
        [{ resize: { width: 768 } }],
        {
          compress: 0.82,
          format: ImageManipulator.SaveFormat.JPEG,
          base64: false,
        }
      );

      console.info("[Flow] User self photo prepared", {
        width: compressed.width,
        height: compressed.height,
      });

      const upload = await uploadEphemeralPersonImage({
        uri: compressed.uri,
        name: "person-photo.jpg",
        type: "image/jpeg",
      });

      console.info("[State] Ephemeral person photo ready", {
        expiresInSeconds: upload.expires_in_seconds,
      });
      setPersonPhotoUri(compressed.uri);
      setPersonUpload(upload);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Não conseguimos preparar sua foto. Tente uma imagem de corpo inteiro, com boa luz."
      );
      setPersonUpload(null);
    } finally {
      setPersonUploading(false);
    }
  }

  async function run(mode: VtonRunMode = preferredMode) {
    let coldStartTimer: ReturnType<typeof setTimeout> | null = null;

    try {
      console.info("[API] Requesting VTON", {
        mode,
        hasGarmentImage,
        fitZoneCount: fitZones.length,
      });
      setLoadingMode(mode);
      setError(null);
      setTaskMessage("Preparando seu look...");
      coldStartTimer = setTimeout(() => {
        setTaskMessage(CLOUD_COLD_START_MESSAGE);
      }, 3500);

      const userPersonImageUrl = personUpload?.person_image_url ?? null;
      const front = mode === "mock" || userPersonImageUrl ? null : await ensureFrontRender();

      const prepared = await prepareVton({
        mannequin,
        garment_processed_url: garment?.processed_url ?? null,
        garment_original_url: garment?.original_url ?? null,
        person_image_url: userPersonImageUrl ?? front?.image_url ?? null,
        user_uploaded_person_image_url: userPersonImageUrl,
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
          render_method: mock.render_method ?? "LOCAL_FIT_DIAGRAM",
          status: "succeeded",
          used_fallback: false,
          success: true,
          message: mock.message,
          raw_response: null,
        };

        onResultReady?.({ result, payload: prepared, frontRender: null });
        return;
      }

      setTaskMessage("Tentando criar uma Prévia Realista primeiro...");
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

      console.info("[API] VTON result ready", {
        render_method: result.render_method,
        provider: result.provider,
        used_fallback: result.used_fallback,
      });
      onResultReady?.({ result, payload: prepared, frontRender: userPersonImageUrl ? null : front ?? null });

    } catch (err) {
      console.info("[Flow] VTON preview failed", {
        message: err instanceof Error ? err.message : "unknown",
      });
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
              Podemos gerar um Diagrama de Caimento Estimado com as medidas. Para criarmos uma Prévia Realista, envie uma foto nítida da peça ou use um link direto do produto.
            </Text>
          )}
        </FashionCard>

        <FashionCard highlighted={Boolean(personUpload)}>
          <Text style={{ color: fashionColors.text, fontWeight: "900", fontSize: 17 }}>
            Usar minha foto na Prévia Realista
          </Text>
          <Text style={{ color: fashionColors.textSoft, lineHeight: 21 }}>
            Privacidade em 1º lugar. Sua foto viaja de forma criptografada para gerar o look e é destruída permanentemente do nosso servidor logo após o resultado. Não guardamos, não olhamos e não treinamos modelos com sua imagem.
          </Text>

          {!personConsentAccepted ? (
            <PrimaryButton
              label="Entendi e quero enviar minha foto"
              onPress={() => {
                setPersonConsentAccepted(true);
                setShowPersonGuide(true);
              }}
              tone="secondary"
            />
          ) : null}

          {personConsentAccepted && showPersonGuide ? (
            <View style={{ gap: 10 }}>
              <InfoPill label="Guia rápido para evitar falhas" tone="gold" />
              {[
                "Fundo liso e claro.",
                "Pose de frente para a câmera.",
                "Braços levemente afastados do corpo.",
                "Boa iluminação para reconhecer a silhueta.",
              ].map((item) => (
                <Text key={item} style={{ color: fashionColors.textSoft, lineHeight: 20 }}>
                  • {item}
                </Text>
              ))}

              <View style={{ flexDirection: "row", gap: 10 }}>
                <View style={{ flex: 1 }}>
                  <SecondaryButton
                    label="Galeria"
                    onPress={() => pickPersonPhoto("library")}
                    disabled={personUploading}
                  />
                </View>
                <View style={{ flex: 1 }}>
                  <SecondaryButton
                    label="Câmera"
                    onPress={() => pickPersonPhoto("camera")}
                    disabled={personUploading}
                  />
                </View>
              </View>
            </View>
          ) : null}

          {personPhotoUri ? (
            <View style={{ gap: 10 }}>
              <InfoPill label="Foto efêmera pronta" tone="purple" />
              <Image
                source={{ uri: personPhotoUri }}
                style={{
                  width: "100%",
                  height: 260,
                  borderRadius: 16,
                  backgroundColor: "#170b25",
                }}
                resizeMode="contain"
              />
              <Text style={{ color: fashionColors.textMuted, lineHeight: 20 }}>
                Ela será usada somente nesta tentativa de prévia e não será salva no histórico.
              </Text>
            </View>
          ) : null}

          {personUploading ? (
            <LoadingState
              title="Preparando sua foto"
              message="Removendo metadados, comprimindo a imagem e criando uma referência temporária."
            />
          ) : null}
        </FashionCard>

        <FashionCard>
          <InfoPill label={hasGarmentImage ? "Prévia Realista quando possível" : "Diagrama estimado"} tone={hasGarmentImage ? "purple" : "gold"} />
          <Text style={{ color: fashionColors.textSoft, lineHeight: 21, marginTop: 8 }}>
            {hasGarmentImage
              ? "Vamos buscar a melhor prévia disponível. Se a imagem não for compatível com a renderização realista, mostramos um Diagrama de Caimento Estimado para você continuar decidindo."
              : "Como ainda não temos imagem utilizável da peça, esta etapa mostra um Diagrama de Caimento Estimado com base nas medidas."}
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
