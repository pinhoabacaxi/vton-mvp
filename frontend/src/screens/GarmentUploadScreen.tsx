import React, { useState } from "react";
import { Alert, Image, ScrollView, Text, View } from "react-native";
import * as ImagePicker from "expo-image-picker";
import * as ImageManipulator from "expo-image-manipulator";
import { resolveApiUrl, uploadGarmentImage } from "../api/client";
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
import { GarmentUploadResult } from "../types/product";

type Props = {
  onContinue: () => void;
  onUploadComplete?: (result: GarmentUploadResult) => Promise<void> | void;
};

export function GarmentUploadScreen({ onContinue, onUploadComplete }: Props) {
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [result, setResult] = useState<GarmentUploadResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  async function pickImage() {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();

    if (!permission.granted) {
      Alert.alert("Permissão necessária", "Permita acesso às imagens para escolher uma foto da peça.");
      return;
    }

    const picked = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: false,
      quality: 0.9,
    });

    if (picked.canceled || picked.assets.length === 0) {
      return;
    }

    const asset = picked.assets[0];
    setImageUri(asset.uri);
    setResult(null);
    setConfirmed(false);
  }

  async function upload() {
    if (!imageUri) {
      Alert.alert("Escolha uma foto", "Use uma imagem com a peça inteira, de preferência em fundo claro.");
      return;
    }

    try {
      setLoading(true);

      const compressed = await ImageManipulator.manipulateAsync(
        imageUri,
        [{ resize: { width: 1200 } }],
        { compress: 0.7, format: ImageManipulator.SaveFormat.JPEG }
      );

      const response = await uploadGarmentImage({
        uri: compressed.uri,
        name: "garment.jpg",
        type: "image/jpeg",
      });

      setResult(response);
      setConfirmed(false);
    } catch (error) {
      Alert.alert(
        "Não conseguimos preparar a imagem",
        error instanceof Error ? error.message : "Tente uma foto mais nítida, com bom contraste."
      );
    } finally {
      setLoading(false);
    }
  }

  function rejectResult() {
    setResult(null);
    setImageUri(null);
    setConfirmed(false);
  }

  async function acceptResult() {
    if (!result) return;

    try {
      await onUploadComplete?.(result);
      setConfirmed(true);
    } catch (error) {
      Alert.alert(
        "Não foi possível salvar a peça",
        error instanceof Error ? error.message : "Tente novamente em instantes."
      );
    }
  }

  const processedUrl = resolveApiUrl(result?.processed_url);
  const originalUrl = resolveApiUrl(result?.original_url);

  return (
    <AppScreen>
      <ScrollView contentContainerStyle={{ padding: 24, gap: 16 }}>
        <StepHeader
          eyebrow="Peça"
          step="4 de 5"
          title="Enviar foto da peça"
          subtitle="Use uma foto frontal da roupa, com boa luz e fundo contrastante. Vamos preparar a imagem para a prévia do look."
        />
        <JourneyStepper activeStep="piece" />

        <PrimaryButton label="Escolher foto da peça" onPress={pickImage} tone="secondary" />

        {imageUri ? (
          <FashionCard>
            <Text style={{ color: fashionColors.text, fontWeight: "900" }}>
              Foto escolhida
            </Text>
            <Image
              source={{ uri: imageUri }}
              style={{
                width: "100%",
                height: 280,
                borderRadius: 20,
                backgroundColor: "#241233",
              }}
              resizeMode="contain"
            />
          </FashionCard>
        ) : null}

        <PrimaryButton
          label={loading ? "Preparando imagem..." : "Preparar imagem da peça"}
          onPress={upload}
          loading={loading}
          disabled={!imageUri}
        />

        {result ? (
          <FashionCard highlighted>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
              <Text style={{ color: fashionColors.text, fontWeight: "900", fontSize: 18, flex: 1 }}>
                A peça ficou assim
              </Text>
              <InfoPill
                label={result.background_removed ? "Recorte aplicado" : "Imagem otimizada"}
                tone={result.background_removed ? "gold" : "neutral"}
              />
            </View>

            <Text style={{ color: fashionColors.textSoft, lineHeight: 21 }}>
              Confira se mangas, barras e detalhes escuros continuam visíveis. Se algo sumiu, tente uma foto com fundo mais claro ou mais contraste.
            </Text>

            {processedUrl ? (
              <View
                style={{
                  width: "100%",
                  height: 300,
                  borderRadius: 18,
                  backgroundColor: "#f3e8ff",
                  alignItems: "center",
                  justifyContent: "center",
                  overflow: "hidden",
                }}
              >
                <Image
                  source={{ uri: processedUrl }}
                  style={{ width: "100%", height: "100%" }}
                  resizeMode="contain"
                />
              </View>
            ) : null}

            {originalUrl && !processedUrl ? (
              <Image
                source={{ uri: originalUrl }}
                style={{
                  width: "100%",
                  height: 260,
                  borderRadius: 18,
                  backgroundColor: "#241233",
                }}
                resizeMode="contain"
              />
            ) : null}

            {!confirmed ? (
              <View style={{ flexDirection: "row", gap: 10 }}>
                <View style={{ flex: 1 }}>
                  <SecondaryButton label="Refazer foto" onPress={rejectResult} />
                </View>
                <View style={{ flex: 1 }}>
                  <PrimaryButton label="Usar esta peça" onPress={acceptResult} tone="success" />
                </View>
              </View>
            ) : (
              <PrimaryButton label="Ver caimento" onPress={onContinue} />
            )}
          </FashionCard>
        ) : null}
      </ScrollView>
    </AppScreen>
  );
}
