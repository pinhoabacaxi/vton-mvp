import React, { useState } from "react";
import {
  Alert,
  Image,
  SafeAreaView,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import * as ImageManipulator from "expo-image-manipulator";
import { resolveApiUrl, uploadGarmentImage } from "../api/client";
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
      Alert.alert("Permissão necessária", "Permita acesso às imagens.");
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
      Alert.alert("Selecione uma imagem", "Escolha uma foto da roupa primeiro.");
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
        "Erro no upload",
        error instanceof Error ? error.message : "Erro inesperado"
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
        "Erro ao salvar peca",
        error instanceof Error ? error.message : "Erro inesperado"
      );
    }
  }

  const processedUrl = resolveApiUrl(result?.processed_url);
  const originalUrl = resolveApiUrl(result?.original_url);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#12071f" }}>
      <ScrollView contentContainerStyle={{ padding: 24, gap: 16 }}>
        <Text style={{ color: "white", fontSize: 28, fontWeight: "800" }}>
          Upload da roupa
        </Text>

        <Text style={{ color: "#d8c7ff", fontSize: 15 }}>
          Envie uma foto plana da peça. O backend salvará a imagem e removerá o fundo.
        </Text>

        <TouchableOpacity
          onPress={pickImage}
          style={{
            backgroundColor: "#241233",
            borderColor: "#6d35b8",
            borderWidth: 1,
            padding: 16,
            borderRadius: 18,
            alignItems: "center",
          }}
        >
          <Text style={{ color: "white", fontWeight: "800" }}>
            Escolher imagem
          </Text>
        </TouchableOpacity>

        {imageUri && (
          <View style={{ gap: 8 }}>
            <Text style={{ color: "white", fontWeight: "800" }}>
              Imagem selecionada
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
          </View>
        )}

        <TouchableOpacity
          onPress={upload}
          disabled={loading}
          style={{
            backgroundColor: loading ? "#5b3d87" : "#8b5cf6",
            padding: 16,
            borderRadius: 18,
            alignItems: "center",
          }}
        >
          <Text style={{ color: "white", fontWeight: "800" }}>
            {loading ? "Processando..." : "Enviar e remover fundo"}
          </Text>
        </TouchableOpacity>

        {result && (
          <View
            style={{
              backgroundColor: "#21102f",
              borderRadius: 18,
              padding: 14,
              gap: 12,
              borderWidth: 1,
              borderColor: "#4c2a69",
            }}
          >
            <Text style={{ color: "white", fontWeight: "800", fontSize: 18 }}>
              A roupa ficou assim
            </Text>

            <Text style={{ color: "#d8c7ff" }}>
              {result.message}
            </Text>

            <Text style={{ color: "#d8c7ff" }}>
              Fundo removido: {result.background_removed ? "sim" : "não"}
            </Text>

            {originalUrl && (
              <View style={{ gap: 8 }}>
                <Text style={{ color: "white", fontWeight: "800" }}>
                  Original salva no backend
                </Text>

                <Image
                  source={{ uri: originalUrl }}
                  style={{
                    width: "100%",
                    height: 240,
                    borderRadius: 18,
                    backgroundColor: "#241233",
                  }}
                  resizeMode="contain"
                />
              </View>
            )}

            {processedUrl && (
              <View style={{ gap: 8 }}>
                <Text style={{ color: "white", fontWeight: "800" }}>
                  Roupa sem fundo
                </Text>

                <View
                  style={{
                    width: "100%",
                    height: 280,
                    borderRadius: 18,
                    backgroundColor: "#f3e8ff",
                    alignItems: "center",
                    justifyContent: "center",
                    overflow: "hidden",
                  }}
                >
                  <Image
                    source={{ uri: processedUrl }}
                    style={{
                      width: "100%",
                      height: "100%",
                    }}
                    resizeMode="contain"
                  />
                </View>
              </View>
            )}

            {!confirmed ? (
              <View style={{ gap: 10 }}>
                <Text style={{ color: "#fef3c7" }}>
                  Confira se a silhueta nao perdeu mangas, barras ou detalhes escuros. Se o recorte falhou, use outra foto com fundo mais contrastante.
                </Text>

                <View style={{ flexDirection: "row", gap: 10 }}>
                  <TouchableOpacity
                    onPress={rejectResult}
                    style={{
                      flex: 1,
                      backgroundColor: "#450a0a",
                      padding: 14,
                      borderRadius: 16,
                      alignItems: "center",
                    }}
                  >
                    <Text style={{ color: "#fecaca", fontWeight: "800" }}>
                      Refazer
                    </Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    onPress={acceptResult}
                    style={{
                      flex: 1,
                      backgroundColor: "#16a34a",
                      padding: 14,
                      borderRadius: 16,
                      alignItems: "center",
                    }}
                  >
                    <Text style={{ color: "white", fontWeight: "800" }}>
                      Usar peca
                    </Text>
                  </TouchableOpacity>
                </View>
              </View>
            ) : (
              <TouchableOpacity
                onPress={onContinue}
                style={{
                  backgroundColor: "#8b5cf6",
                  padding: 14,
                  borderRadius: 16,
                  alignItems: "center",
                }}
              >
                <Text style={{ color: "white", fontWeight: "800" }}>
                  Continuar para Fit Check
                </Text>
              </TouchableOpacity>
            )}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
