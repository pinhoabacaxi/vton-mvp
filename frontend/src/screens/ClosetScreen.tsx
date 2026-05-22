import React from "react";
import { Alert, Image, ScrollView, Text, TouchableOpacity, View } from "react-native";

import { resolveApiUrl } from "../api/client";
import {
  AppScreen,
  FashionCard,
  PremiumEmptyState,
  SecondaryButton,
  StepHeader,
  fashionColors,
} from "../components/FashionUI";
import { ClosetItem } from "../types/closet";

type Props = {
  items: ClosetItem[];
  onSelectItem: (item: ClosetItem) => void;
  onBack: () => void;
  onClear: () => Promise<void> | void;
};

export default function ClosetScreen({
  items,
  onSelectItem,
  onBack,
  onClear,
}: Props) {
  async function confirmClear() {
    Alert.alert("Limpar armário", "Deseja remover todas as peças salvas?", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Limpar",
        style: "destructive",
        onPress: () => {
          void onClear();
        },
      },
    ]);
  }

  return (
    <AppScreen>
      <ScrollView contentContainerStyle={{ padding: 24, gap: 16 }}>
        <StepHeader
          eyebrow="Armário"
          title="Meu armário"
          subtitle="Peças preparadas ficam salvas para novas combinações e comparações de caimento."
        />

        {items.length === 0 ? (
          <PremiumEmptyState
            variant="closet"
            title="Seu provador está pronto."
            description="Salve peças para testar combinações e comparar caimentos depois."
            actionLabel="Adicionar primeira peça"
            onAction={onBack}
          />
        ) : (
          <>
            <View style={{ flexDirection: "row", gap: 10 }}>
              <View style={{ flex: 1 }}>
                <SecondaryButton label="Voltar" onPress={onBack} />
              </View>
              <View style={{ flex: 1 }}>
                <SecondaryButton label="Limpar armário" onPress={confirmClear} />
              </View>
            </View>

            {items.map((item) => {
              const imageUrl =
                resolveApiUrl(item.garment.processed_url) ??
                resolveApiUrl(item.garment.original_url);

              return (
                <TouchableOpacity key={item.id} onPress={() => onSelectItem(item)} activeOpacity={0.9}>
                  <FashionCard>
                    <Text style={{ color: fashionColors.text, fontSize: 18, fontWeight: "900" }}>
                      {item.title}
                    </Text>

                    <Text style={{ color: fashionColors.textMuted }}>
                      Salva em {new Date(item.created_at).toLocaleString()}
                    </Text>

                    {imageUrl ? (
                      <View
                        style={{
                          backgroundColor: "#f3e8ff",
                          borderRadius: 16,
                          height: 220,
                          overflow: "hidden",
                        }}
                      >
                        <Image
                          source={{ uri: imageUrl }}
                          style={{ width: "100%", height: "100%" }}
                          resizeMode="contain"
                        />
                      </View>
                    ) : null}

                    <Text style={{ color: fashionColors.textSoft, fontWeight: "800" }}>
                      Ver caimento desta peça
                    </Text>
                  </FashionCard>
                </TouchableOpacity>
              );
            })}
          </>
        )}
      </ScrollView>
    </AppScreen>
  );
}
