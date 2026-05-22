import "react-native-gesture-handler";
import React, { useState, useEffect } from "react";
import { ActivityIndicator, Alert, SafeAreaView, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { enableScreens } from "react-native-screens";

import { recommendBodyModels, generateMannequin } from "./src/api/client";
import { InitialBodyInput, BodyRecommendationResponse, BodyModel, FineTuneInput, MannequinParams } from "./src/types/body";
import { createSavedLook, SavedLook, SaveLookInput } from "./src/types/look";
import { createClosetItem } from "./src/types/closet";
import { FitCheckResult, ProductScrapeResult } from "./src/types/product";
import { MannequinRenderResult } from "./src/types/mannequin";
import { VtonPayload, VtonRunResult } from "./src/types/vton";
import { buildAffiliateUrl } from "./src/utils/affiliate";
import { useVtonStore } from "./src/stores/useVtonStore";
import { useHistoryStore } from "./src/stores/useHistoryStore";
import { useClosetStore } from "./src/stores/useClosetStore";
import { loadSavedBodyProfile, saveSavedBodyProfile } from "./src/storage/bodyProfileStorage";

import { MeasurementsScreen } from "./src/screens/MeasurementsScreen";
import { BodyModelSelectionScreen } from "./src/screens/BodyModelSelectionScreen";
import { FineTuneScreen } from "./src/screens/FineTuneScreen";
import { MannequinPreviewScreen } from "./src/screens/MannequinPreviewScreen";
import ProductUrlScreen from "./src/screens/ProductUrlScreen";
import { GarmentUploadScreen } from "./src/screens/GarmentUploadScreen";
import { FitCheckScreen } from "./src/screens/FitCheckScreen";
import { VtonPreviewScreen } from "./src/screens/VtonPreviewScreen";
import VtonResultScreen from "./src/screens/VtonResultScreen";
import LookHistoryScreen from "./src/screens/LookHistoryScreen";
import ClosetScreen from "./src/screens/ClosetScreen";

type RootStackParamList = {
  Measurements: undefined;
  SelectModel: undefined;
  FineTune: undefined;
  Preview: undefined;
  ProductUrl: undefined;
  GarmentUpload: undefined;
  FitCheck: undefined;
  VtonPreview: undefined;
  VtonResult: undefined;
  LookHistory: undefined;
  Closet: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

enableScreens();

function MissingFlowScreen({
  message,
  onRestart,
}: {
  message: string;
  onRestart: () => void;
}) {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#12071f", justifyContent: "center", alignItems: "center", padding: 24 }}>
      <Text style={{ color: "white", fontSize: 22, fontWeight: "800", marginBottom: 16, textAlign: "center" }}>
        {message}
      </Text>
      <TouchableOpacity
        onPress={onRestart}
        style={{ backgroundColor: "#8b5cf6", padding: 16, borderRadius: 16, minWidth: 220, alignItems: "center" }}
      >
        <Text style={{ color: "white", fontWeight: "800" }}>Voltar ao início</Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

export default function App() {
  const [loading, setLoading] = useState(false);
  const [bootingProfile, setBootingProfile] = useState(true);
  const [initialRouteName, setInitialRouteName] =
    useState<keyof RootStackParamList>("Measurements");
  const looks = useHistoryStore((state) => state.looks);
  const loadHistory = useHistoryStore((state) => state.loadHistory);
  const addLook = useHistoryStore((state) => state.addLook);
  const clearHistory = useHistoryStore((state) => state.clearHistory);
  const closetItems = useClosetStore((state) => state.items);
  const loadCloset = useClosetStore((state) => state.loadCloset);
  const addClosetItem = useClosetStore((state) => state.addItem);
  const clearCloset = useClosetStore((state) => state.clearCloset);

  const initialInput = useVtonStore((state) => state.initialInput);
  const recommendation = useVtonStore((state) => state.recommendation);
  const selectedModel = useVtonStore((state) => state.selectedModel);
  const mannequin = useVtonStore((state) => state.mannequin);
  const garment = useVtonStore((state) => state.garment);
  const fitCheckResult = useVtonStore((state) => state.fitCheckResult);
  const frontRender = useVtonStore((state) => state.frontRender);
  const vtonPayload = useVtonStore((state) => state.vtonPayload);
  const vtonResult = useVtonStore((state) => state.vtonResult);
  const productUrl = useVtonStore((state) => state.productUrl);
  const productSource = useVtonStore((state) => state.productSource);
  const productDetails = useVtonStore((state) => state.productDetails);

  const setInitialInput = useVtonStore((state) => state.setInitialInput);
  const setRecommendation = useVtonStore((state) => state.setRecommendation);
  const setSelectedModel = useVtonStore((state) => state.setSelectedModel);
  const setMannequin = useVtonStore((state) => state.setMannequin);
  const setGarment = useVtonStore((state) => state.setGarment);
  const setFitCheckResult = useVtonStore((state) => state.setFitCheckResult);
  const setFrontRender = useVtonStore((state) => state.setFrontRender);
  const setVtonPayload = useVtonStore((state) => state.setVtonPayload);
  const setVtonResult = useVtonStore((state) => state.setVtonResult);
  const setProductUrl = useVtonStore((state) => state.setProductUrl);
  const setProductSource = useVtonStore((state) => state.setProductSource);
  const setProductDetails = useVtonStore((state) => state.setProductDetails);

  useEffect(() => {
    let mounted = true;

    async function boot() {
      try {
        const [profile] = await Promise.all([
          loadSavedBodyProfile(),
          loadHistory(),
          loadCloset(),
        ]);

        if (!mounted) return;

        if (profile) {
          setInitialInput(profile.initial_input);
          setSelectedModel(profile.selected_model);
          setMannequin(profile.mannequin);
          setInitialRouteName("Preview");
        }
      } finally {
        if (mounted) {
          setBootingProfile(false);
        }
      }
    }

    boot();

    return () => {
      mounted = false;
    };
  }, [
    loadCloset,
    loadHistory,
    setInitialInput,
    setMannequin,
    setSelectedModel,
  ]);

  async function handleInitialSubmit(data: InitialBodyInput, navigation: any) {
    setInitialInput(data);
    setLoading(true);

    try {
      const rec = await recommendBodyModels(data);
      setRecommendation(rec);
      navigation.navigate("SelectModel");
    } catch (err) {
      Alert.alert("Erro", err instanceof Error ? err.message : "Erro ao recomendar modelos");
    } finally {
      setLoading(false);
    }
  }

  function handleModelSelect(model: BodyModel, navigation: any) {
    setSelectedModel(model);
    navigation.navigate("FineTune");
  }

  async function handleFineTuneSubmit(data: FineTuneInput, navigation: any) {
    setLoading(true);
    try {
      const m = await generateMannequin(data);
      setMannequin(m);
      if (initialInput && selectedModel) {
        await saveSavedBodyProfile({
          initial_input: initialInput,
          selected_model: selectedModel,
          mannequin: m,
          updated_at: new Date().toISOString(),
        });
      }
      navigation.navigate("Preview");
    } catch (err) {
      Alert.alert("Erro", err instanceof Error ? err.message : "Erro ao gerar manequim");
    } finally {
      setLoading(false);
    }
  }

  async function saveLook(input: SaveLookInput) {
    try {
      const look = createSavedLook({ ...input, source: input.source ?? productSource ?? null });
      await addLook(look);
      Alert.alert("Salvo", "Look salvo no histórico local.");
    } catch (error) {
      Alert.alert("Erro ao salvar histórico", error instanceof Error ? error.message : "Erro inesperado");
    }
  }

  async function handleLookOpen(look: SavedLook, navigation: any) {
    setMannequin(look.mannequin);
    setGarment(look.garment ?? null);
    setFrontRender(look.front_render ?? null);
    setFitCheckResult({ zones: look.fit_zones, summary: "Look salvo no histórico." });
    setVtonPayload(look.vton_payload ?? null);
    setVtonResult(look.vton_result);
    setProductSource(look.source ?? null);
    navigation.navigate("VtonResult");
  }

  if (bootingProfile) {
    return (
      <SafeAreaProvider>
        <SafeAreaView style={{ flex: 1, backgroundColor: "#12071f", justifyContent: "center", alignItems: "center", gap: 12 }}>
          <ActivityIndicator size="large" color="white" />
          <Text style={{ color: "#d8c7ff", fontWeight: "700" }}>
            Carregando seu manequim base...
          </Text>
        </SafeAreaView>
        <StatusBar style="light" />
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <Stack.Navigator initialRouteName={initialRouteName} screenOptions={{ headerShown: false }}>
          <Stack.Screen name="Measurements">
            {(props) => (
              <MeasurementsScreen
                onSubmit={(data) => handleInitialSubmit(data, props.navigation)}
              />
            )}
          </Stack.Screen>

          <Stack.Screen name="SelectModel">
            {(props) =>
              recommendation ? (
                <BodyModelSelectionScreen
                  recommendation={recommendation}
                  onSelect={(model) => handleModelSelect(model, props.navigation)}
                />
              ) : (
                <MissingFlowScreen
                  message="Recomendação ausente. Retorne ao início para calcular seu corpo."
                  onRestart={() => props.navigation.reset({ index: 0, routes: [{ name: "Measurements" }] })}
                />
              )
            }
          </Stack.Screen>

          <Stack.Screen name="FineTune">
            {(props) =>
              initialInput && selectedModel ? (
                <FineTuneScreen
                  initial={initialInput}
                  selectedModel={selectedModel}
                  onSubmit={(data) => handleFineTuneSubmit(data, props.navigation)}
                />
              ) : (
                <MissingFlowScreen
                  message="Dados do corpo ausentes. Volte ao início para refazer as medidas."
                  onRestart={() => props.navigation.reset({ index: 0, routes: [{ name: "Measurements" }] })}
                />
              )
            }
          </Stack.Screen>

          <Stack.Screen name="Preview">
            {(props) =>
              mannequin ? (
                <SafeAreaView style={{ flex: 1, backgroundColor: "#12071f" }}>
                  <ScrollView contentContainerStyle={{ padding: 20, gap: 12 }}>
                    <MannequinPreviewScreen mannequin={mannequin} />

                    <View style={{ flexDirection: "row", gap: 8 }}>
                      <TouchableOpacity
                        onPress={() => props.navigation.reset({ index: 0, routes: [{ name: "Measurements" }] })}
                        style={{ flex: 1, backgroundColor: "#312044", padding: 12, borderRadius: 10, alignItems: "center" }}
                      >
                        <Text style={{ color: "white", fontWeight: "800" }}>Editar medidas</Text>
                      </TouchableOpacity>

                      <TouchableOpacity
                        onPress={() => props.navigation.navigate("Closet")}
                        style={{ flex: 1, backgroundColor: "#4c1d95", padding: 12, borderRadius: 10, alignItems: "center" }}
                      >
                        <Text style={{ color: "white", fontWeight: "800" }}>Meu Armário</Text>
                      </TouchableOpacity>
                    </View>

                    <View style={{ flexDirection: "row", gap: 8, marginTop: 12 }}>
                      <View style={{ flex: 1 }}>
                        <Text
                          style={{ color: "white", fontWeight: "800", marginBottom: 8 }}
                        >
                          Próximo passo
                        </Text>
                        <View style={{ gap: 8 }}>
                          <View style={{ flexDirection: "row", gap: 8 }}>
                            <Text
                              style={{ color: "#d8c7ff", fontWeight: "700" }}
                            >
                              Produto:
                            </Text>
                            <Text style={{ color: "#c4b5fd" }}>{productUrl ?? "Nenhum"}</Text>
                          </View>
                        </View>
                      </View>
                    </View>

                    <View style={{ flexDirection: "row", gap: 8 }}>
                      <View style={{ flex: 1 }}>
                        <TouchableOpacity
                          onPress={() => props.navigation.navigate("ProductUrl")}
                          style={{ backgroundColor: "#6b7280", padding: 12, borderRadius: 10, alignItems: "center" }}
                        >
                          <Text style={{ color: "white", fontWeight: "800" }}>URL do produto</Text>
                        </TouchableOpacity>
                      </View>

                      <View style={{ flex: 1 }}>
                        <TouchableOpacity
                          onPress={() => props.navigation.navigate("GarmentUpload")}
                          style={{ backgroundColor: "#8b5cf6", padding: 12, borderRadius: 10, alignItems: "center" }}
                        >
                          <Text style={{ color: "white", fontWeight: "800" }}>Upload da peça</Text>
                        </TouchableOpacity>
                      </View>

                      <View style={{ flex: 1 }}>
                        <TouchableOpacity
                          onPress={() => props.navigation.navigate("FitCheck")}
                          style={{ backgroundColor: "#3b82f6", padding: 12, borderRadius: 10, alignItems: "center" }}
                        >
                          <Text style={{ color: "white", fontWeight: "800" }}>Fit Check</Text>
                        </TouchableOpacity>
                      </View>
                    </View>
                  </ScrollView>
                </SafeAreaView>
              ) : (
                <MissingFlowScreen
                  message="Manequim ausente. Volte ao início para refazer o cálculo de corpo."
                  onRestart={() => props.navigation.reset({ index: 0, routes: [{ name: "Measurements" }] })}
                />
              )
            }
          </Stack.Screen>

          <Stack.Screen name="ProductUrl">
            {(props) =>
              mannequin ? (
                <ProductUrlScreen
                  initialUrl={productUrl}
                  onProductCaptured={(data) => {
                    const affiliateUrl = buildAffiliateUrl({ sourceUrl: data.product_url, sourceName: data.source_name, campaign: "virtual_try_on" });
                    setProductDetails(data.product ?? null);
                    setProductSource({
                      product_url: data.product_url,
                      affiliate_url: affiliateUrl,
                      source_name: data.source_name ?? data.product_title ?? null,
                      product_title: data.product_title ?? null,
                    });
                    setProductUrl(data.product_url);
                  }}
                  onContinue={() => props.navigation.navigate("FitCheck")}
                  onBack={() => props.navigation.navigate("Preview")}
                />
              ) : (
                <MissingFlowScreen
                  message="Não há manequim ativo. Volte ao início para continuar."
                  onRestart={() => props.navigation.reset({ index: 0, routes: [{ name: "Measurements" }] })}
                />
              )
            }
          </Stack.Screen>

          <Stack.Screen name="GarmentUpload">
            {(props) => (
              <GarmentUploadScreen
                onContinue={() => props.navigation.navigate("FitCheck")}
                onUploadComplete={async (result) => {
                  setGarment(result);
                  await addClosetItem(
                    createClosetItem({
                      garment: result,
                      source: productSource ?? null,
                    })
                  );
                }}
              />
            )}
          </Stack.Screen>

          <Stack.Screen name="FitCheck">
            {(props) =>
              mannequin ? (
                <FitCheckScreen
                  mannequin={mannequin}
                  product={productDetails}
                  onContinue={() => props.navigation.navigate("VtonPreview")}
                  onFitComplete={(result) => setFitCheckResult(result)}
                />
              ) : (
                <MissingFlowScreen
                  message="Manequim necessário para o Fit Check. Retorne ao início."
                  onRestart={() => props.navigation.reset({ index: 0, routes: [{ name: "Measurements" }] })}
                />
              )
            }
          </Stack.Screen>

          <Stack.Screen name="VtonPreview">
            {(props) =>
              mannequin ? (
                <VtonPreviewScreen
                  mannequin={mannequin}
                  fitZones={fitCheckResult?.zones ?? []}
                  garment={garment}
                  onFinish={() => props.navigation.navigate("VtonResult")}
                  onResultReady={({ result, payload, frontRender: fr }) => {
                    setVtonPayload(payload);
                    setVtonResult(result);
                    setFrontRender(fr);
                    props.navigation.navigate("VtonResult");
                  }}
                />
              ) : (
                <MissingFlowScreen
                  message="Dados insuficientes para VTON. Reinicie a jornada."
                  onRestart={() => props.navigation.reset({ index: 0, routes: [{ name: "Measurements" }] })}
                />
              )
            }
          </Stack.Screen>

          <Stack.Screen name="VtonResult">
            {(props) =>
              mannequin && vtonResult ? (
                <VtonResultScreen
                  mannequin={mannequin}
                  garment={garment}
                  frontRender={frontRender ?? null}
                  fitZones={fitCheckResult?.zones ?? []}
                  payload={vtonPayload ?? null}
                  result={vtonResult}
                  source={productSource}
                  onSaveLook={saveLook}
                  onOpenHistory={() => props.navigation.navigate("LookHistory")}
                  onBackToVton={() => props.navigation.navigate("VtonPreview")}
                />
              ) : (
                <MissingFlowScreen
                  message="Resultado VTON indisponível. Volte ao fluxo e gere um novo look."
                  onRestart={() => props.navigation.reset({ index: 0, routes: [{ name: "Measurements" }] })}
                />
              )
            }
          </Stack.Screen>

          <Stack.Screen name="LookHistory">
            {(props) => (
              <LookHistoryScreen
                looks={looks}
                onOpenLook={(look) => handleLookOpen(look, props.navigation)}
                onBack={() => props.navigation.navigate("Measurements")}
                onClear={clearHistory}
              />
            )}
          </Stack.Screen>

          <Stack.Screen name="Closet">
            {(props) =>
              mannequin ? (
                <ClosetScreen
                  items={closetItems}
                  onSelectItem={(item) => {
                    setGarment(item.garment);
                    setProductSource(item.source ?? null);
                    props.navigation.navigate("FitCheck");
                  }}
                  onBack={() => props.navigation.navigate("Preview")}
                  onClear={clearCloset}
                />
              ) : (
                <MissingFlowScreen
                  message="Manequim necessario para usar o armario. Volte ao inicio."
                  onRestart={() => props.navigation.reset({ index: 0, routes: [{ name: "Measurements" }] })}
                />
              )
            }
          </Stack.Screen>
        </Stack.Navigator>
        {loading && (
          <View style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, justifyContent: "center", alignItems: "center", backgroundColor: "rgba(0,0,0,0.3)" }}>
            <ActivityIndicator size="large" color="white" />
          </View>
        )}
      </NavigationContainer>
      <StatusBar style="light" />
    </SafeAreaProvider>
  );
}
