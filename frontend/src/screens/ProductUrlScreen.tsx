import React, { useState } from "react";
import { SafeAreaView, View, Text, TextInput, TouchableOpacity, Alert } from "react-native";
import { scrapeProduct } from "../api/client";
import { ProductScrapeResult } from "../types/product";

type Props = {
  initialUrl?: string | null;
  onContinue: () => void;
  onProductCaptured?: (data: { product_url: string; source_name?: string | null; product_title?: string | null; product?: ProductScrapeResult | null }) => void;
  onBack: () => void;
};

export function ProductUrlScreen({ initialUrl, onContinue, onProductCaptured, onBack }: Props) {
  const [url, setUrl] = useState(initialUrl ?? "");
  const [loading, setLoading] = useState(false);
  const [product, setProduct] = useState<any | null>(null);

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
      Alert.alert("Informe a URL", "Digite a URL do produto.");
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

      onContinue();
    } catch (err) {
      Alert.alert("Erro ao analisar produto", err instanceof Error ? err.message : "Erro inesperado");
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#12071f" }}>
      <View style={{ padding: 20, gap: 12 }}>
        <Text style={{ color: "white", fontSize: 26, fontWeight: "800" }}>Produto / URL</Text>

        <Text style={{ color: "#d8c7ff" }}>Cole a URL do produto para referência futura.</Text>

        <TextInput value={url} onChangeText={setUrl} placeholder="https://example.com/product" placeholderTextColor="#7c6b8a" style={{ backgroundColor: "#241233", color: "white", padding: 12, borderRadius: 10, marginTop: 12 }} />

        {product && (
          <View style={{ backgroundColor: "#21102f", padding: 12, borderRadius: 10, marginTop: 12 }}>
            <Text style={{ color: "white", fontWeight: "800" }}>{product.title ?? 'Produto encontrado'}</Text>
            {product.image_url ? (
              <View style={{ marginTop: 8 }}>
                <Text style={{ color: "#c4b5fd" }}>Imagem:</Text>
                <Text style={{ color: "#c4b5fd" }}>{product.image_url}</Text>
              </View>
            ) : null}

            {product.price ? (
              <Text style={{ color: "#c4b5fd", marginTop: 6 }}>Preço: {product.price}</Text>
            ) : null}

            <Text style={{ color: "#c4b5fd", marginTop: 6 }}>{product.source_url}</Text>

            {product.fabric_analysis ? (
              <Text style={{ color: "#c4b5fd", marginTop: 6 }}>
                Tecido: stretch {Math.round((product.fabric_analysis.stretch_factor ?? 0) * 100)}% Ã¢â‚¬Â¢ encolhimento {Math.round((product.fabric_analysis.shrink_risk ?? 0) * 100)}%
              </Text>
            ) : null}

            {Array.isArray(product.normalized_sizes) && product.normalized_sizes.length > 0 ? (
              <View style={{ marginTop: 8 }}>
                <Text style={{ color: "#d8c7ff", fontWeight: "700" }}>Tamanhos normalizados</Text>
                {product.normalized_sizes.map((s: any, i: number) => (
                  <Text key={i} style={{ color: "#c4b5fd" }}>
                    • {s.size_label} — B:{s.chest_cm ?? '-'} C:{s.waist_cm ?? '-'} Q:{s.hip_cm ?? '-'} M:{s.sleeve_cm ?? '-'} Coxa:{s.thigh_cm ?? '-'} Entrep:{s.inseam_cm ?? '-'}
                  </Text>
                ))}
              </View>
            ) : null}
          </View>
        )}

        <View style={{ flexDirection: "row", gap: 8, marginTop: 12 }}>
          <TouchableOpacity onPress={onBack} style={{ flex: 1, backgroundColor: "#6b7280", padding: 12, borderRadius: 10, alignItems: "center" }}>
            <Text style={{ color: "white", fontWeight: "800" }}>Voltar</Text>
          </TouchableOpacity>

          <TouchableOpacity onPress={submit} disabled={loading} style={{ flex: 1, backgroundColor: loading ? '#6d28d9' : '#8b5cf6', padding: 12, borderRadius: 10, alignItems: "center" }}>
            <Text style={{ color: "white", fontWeight: "800" }}>{loading ? 'Analisando...' : 'Salvar e continuar'}</Text>
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
}

export default ProductUrlScreen;
