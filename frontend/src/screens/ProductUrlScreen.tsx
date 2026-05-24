import * as ImagePicker from "expo-image-picker";
import React, { useRef, useState } from "react";
import {
  Alert,
  Image,
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { resolveApiUrl, scrapeProduct, uploadSizeChartImage } from "../api/client";
import {
  AppScreen,
  FashionCard,
  InfoPill,
  JourneyStepper,
  PremiumEmptyState,
  PrimaryButton,
  SecondaryButton,
  StepHeader,
  fashionColors,
} from "../components/FashionUI";
import { ProductScrapeResult, SizeMeasurement } from "../types/product";

type Props = {
  initialUrl?: string | null;
  onContinue: () => void;
  onProductCaptured?: (data: {
    product_url: string;
    source_name?: string | null;
    product_title?: string | null;
    product?: ProductScrapeResult | null;
  }) => void;
  onBack: () => void;
  onUploadPhoto?: () => void;
};

type ManualMeasurements = {
  sizeLabel: string;
  chest: string;
  waist: string;
  hip: string;
  length: string;
};

const initialManualMeasurements: ManualMeasurements = {
  sizeLabel: "M",
  chest: "",
  waist: "",
  hip: "",
  length: "",
};

export function ProductUrlScreen({
  initialUrl,
  onContinue,
  onProductCaptured,
  onBack,
  onUploadPhoto,
}: Props) {
  const scrollRef = useRef<ScrollView>(null);
  const [url, setUrl] = useState(initialUrl ?? "");
  const [loading, setLoading] = useState(false);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [product, setProduct] = useState<ProductScrapeResult | null>(null);
  const [linkError, setLinkError] = useState<string | null>(null);
  const [manualOpen, setManualOpen] = useState(false);
  const [manual, setManual] = useState(initialManualMeasurements);

  function showLinkError(message: string) {
    Keyboard.dismiss();
    setLinkError(message);
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 80);
  }

  function detectSourceName(value: string): string | null {
    try {
      return new URL(value).hostname.replace("www.", "");
    } catch {
      return null;
    }
  }

  function captureProduct(result: ProductScrapeResult, sourceUrl: string) {
    console.info("[State] Product measurements persisted", {
      source: result.extraction_method ?? "unknown",
      sizeCount: result.normalized_sizes?.length ?? 0,
      confidence: result.confidence_score ?? null,
    });
    setProduct(result);
    onProductCaptured?.({
      product_url: result.source_url ?? sourceUrl,
      source_name: detectSourceName(result.source_url ?? sourceUrl),
      product_title: result.title ?? null,
      product: result,
    });
  }

  async function submit() {
    const trimmedUrl = url.trim();

    if (!trimmedUrl) {
      Alert.alert("Cole o link da peça", "Use o link da página pública do produto na loja.");
      return;
    }

    try {
      const parsedUrl = new URL(trimmedUrl);
      if (!["http:", "https:"].includes(parsedUrl.protocol)) {
        showLinkError("Use um link público começando com http:// ou https://.");
        return;
      }
    } catch {
      showLinkError("Use um link público de produto, começando com http:// ou https://.");
      return;
    }

    setLoading(true);
    setLinkError(null);
    try {
      console.info("[API] Scraping product link", { host: detectSourceName(trimmedUrl) });
      const result = await scrapeProduct(trimmedUrl);
      captureProduct(result, trimmedUrl);
    } catch (err) {
      console.info("[Flow] Product link failed", {
        message: err instanceof Error ? err.message : "unknown",
      });
      showLinkError(
        err instanceof Error
          ? err.message
          : "Não conseguimos ler esse link. Você pode enviar um print da tabela ou preencher as medidas manualmente."
      );
    } finally {
      setLoading(false);
    }
  }

  async function pickSizeChartImage() {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert("Permissão necessária", "Autorize o acesso às imagens para enviar o print da tabela de medidas.");
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: false,
      quality: 0.9,
    });

    if (result.canceled || !result.assets?.[0]) {
      return;
    }

    const asset = result.assets[0];
    console.info("[Flow] User uploaded OCR image", {
      width: asset.width,
      height: asset.height,
    });
    setOcrLoading(true);
    setLinkError(null);
    try {
      const ocrResult = await uploadSizeChartImage({
        uri: asset.uri,
        name: asset.fileName ?? "tabela-medidas.jpg",
        type: asset.mimeType ?? "image/jpeg",
      });
      console.info("[API] OCR size chart completed", {
        sizeCount: ocrResult.normalized_sizes?.length ?? 0,
        confidence: ocrResult.confidence_score ?? null,
      });
      captureProduct(ocrResult, "ocr://size-chart");
      setManualOpen((ocrResult.normalized_sizes?.length ?? 0) === 0);
    } catch (err) {
      console.info("[Flow] OCR size chart failed", {
        message: err instanceof Error ? err.message : "unknown",
      });
      showLinkError(
        err instanceof Error
          ? err.message
          : "Não conseguimos ler o print. Você ainda pode preencher as medidas manualmente."
      );
      setManualOpen(true);
    } finally {
      setOcrLoading(false);
    }
  }

  function submitManualMeasurements() {
    const size = buildManualSize(manual);
    if (!size) {
      Alert.alert(
        "Complete pelo menos uma medida",
        "Preencha busto, cintura, quadril ou comprimento em centímetros."
      );
      return;
    }

    const result: ProductScrapeResult = {
      source_url: "manual://measurements",
      title: "Medidas preenchidas manualmente",
      image_url: null,
      currency: null,
      price: null,
      raw_size_text: manualText(size),
      normalized_sizes: [size],
      fabric_composition_text: null,
      fabric_analysis: null,
      confidence_score: 0.95,
      extraction_method: "manual_entry",
      fallback_reason: null,
      blocked_by_antibot: false,
    };

    console.info("[State] Manual measurements persisted", {
      sizeLabel: size.size_label,
      filledFields: [size.chest_cm, size.waist_cm, size.hip_cm, size.length_cm].filter((value) => value != null).length,
    });
    captureProduct(result, "manual://measurements");
    setLinkError(null);
    setManualOpen(false);
  }

  const productImageUrl = resolveApiUrl(product?.image_url);
  const measuresFound = product?.normalized_sizes?.length ?? 0;
  const confidencePercent =
    typeof product?.confidence_score === "number"
      ? Math.round(product.confidence_score * 100)
      : null;

  return (
    <AppScreen>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView
          ref={scrollRef}
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={{ padding: 24, gap: 16, paddingBottom: 40 }}
        >
          <StepHeader
            eyebrow="Peça"
            step="4 de 5"
            title="Adicionar peça"
            subtitle="Cole o link, envie um print da tabela de medidas ou preencha os dados principais. O provador continua mesmo quando a loja bloqueia a leitura automática."
          />
          <JourneyStepper activeStep="piece" />

          <FashionCard>
            <Text style={{ color: fashionColors.text, fontWeight: "900" }}>Link da peça</Text>
            <TextInput
              value={url}
              onChangeText={(value) => {
                setUrl(value);
                setLinkError(null);
              }}
              placeholder="https://loja.com/produto"
              placeholderTextColor="#9b86b8"
              autoCapitalize="none"
              autoCorrect={false}
              returnKeyType="go"
              keyboardType="url"
              onSubmitEditing={submit}
              blurOnSubmit
              style={inputStyle}
            />
            <PrimaryButton
              label={loading ? "Analisando a peça..." : "Analisar link"}
              onPress={submit}
              loading={loading}
            />
            <SecondaryButton
              label={ocrLoading ? "Lendo tabela..." : "Enviar print da tabela de medidas"}
              onPress={pickSizeChartImage}
              disabled={ocrLoading}
            />
            <SecondaryButton
              label={manualOpen ? "Ocultar preenchimento manual" : "Preencher medidas manualmente"}
              onPress={() => setManualOpen((value) => !value)}
            />
          </FashionCard>

          {linkError ? (
            <PremiumEmptyState
              variant="linkError"
              title="Não conseguimos ler este link."
              description="Algumas lojas bloqueiam a leitura automática. Você pode enviar um print da tabela de medidas ou preencher os dados principais da peça."
              actionLabel="Tentar outro link"
              onAction={() => setLinkError(null)}
              secondaryActionLabel="Enviar print da tabela"
              onSecondaryAction={pickSizeChartImage}
            />
          ) : null}

          {manualOpen ? (
            <ManualMeasurementsCard
              values={manual}
              onChange={setManual}
              onSubmit={submitManualMeasurements}
            />
          ) : null}

          {product ? (
            <FashionCard highlighted>
              <View style={{ flexDirection: "row", gap: 12 }}>
                <View
                  style={{
                    width: 92,
                    height: 122,
                    borderRadius: 16,
                    backgroundColor: "#f3e8ff",
                    overflow: "hidden",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  {productImageUrl ? (
                    <Image source={{ uri: productImageUrl }} style={{ width: "100%", height: "100%" }} resizeMode="cover" />
                  ) : (
                    <Text style={{ color: "#6d28d9", textAlign: "center", fontSize: 12 }}>
                      Sem imagem
                    </Text>
                  )}
                </View>

                <View style={{ flex: 1, gap: 8 }}>
                  <Text style={{ color: fashionColors.text, fontSize: 17, fontWeight: "900" }} numberOfLines={3}>
                    {product.title ?? "Peça encontrada"}
                  </Text>
                  {product.price ? (
                    <Text style={{ color: fashionColors.textSoft, fontWeight: "800" }}>
                      {product.price}
                    </Text>
                  ) : null}
                  <InfoPill
                    label={measuresFound > 0 ? `${measuresFound} tamanhos encontrados` : "Medidas não informadas"}
                    tone={measuresFound > 0 ? "gold" : "neutral"}
                  />
                  {confidencePercent !== null ? (
                    <InfoPill
                      label={`Confiança da leitura: ${confidencePercent}%`}
                      tone={confidencePercent >= 70 ? "gold" : "neutral"}
                    />
                  ) : null}
                </View>
              </View>

              {product.fabric_analysis ? (
                <Text style={{ color: fashionColors.textSoft, lineHeight: 20 }}>
                  Tecido analisado: elasticidade estimada {Math.round((product.fabric_analysis.stretch_factor ?? 0) * 100)}%, risco de encolhimento {Math.round((product.fabric_analysis.shrink_risk ?? 0) * 100)}%.
                </Text>
              ) : (
                <Text style={{ color: fashionColors.textSoft, lineHeight: 20 }}>
                  Se a loja não informar tecido ou medidas, sinalizamos a incerteza no caimento.
                </Text>
              )}

              <PrimaryButton label="Ver caimento" onPress={onContinue} />
            </FashionCard>
          ) : null}

          {onUploadPhoto ? (
            <SecondaryButton label="Enviar foto da peça" onPress={onUploadPhoto} />
          ) : null}
          <SecondaryButton label="Voltar ao provador" onPress={onBack} />
        </ScrollView>
      </KeyboardAvoidingView>
    </AppScreen>
  );
}

function ManualMeasurementsCard({
  values,
  onChange,
  onSubmit,
}: {
  values: ManualMeasurements;
  onChange: (values: ManualMeasurements) => void;
  onSubmit: () => void;
}) {
  const update = (key: keyof ManualMeasurements, value: string) => {
    onChange({ ...values, [key]: value });
  };

  return (
    <FashionCard>
      <Text style={{ color: fashionColors.text, fontWeight: "900", fontSize: 18 }}>
        Preencher medidas da peça
      </Text>
      <Text style={{ color: fashionColors.textSoft, lineHeight: 20 }}>
        Use os números da tabela da loja em centímetros. Não precisa preencher tudo agora.
      </Text>
      <LabeledInput label="Tamanho" value={values.sizeLabel} onChangeText={(text) => update("sizeLabel", text)} />
      <LabeledInput label="Busto/Tórax (cm)" value={values.chest} onChangeText={(text) => update("chest", text)} keyboardType="numeric" />
      <LabeledInput label="Cintura (cm)" value={values.waist} onChangeText={(text) => update("waist", text)} keyboardType="numeric" />
      <LabeledInput label="Quadril (cm)" value={values.hip} onChangeText={(text) => update("hip", text)} keyboardType="numeric" />
      <LabeledInput label="Comprimento (cm)" value={values.length} onChangeText={(text) => update("length", text)} keyboardType="numeric" />
      <PrimaryButton label="Usar essas medidas" onPress={onSubmit} />
    </FashionCard>
  );
}

function LabeledInput({
  label,
  value,
  onChangeText,
  keyboardType = "default",
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: "default" | "numeric";
}) {
  return (
    <View style={{ gap: 6 }}>
      <Text style={{ color: fashionColors.textSoft, fontWeight: "800" }}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        keyboardType={keyboardType}
        placeholder="Opcional"
        placeholderTextColor="#9b86b8"
        style={inputStyle}
      />
    </View>
  );
}

function buildManualSize(values: ManualMeasurements): SizeMeasurement | null {
  const size: SizeMeasurement = {
    size_label: values.sizeLabel.trim() || "M",
    chest_cm: parseCm(values.chest),
    waist_cm: parseCm(values.waist),
    hip_cm: parseCm(values.hip),
    length_cm: parseCm(values.length),
    confidence: 0.95,
    is_estimated: false,
  };

  if ([size.chest_cm, size.waist_cm, size.hip_cm, size.length_cm].every((value) => value == null)) {
    return null;
  }

  return size;
}

function manualText(size: SizeMeasurement): string {
  return [
    size.size_label,
    size.chest_cm != null ? `busto ${size.chest_cm} cm` : null,
    size.waist_cm != null ? `cintura ${size.waist_cm} cm` : null,
    size.hip_cm != null ? `quadril ${size.hip_cm} cm` : null,
    size.length_cm != null ? `comprimento ${size.length_cm} cm` : null,
  ]
    .filter(Boolean)
    .join(" ");
}

function parseCm(value: string): number | null {
  const parsed = Number(value.replace(",", "."));
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

const inputStyle = {
  backgroundColor: "#241233",
  color: fashionColors.text,
  padding: 14,
  borderRadius: 14,
  borderWidth: 1,
  borderColor: fashionColors.borderStrong,
  minHeight: 52,
};

export default ProductUrlScreen;
