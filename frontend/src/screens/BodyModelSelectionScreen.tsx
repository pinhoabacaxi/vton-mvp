import React from "react";
import {
  SafeAreaView,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { BodyModel, BodyRecommendationResponse } from "../types/body";

type Props = {
  recommendation: BodyRecommendationResponse;
  onSelect: (model: BodyModel) => void;
};

export function BodyModelSelectionScreen({ recommendation, onSelect }: Props) {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#12071f" }}>
      <ScrollView contentContainerStyle={{ padding: 24, gap: 14 }}>
        <Text style={{ color: "white", fontSize: 28, fontWeight: "800" }}>
          Escolha uma base
        </Text>

        <Text style={{ color: "#d8c7ff", fontSize: 15 }}>
          IMC estimado: {recommendation.bmi}. Escolha o modelo que mais se aproxima do seu corpo.
        </Text>

        {recommendation.models.map((model) => (
          <TouchableOpacity
            key={model.id}
            onPress={() => onSelect(model)}
            style={{
              backgroundColor: model.recommended ? "#3b1c5c" : "#21102f",
              padding: 16,
              borderRadius: 18,
              borderWidth: 1,
              borderColor: model.recommended ? "#a78bfa" : "#3f2458",
            }}
          >
            <Text style={{ color: "white", fontSize: 18, fontWeight: "800" }}>
              {model.label}
            </Text>

            <Text style={{ color: "#d8c7ff", marginTop: 6 }}>
              {model.description}
            </Text>

            {model.recommended && (
              <Text style={{ color: "#c4b5fd", marginTop: 8, fontWeight: "700" }}>
                Recomendado
              </Text>
            )}
          </TouchableOpacity>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}
