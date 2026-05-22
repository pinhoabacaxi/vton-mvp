import React, { useState } from "react";
import { Alert, Image, ScrollView, Text, TextInput, View } from "react-native";
import { resolveApiUrl, scrapeProduct } from "../api/client";
import {
  AppScreen,
  FashionCard,
  InfoPill,
  PrimaryButton,
  SecondaryButton,
  StepHeader,
  fashionColors,
} from "../components/FashionUI";
import { ProductScrapeResult } from "../types/product";

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
};

export function ProductUrlScreen({ initialUrl, onContinue, onProductCaptured, onBack }: Props) {
  const [url, setUrl] = useState(initialUrl ?? "");
  const [loading, setLoading] = useState(false);
  const [product, setProduct] = useState<ProductScrapeResult | null>(null);

  function detectSourceName(u: string): string | null {
    try {
      const host = new URL(u).hostname.replace("www.", "");
      return host;
    } catch {
      return null;
    }
  }

  async function submit() {
    if (!url.trim()) {
      Alert.alert("Cole o link da peça", "Use o link da página do produto na loja.");
      return;
    }

    setLoading(true);
    try {
      const result = await scrapeProduct(url.trim());
      setProduct(result);

      const sourceName = detectSourceName(result.source_url ?? url.trim());

      onProductCaptured?.({
        product_url: result.source_url ?? url.trim(),
        source_name: sourceName,
        product_title: result.title ?? null,
        product: result,
      });
    } catch (err) {
      Alert.alert(
        "Não conseguimos ler esse link",
        err instanceof Error ? err.message : "Tente outro link ou envie uma foto da peça."
      );
    } finally {
      setLoading(false);
    }
  }

  const productImageUrl = resolveApiUrl(product?.image_url);
  const measuresFound = product?.normalized_sizes?.length ?? 0;

  return (
    <AppScreen>
      <ScrollView contentContainerStyle={{ padding: 24, gap: 16 }}>
        <StepHeader
          eyebrow="Peça"
          step="4 de 5"
          title="Adicionar peça por link"
          subtitle="Cole o link da loja para tentarmos encontrar imagem, nome, preço e medidas. Se a loja esconder alguma informação, o app faz uma estimativa cuidadosa."
        />

        <FashionCard>
          <Text style={{ color: fashionColors.text, fontWeight: "900" }}>Link da peça</Text>
          <TextInput
            value={url}
            onChangeText={setUrl}
            placeholder="https://loja.com/produto"
            placeholderTextColor="#9b86b8"
            autoCapitalize="none"
            keyboardType="url"
            style={{
              backgroundColor: "#241233",
              color: fashionColors.text,
              padding: 14,
              borderRadius: 14,
              borderWidth: 1,
              borderColor: fashionColors.borderStrong,
            }}
          />
          <PrimaryButton
            label={loading ? "Analisando a peça..." : "Analisar peça"}
            onPress={submit}
            loading={loading}
          />
        </FashionCard>

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
                  label={measuresFound > 0 ? `${measuresFound} tamanhos encontrados` : "Medidas não informadas pela loja"}
                  tone={measuresFound > 0 ? "gold" : "neutral"}
                />
              </View>
            </View>

            {product.fabric_analysis ? (
              <Text style={{ color: fashionColors.textSoft, lineHeight: 20 }}>
                Tecido analisado: elasticidade estimada {Math.round((product.fabric_analysis.stretch_factor ?? 0) * 100)}%, risco de encolhimento {Math.round((product.fabric_analysis.shrink_risk ?? 0) * 100)}%.
              </Text>
            ) : (
              <Text style={{ color: fashionColors.textSoft, lineHeight: 20 }}>
                Não encontramos composição do tecido. Vamos usar uma análise padrão e sinalizar incertezas no caimento.
              </Text>
            )}

            <PrimaryButton label="Ver caimento" onPress={onContinue} />
          </FashionCard>
        ) : null}

        <SecondaryButton label="Voltar ao provador" onPress={onBack} />
      </ScrollView>
    </AppScreen>
  );
}

export default ProductUrlScreen;
