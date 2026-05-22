import React from "react";
import { SafeAreaView, ScrollView, View, Text, Image, TouchableOpacity, Alert } from "react-native";
import { SavedLook } from "../types/look";
import { openExternalUrl, getPreferredBuyUrl } from "../utils/openExternalUrl";
import { resolveApiUrl, submitFitFeedback } from "../api/client";

type Props = {
  looks: SavedLook[];
  onOpenLook: (look: SavedLook) => void;
  onBack: () => void;
  onClear: () => void;
};

function buildFitSummary(fitZones: SavedLook["fit_zones"]): string {
  if (fitZones.length === 0) return "Sem Fit Check.";

  const hasTight = fitZones.some((zone) =>
    zone.status === "apertado" || zone.status === "too_small" || zone.status === "tight" || zone.color === "red"
  );

  const hasBalanced = fitZones.some((zone) =>
    zone.status === "justo" || zone.status === "balanced" || zone.color === "yellow"
  );

  const hasLoose = fitZones.some((zone) =>
    zone.status === "folgado" || zone.status === "loose" || zone.color === "green" || zone.color === "blue"
  );

  if (hasTight) return "Pode apertar em algumas regiões.";
  if (hasBalanced) return "Caimento próximo ao corpo.";
  if (hasLoose) return "Folga confortável.";
  return "Caimento avaliado.";
}

export function LookHistoryScreen({ looks, onOpenLook, onBack, onClear }: Props) {
  async function sendFeedback(look: SavedLook, reportedStatus: "apertado" | "justo" | "folgado") {
    const predicted = dominantFitStatus(look.fit_zones);
    try {
      const result = await submitFitFeedback({
        user_key: "local-device",
        predicted_status: predicted,
        reported_status: reportedStatus,
      });
      Alert.alert("Feedback salvo", result.message);
    } catch (error) {
      Alert.alert("Nao foi possivel salvar feedback", error instanceof Error ? error.message : "Erro inesperado");
    }
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#12071f" }}>
      <ScrollView contentContainerStyle={{ padding: 20, gap: 12 }}>
        <Text style={{ color: "white", fontSize: 26, fontWeight: "800" }}>Histórico de looks</Text>

        <Text style={{ color: "#c4b5fd", marginBottom: 6 }}>Histórico salvo localmente neste dispositivo.</Text>

        {looks.length === 0 ? (
          <View style={{ backgroundColor: "#21102f", padding: 16, borderRadius: 12 }}>
            <Text style={{ color: "#d8c7ff" }}>Nenhum look salvo ainda.</Text>
          </View>
        ) : (
          looks.map((look) => {
            const img = resolveApiUrl(look.vton_result.result_url ?? null);

            return (
              <TouchableOpacity key={look.id} onPress={() => onOpenLook(look)} style={{ backgroundColor: "#21102f", borderRadius: 12, padding: 12 }}>
                {img ? (
                  <Image source={{ uri: img }} style={{ width: "100%", height: 240, borderRadius: 10, marginBottom: 8 }} resizeMode="cover" />
                ) : null}

                <Text style={{ color: "white", fontWeight: "800" }}>{look.title}</Text>
                <Text style={{ color: "#c4b5fd" }}>{new Date(look.created_at).toLocaleString()}</Text>
                <Text style={{ color: "#d8c7ff", marginTop: 6 }}>Provider: {look.vton_result.provider} • Fallback: {look.vton_result.used_fallback ? "sim" : "não"}</Text>
                <Text style={{ color: "#c4b5fd", marginTop: 4 }}>{buildFitSummary(look.fit_zones)}</Text>

                {look.source && (
                  <View style={{ marginTop: 8 }}>
                    <Text style={{ color: "#d8c7ff", fontWeight: "700" }}>Origem</Text>
                    <Text style={{ color: "#c4b5fd", fontWeight: "800" }}>{look.source.product_title ?? '-'}</Text>
                    <Text style={{ color: "#c4b5fd" }}>{look.source.source_name ?? "-"}</Text>
                    {look.source.product_url ? <Text style={{ color: "#c4b5fd" }}>{look.source.product_url}</Text> : null}
                    {look.source.affiliate_url ? <Text style={{ color: "#c4b5fd" }}>Affiliate: {look.source.affiliate_url}</Text> : null}

                    {getPreferredBuyUrl(look.source) && (
                      <TouchableOpacity
                        onPress={async () => {
                          try {
                            const buyUrl = getPreferredBuyUrl(look.source);
                            if (!buyUrl) throw new Error('URL de compra indisponível');
                            await openExternalUrl(buyUrl);
                          } catch (err) {
                            Alert.alert('Não foi possível abrir a compra', err instanceof Error ? err.message : 'Erro inesperado');
                          }
                        }}
                        style={{ marginTop: 8, backgroundColor: '#7c3aed', padding: 10, borderRadius: 10, alignItems: 'center' }}
                      >
                        <Text style={{ color: 'white', fontWeight: '800' }}>Comprar</Text>
                      </TouchableOpacity>
                    )}
                  </View>
                )}
                <View style={{ marginTop: 10, gap: 8 }}>
                  <Text style={{ color: "#d8c7ff", fontWeight: "700" }}>Como essa roupa ficou em voce?</Text>
                  <View style={{ flexDirection: "row", gap: 8 }}>
                    <TouchableOpacity onPress={() => sendFeedback(look, "apertado")} style={{ flex: 1, backgroundColor: "#7f1d1d", padding: 9, borderRadius: 10, alignItems: "center" }}>
                      <Text style={{ color: "white", fontWeight: "800" }}>Apertada</Text>
                    </TouchableOpacity>
                    <TouchableOpacity onPress={() => sendFeedback(look, "justo")} style={{ flex: 1, backgroundColor: "#92400e", padding: 9, borderRadius: 10, alignItems: "center" }}>
                      <Text style={{ color: "white", fontWeight: "800" }}>Justa</Text>
                    </TouchableOpacity>
                    <TouchableOpacity onPress={() => sendFeedback(look, "folgado")} style={{ flex: 1, backgroundColor: "#14532d", padding: 9, borderRadius: 10, alignItems: "center" }}>
                      <Text style={{ color: "white", fontWeight: "800" }}>Folgada</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              </TouchableOpacity>
            );
          })
        )}

        <View style={{ flexDirection: "row", gap: 8 }}>
          <TouchableOpacity onPress={onBack} style={{ flex: 1, backgroundColor: "#6b7280", padding: 12, borderRadius: 12, alignItems: "center" }}>
            <Text style={{ color: "white", fontWeight: "800" }}>Voltar</Text>
          </TouchableOpacity>

          {looks.length > 0 && (
            <TouchableOpacity onPress={() => { Alert.alert("Limpar histórico", "Deseja limpar o histórico local?", [{ text: "Cancelar" }, { text: "Limpar", onPress: onClear }]) }} style={{ flex: 1, backgroundColor: "#9ca3af", padding: 12, borderRadius: 12, alignItems: "center" }}>
              <Text style={{ color: "white", fontWeight: "800" }}>Limpar histórico</Text>
            </TouchableOpacity>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

export default LookHistoryScreen;

function dominantFitStatus(fitZones: SavedLook["fit_zones"]): string {
  if (fitZones.some((zone) => zone.status === "apertado" || zone.color === "red")) {
    return "apertado";
  }
  if (fitZones.some((zone) => zone.status === "justo" || zone.color === "yellow")) {
    return "justo";
  }
  return "folgado";
}
