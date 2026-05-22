import React, { useEffect, useMemo, useState } from "react";
import {
  Image,
  SafeAreaView,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { getBodyModelPreviews, resolveApiUrl } from "../api/client";
import { BodyModel, BodyModelPreview, BodyRecommendationResponse } from "../types/body";

type Props = {
  recommendation: BodyRecommendationResponse;
  onSelect: (model: BodyModel) => void;
};

export function BodyModelSelectionScreen({ recommendation, onSelect }: Props) {
  const [previews, setPreviews] = useState<BodyModelPreview[]>([]);

  useEffect(() => {
    let mounted = true;

    getBodyModelPreviews()
      .then((response) => {
        if (mounted) {
          setPreviews(response.previews);
        }
      })
      .catch(() => {
        if (mounted) {
          setPreviews([]);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  const previewsByModel = useMemo(() => {
    return new Map(previews.map((preview) => [preview.base_model_id, preview]));
  }, [previews]);

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
          <ModelCard
            key={model.id}
            model={model}
            previewUrl={resolveApiUrl(previewsByModel.get(model.id)?.preview_url)}
            onPress={() => onSelect(model)}
          />
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

function ModelCard(props: {
  model: BodyModel;
  previewUrl: string | null;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      onPress={props.onPress}
      style={{
        backgroundColor: props.model.recommended ? "#3b1c5c" : "#21102f",
        padding: 12,
        borderRadius: 18,
        borderWidth: 1,
        borderColor: props.model.recommended ? "#a78bfa" : "#3f2458",
        flexDirection: "row",
        gap: 12,
      }}
    >
      <View
        style={{
          width: 92,
          height: 124,
          borderRadius: 14,
          backgroundColor: "#170b25",
          overflow: "hidden",
          borderWidth: 1,
          borderColor: "#3f2458",
        }}
      >
        {props.previewUrl ? (
          <Image
            source={{ uri: props.previewUrl }}
            style={{ width: "100%", height: "100%" }}
            resizeMode="cover"
          />
        ) : null}
      </View>

      <View style={{ flex: 1, justifyContent: "center" }}>
        <Text style={{ color: "white", fontSize: 18, fontWeight: "800" }}>
          {props.model.label}
        </Text>

        <Text style={{ color: "#d8c7ff", marginTop: 6 }}>
          {props.model.description}
        </Text>

        {props.model.recommended && (
          <Text style={{ color: "#c4b5fd", marginTop: 8, fontWeight: "700" }}>
            Recomendado
          </Text>
        )}
      </View>
    </TouchableOpacity>
  );
}
