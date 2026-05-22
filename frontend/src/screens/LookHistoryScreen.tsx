import React from "react";
import { Alert, Image, ScrollView, Text, TouchableOpacity, View } from "react-native";
import {
  AppScreen,
  FashionCard,
  PremiumEmptyState,
  PrimaryButton,
  SecondaryButton,
  StepHeader,
  fashionColors,
} from "../components/FashionUI";
import { resolveApiUrl, submitFitFeedback } from "../api/client";
import { openExternalUrl, getPreferredBuyUrl } from "../utils/openExternalUrl";
import { buildFitSummaryForUser } from "../utils/fitCopy";
import { SavedLook } from "../types/look";

type Props = {
  looks: SavedLook[];
  onOpenLook: (look: SavedLook) => void;
  onBack: () => void;
  onClear: () => void;
};

export function LookHistoryScreen({ looks, onOpenLook, onBack, onClear }: Props) {
  async function sendFeedback(look: SavedLook, reportedStatus: "apertado" | "justo" | "folgado") {
    const predicted = dominantFitStatus(look.fit_zones);
    try {
      const result = await submitFitFeedback({
        user_key: "local-device",
        predicted_status: predicted,
        reported_status: reportedStatus,
      });
      Alert.alert("Obrigado pelo retorno", result.message);
    } catch (error) {
      Alert.alert("Não foi possível salvar sua resposta", error instanceof Error ? error.message : "Tente novamente em instantes.");
    }
  }

  return (
    <AppScreen>
      <ScrollView contentContainerStyle={{ padding: 20, gap: 14 }}>
        <StepHeader
          eyebrow="Looks"
          title="Histórico de looks"
          subtitle="Seus looks salvos ficam neste dispositivo para você comparar estilos e caimentos depois."
        />

        {looks.length === 0 ? (
          <PremiumEmptyState
            variant="history"
            title="Seus looks salvos aparecerão aqui."
            description="Experimente uma peça e salve o resultado para comparar caimentos e estilos depois."
            actionLabel="Criar primeiro look"
            onAction={onBack}
          />
        ) : (
          looks.map((look) => {
            const img = resolveApiUrl(look.vton_result.result_url ?? null);
            const buyUrl = getPreferredBuyUrl(look.source ?? null);

            return (
              <TouchableOpacity key={look.id} onPress={() => onOpenLook(look)} activeOpacity={0.9}>
                <FashionCard>
                  {img ? (
                    <Image
                      source={{ uri: img }}
                      style={{ width: "100%", height: 240, borderRadius: 14, marginBottom: 2 }}
                      resizeMode="cover"
                    />
                  ) : null}

                  <Text style={{ color: fashionColors.text, fontWeight: "900", fontSize: 17 }}>
                    {look.title}
                  </Text>
                  <Text style={{ color: fashionColors.textMuted }}>
                    {new Date(look.created_at).toLocaleString()}
                  </Text>
                  <Text style={{ color: fashionColors.textSoft, lineHeight: 20 }}>
                    {buildFitSummaryForUser(look.fit_zones)}
                  </Text>

                  {look.source ? (
                    <View style={{ gap: 4 }}>
                      <Text style={{ color: fashionColors.text, fontWeight: "800" }}>Peça</Text>
                      <Text style={{ color: fashionColors.textSoft }}>
                        {look.source.product_title ?? "Produto sem título"}
                        {look.source.source_name ? `\n${look.source.source_name}` : ""}
                      </Text>

                      {buyUrl ? (
                        <PrimaryButton
                          label="Ver na loja"
                          tone="secondary"
                          onPress={async () => {
                            try {
                              await openExternalUrl(buyUrl);
                            } catch (err) {
                              Alert.alert("Não foi possível abrir a compra", err instanceof Error ? err.message : "Tente novamente em instantes.");
                            }
                          }}
                        />
                      ) : null}
                    </View>
                  ) : null}

                  <View style={{ marginTop: 4, gap: 8 }}>
                    <Text style={{ color: fashionColors.textSoft, fontWeight: "800" }}>
                      Como essa peça ficou em você?
                    </Text>
                    <View style={{ flexDirection: "row", gap: 8 }}>
                      <TouchableOpacity onPress={() => sendFeedback(look, "apertado")} style={{ flex: 1, backgroundColor: "#7f1d1d", padding: 9, borderRadius: 10, alignItems: "center", justifyContent: "center", minHeight: 48 }}>
                        <Text style={{ color: "white", fontWeight: "800" }}>Pouca folga</Text>
                      </TouchableOpacity>
                      <TouchableOpacity onPress={() => sendFeedback(look, "justo")} style={{ flex: 1, backgroundColor: "#92400e", padding: 9, borderRadius: 10, alignItems: "center", justifyContent: "center", minHeight: 48 }}>
                        <Text style={{ color: "white", fontWeight: "800" }}>Próxima</Text>
                      </TouchableOpacity>
                      <TouchableOpacity onPress={() => sendFeedback(look, "folgado")} style={{ flex: 1, backgroundColor: "#14532d", padding: 9, borderRadius: 10, alignItems: "center", justifyContent: "center", minHeight: 48 }}>
                        <Text style={{ color: "white", fontWeight: "800" }}>Mais solta</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                </FashionCard>
              </TouchableOpacity>
            );
          })
        )}

        <View style={{ flexDirection: "row", gap: 8 }}>
          <View style={{ flex: 1 }}>
            <SecondaryButton label="Voltar" onPress={onBack} />
          </View>

          {looks.length > 0 ? (
            <View style={{ flex: 1 }}>
              <SecondaryButton
                label="Limpar histórico"
                onPress={() => {
                  Alert.alert("Limpar histórico", "Deseja limpar os looks salvos neste dispositivo?", [
                    { text: "Cancelar" },
                    { text: "Limpar", onPress: onClear },
                  ]);
                }}
              />
            </View>
          ) : null}
        </View>
      </ScrollView>
    </AppScreen>
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
