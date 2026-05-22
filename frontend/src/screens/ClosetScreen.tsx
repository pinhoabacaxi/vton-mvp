import React from "react";
import {
  Alert,
  Image,
  SafeAreaView,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { resolveApiUrl } from "../api/client";
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
    Alert.alert("Limpar armario", "Deseja remover todas as pecas salvas?", [
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
    <SafeAreaView style={{ flex: 1, backgroundColor: "#12071f" }}>
      <ScrollView contentContainerStyle={{ padding: 24, gap: 16 }}>
        <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 12 }}>
          <View style={{ flex: 1 }}>
            <Text style={{ color: "white", fontSize: 28, fontWeight: "800" }}>
              Meu Armário
            </Text>
            <Text style={{ color: "#d8c7ff", marginTop: 6 }}>
              Pecas recortadas ficam salvas para novos looks.
            </Text>
          </View>

          <TouchableOpacity
            onPress={onBack}
            style={{
              backgroundColor: "#3b1c5c",
              paddingHorizontal: 14,
              paddingVertical: 10,
              borderRadius: 12,
              alignSelf: "flex-start",
            }}
          >
            <Text style={{ color: "white", fontWeight: "800" }}>Voltar</Text>
          </TouchableOpacity>
        </View>

        {items.length > 0 && (
          <TouchableOpacity
            onPress={confirmClear}
            style={{
              backgroundColor: "#450a0a",
              padding: 12,
              borderRadius: 14,
              alignItems: "center",
            }}
          >
            <Text style={{ color: "#fecaca", fontWeight: "800" }}>
              Limpar armario
            </Text>
          </TouchableOpacity>
        )}

        {items.length === 0 ? (
          <View
            style={{
              backgroundColor: "#21102f",
              borderRadius: 18,
              padding: 18,
              borderWidth: 1,
              borderColor: "#4c2a69",
            }}
          >
            <Text style={{ color: "white", fontWeight: "800", fontSize: 18 }}>
              Nenhuma peca salva ainda
            </Text>
            <Text style={{ color: "#d8c7ff", marginTop: 8 }}>
              Envie uma roupa, confirme o recorte e ela aparecera aqui.
            </Text>
          </View>
        ) : (
          items.map((item) => {
            const imageUrl =
              resolveApiUrl(item.garment.processed_url) ??
              resolveApiUrl(item.garment.original_url);

            return (
              <TouchableOpacity
                key={item.id}
                onPress={() => onSelectItem(item)}
                style={{
                  backgroundColor: "#21102f",
                  borderRadius: 18,
                  padding: 14,
                  gap: 12,
                  borderWidth: 1,
                  borderColor: "#4c2a69",
                }}
              >
                <Text style={{ color: "white", fontSize: 18, fontWeight: "800" }}>
                  {item.title}
                </Text>

                <Text style={{ color: "#c4b5fd" }}>
                  Salva em {new Date(item.created_at).toLocaleString()}
                </Text>

                {imageUrl && (
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
                )}

                <Text style={{ color: "#d8c7ff", fontWeight: "700" }}>
                  Ver caimento desta peca
                </Text>
              </TouchableOpacity>
            );
          })
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
