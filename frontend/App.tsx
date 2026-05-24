import "react-native-gesture-handler";
import React, { useRef, useState, useEffect } from "react";
import { ActivityIndicator, Alert, BackHandler, SafeAreaView, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { NavigationContainer, createNavigationContainerRef } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { enableScreens } from "react-native-screens";
import AsyncStorage from "@react-native-async-storage/async-storage";

import { recommendBodyModels, generateMannequin } from "./src/api/client";
import { InitialBodyInput, BodyRecommendationResponse, BodyModel, FineTuneInput, MannequinParams } from "./src/types/body";
import { createSavedLook, SavedLook, SaveLookInput } from "./src/types/look";
import { createClosetItem } from "./src/types/closet";
import { FitCheckResult, GarmentUploadResult, ProductScrapeResult } from "./src/types/product";
import { MannequinRenderResult } from "./src/types/mannequin";
import { VtonPayload, VtonRunResult } from "./src/types/vton";
import { buildAffiliateUrl } from "./src/utils/affiliate";
import { useVtonStore } from "./src/stores/useVtonStore";
import { useHistoryStore } from "./src/stores/useHistoryStore";
import { useClosetStore } from "./src/stores/useClosetStore";
import { loadSavedBodyProfile, saveSavedBodyProfile } from "./src/storage/bodyProfileStorage";

import { HomeScreen } from "./src/screens/HomeScreen";
import { MeasurementsScreen } from "./src/screens/MeasurementsScreen";
import { BodyModelSelectionScreen } from "./src/screens/BodyModelSelectionScreen";
import { FineTuneScreen } from "./src/screens/FineTuneScreen";
import ProductUrlScreen from "./src/screens/ProductUrlScreen";
import { GarmentUploadScreen } from "./src/screens/GarmentUploadScreen";
import { FitCheckScreen } from "./src/screens/FitCheckScreen";
import { VtonPreviewScreen } from "./src/screens/VtonPreviewScreen";
import VtonResultScreen from "./src/screens/VtonResultScreen";
import LookHistoryScreen from "./src/screens/LookHistoryScreen";
import ClosetScreen from "./src/screens/ClosetScreen";
import { ProvadorHubScreen } from "./src/screens/ProvadorHubScreen";

type RootStackParamList = {
  Home: undefined;
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
const navigationRef = createNavigationContainerRef<RootStackParamList>();
const LAST_ROUTE_KEY = "vton:last-route";
const RESUMABLE_ROUTES: Array<keyof RootStackParamList> = [
  "Home",
  "Measurements",
  "SelectModel",
  "FineTune",
  "Preview",
  "ProductUrl",
  "GarmentUpload",
  "FitCheck",
  "VtonPreview",
  "VtonResult",
  "LookHistory",
  "Closet",
];

function isResumableRoute(value: string | null): value is keyof RootStackParamList {
  return Boolean(value && RESUMABLE_ROUTES.includes(value as keyof RootStackParamList));
}

enableScreens();

function createRemoteGarmentFromProduct(product?: ProductScrapeResult | null): GarmentUploadResult | null {
  if (!product?.image_url) return null;

  return {
    filename: "product-link-image",
    content_type: "image/remote-url",
    original_path: product.image_url,
    processed_path: null,
    original_url: product.image_url,
    processed_url: product.image_url,
    background_removed: false,
    message: "Imagem da peça importada do link para a prévia visual.",
  };
}

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
  const [flowHydrated, setFlowHydrated] = useState(() => useVtonStore.persist.hasHydrated());
  const [resumeRouteName, setResumeRouteName] =
    useState<keyof RootStackParamList>("Home");
  const [navigationReady, setNavigationReady] = useState(false);
  const [currentRouteName, setCurrentRouteName] = useState<keyof RootStackParamList>("Home");
  const resumeAppliedRef = useRef(false);
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
    const unsubscribe = useVtonStore.persist.onFinishHydration(() => {
      console.info("[State] VTON flow restored from AsyncStorage");
      setFlowHydrated(true);
    });

    if (useVtonStore.persist.hasHydrated()) {
      setFlowHydrated(true);
    }

    return unsubscribe;
  }, []);

  useEffect(() => {
    let mounted = true;

    async function boot() {
      try {
        const [profile, lastRoute] = await Promise.all([
          loadSavedBodyProfile(),
          AsyncStorage.getItem(LAST_ROUTE_KEY),
          loadHistory(),
          loadCloset(),
        ]);

        if (!mounted) return;

        if (profile) {
          setInitialInput(profile.initial_input);
          setSelectedModel(profile.selected_model);
          setMannequin(profile.mannequin);
        }

        const routeToResume = isResumableRoute(lastRoute) ? lastRoute : "Home";
        console.info("[State] Last route loaded", { route: routeToResume });
        setResumeRouteName(routeToResume);
        setCurrentRouteName("Home");
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

  function rememberCurrentRoute() {
    const routeName = navigationRef.getCurrentRoute()?.name as keyof RootStackParamList | undefined;
    if (!routeName) return;
    setCurrentRouteName(routeName);
    console.info("[Flow] Route changed", { route: routeName });
    void AsyncStorage.setItem(LAST_ROUTE_KEY, routeName);
  }

  useEffect(() => {
    if (!navigationReady || resumeAppliedRef.current || resumeRouteName === "Home") {
      return;
    }

    resumeAppliedRef.current = true;
    console.info("[Flow] Resuming saved route", { route: resumeRouteName });
    requestAnimationFrame(() => {
      if (navigationRef.isReady()) {
        navigationRef.navigate(resumeRouteName);
      }
    });
  }, [navigationReady, resumeRouteName]);

  function getActiveRouteName(): keyof RootStackParamList {
    const navRoute = navigationRef.getCurrentRoute()?.name as keyof RootStackParamList | undefined;
    if (navRoute && navRoute !== "Home") {
      return navRoute;
    }
    return currentRouteName;
  }

  function handleGlobalBack(): boolean {
    const routeName = getActiveRouteName();
    if (routeName && routeName !== "Home" && navigationRef.canGoBack()) {
      console.info("[Flow] Android back", { from: routeName, action: "goBack" });
      navigationRef.goBack();
      return true;
    }
    if (routeName && routeName !== "Home" && navigationRef.isReady()) {
      console.info("[Flow] Android back", { from: routeName, action: "navigateHome" });
      navigationRef.navigate("Home");
      return true;
    }
    return false;
  }

  useEffect(() => {
    const subscription = BackHandler.addEventListener("hardwareBackPress", () => {
      return handleGlobalBack();
    });

    return () => subscription.remove();
  }, [currentRouteName]);
  async function handleInitialSubmit(data: InitialBodyInput, navigation: any) {
    setInitialInput(data);
    setLoading(true);

    try {
      const rec = await recommendBodyModels(data);
      setRecommendation(rec);
      navigation.navigate("SelectModel");
    } catch (err) {
      Alert.alert("Não conseguimos sugerir silhuetas", err instanceof Error ? err.message : "Tente novamente em instantes.");
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
      Alert.alert("Não conseguimos montar o provador", err instanceof Error ? err.message : "Tente novamente em instantes.");
    } finally {
      setLoading(false);
    }
  }

  async function saveLook(input: SaveLookInput) {
    try {
      const look = createSavedLook({ ...input, source: input.source ?? productSource ?? null });
      await addLook(look);
      Alert.alert("Look salvo", "Ele foi adicionado ao seu histórico.");
    } catch (error) {
      Alert.alert("Não foi possível salvar", error instanceof Error ? error.message : "Tente novamente em instantes.");
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

  if (bootingProfile || !flowHydrated) {
    return (
      <SafeAreaProvider>
        <SafeAreaView style={{ flex: 1, backgroundColor: "#12071f", justifyContent: "center", alignItems: "center", gap: 12 }}>
          <ActivityIndicator size="large" color="white" />
          <Text style={{ color: "#d8c7ff", fontWeight: "700" }}>
            Carregando seu provador...
          </Text>
        </SafeAreaView>
        <StatusBar style="light" />
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <NavigationContainer
        ref={navigationRef}
        onReady={() => {
          setNavigationReady(true);
          rememberCurrentRoute();
        }}
        onStateChange={rememberCurrentRoute}
      >
        <Stack.Navigator initialRouteName="Home" screenOptions={{ headerShown: false }}>
          <Stack.Screen name="Home">
            {(props) => (
              <HomeScreen
                hasProfile={Boolean(mannequin)}
                lookCount={looks.length}
                closetCount={closetItems.length}
                onStart={() => props.navigation.navigate("Measurements")}
                onContinue={() => props.navigation.navigate(mannequin ? "Preview" : "Measurements")}
                onOpenCloset={() => props.navigation.navigate(mannequin ? "Closet" : "Measurements")}
                onOpenHistory={() => props.navigation.navigate("LookHistory")}
              />
            )}
          </Stack.Screen>

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
                  message="Não encontramos sua sugestão de silhueta. Volte ao início para recomeçar com calma."
                  onRestart={() => props.navigation.reset({ index: 0, routes: [{ name: "Home" }] })}
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
                  message="Seu perfil ainda não está completo. Volte ao início para refazer as medidas."
                  onRestart={() => props.navigation.reset({ index: 0, routes: [{ name: "Home" }] })}
                />
              )
            }
          </Stack.Screen>

          <Stack.Screen name="Preview">
            {(props) =>
              mannequin ? (
                <ProvadorHubScreen
                  mannequin={mannequin}
                  productUrl={productUrl}
                  source={productSource}
                  hasGarment={Boolean(garment)}
                  onEditMeasurements={() => props.navigation.navigate("Measurements")}
                  onOpenCloset={() => props.navigation.navigate("Closet")}
                  onAddByLink={() => props.navigation.navigate("ProductUrl")}
                  onUploadPhoto={() => props.navigation.navigate("GarmentUpload")}
                  onCheckFit={() => props.navigation.navigate("FitCheck")}
                />
              ) : (
                <MissingFlowScreen
                  message="Seu provador ainda não está pronto. Volte ao início para montar novamente."
                  onRestart={() => props.navigation.reset({ index: 0, routes: [{ name: "Home" }] })}
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
                    const remoteGarment = createRemoteGarmentFromProduct(data.product);
                    setProductDetails(data.product ?? null);
                    setProductSource({
                      product_url: data.product_url,
                      affiliate_url: affiliateUrl,
                      source_name: data.source_name ?? data.product_title ?? null,
                      product_title: data.product_title ?? null,
                    });
                    if (remoteGarment) {
                      setGarment(remoteGarment);
                    }
                    setProductUrl(data.product_url);
                  }}
                  onContinue={() => props.navigation.navigate("FitCheck")}
                  onBack={() => props.navigation.navigate("Preview")}
                  onUploadPhoto={() => props.navigation.navigate("GarmentUpload")}
                />
              ) : (
                <MissingFlowScreen
                  message="Não há manequim ativo. Volte ao início para continuar."
                  onRestart={() => props.navigation.reset({ index: 0, routes: [{ name: "Home" }] })}
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
                  message="Monte seu provador antes de ver o caimento da peça."
                  onRestart={() => props.navigation.reset({ index: 0, routes: [{ name: "Home" }] })}
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
                  message="Faltam dados para gerar a prévia do look. Reinicie a jornada."
                  onRestart={() => props.navigation.reset({ index: 0, routes: [{ name: "Home" }] })}
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
                  message="Ainda não há uma prévia pronta. Volte ao fluxo e gere um novo look."
                  onRestart={() => props.navigation.reset({ index: 0, routes: [{ name: "Home" }] })}
                />
              )
            }
          </Stack.Screen>

          <Stack.Screen name="LookHistory">
            {(props) => (
              <LookHistoryScreen
                looks={looks}
                onOpenLook={(look) => handleLookOpen(look, props.navigation)}
                onBack={() => props.navigation.navigate("Home")}
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
                  message="Monte seu provador para usar o armário."
                  onRestart={() => props.navigation.reset({ index: 0, routes: [{ name: "Home" }] })}
                />
              )
            }
          </Stack.Screen>
        </Stack.Navigator>
        {currentRouteName !== "Home" ? (
          <TouchableOpacity
            accessibilityRole="button"
            accessibilityLabel="Voltar para a tela anterior"
            onPress={handleGlobalBack}
            style={styles.backPill}
          >
            <Text style={styles.backPillText}>Voltar</Text>
          </TouchableOpacity>
        ) : null}
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

const styles = StyleSheet.create({
  backPill: {
    position: "absolute",
    top: 44,
    left: 16,
    zIndex: 30,
    minHeight: 48,
    paddingHorizontal: 16,
    borderRadius: 999,
    backgroundColor: "rgba(32, 12, 52, 0.88)",
    borderWidth: 1,
    borderColor: "rgba(216, 199, 255, 0.45)",
    justifyContent: "center",
    shadowColor: "#000",
    shadowOpacity: 0.22,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 8,
  },
  backPillText: {
    color: "#f7f0ff",
    fontWeight: "900",
    fontSize: 15,
  },
});
