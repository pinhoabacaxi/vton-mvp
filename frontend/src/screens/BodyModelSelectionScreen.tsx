import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Image,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { getBodyModelPreviews, resolveApiUrl } from "../api/client";
import {
  AppScreen,
  FashionCard,
  InfoPill,
  JourneyStepper,
  StepHeader,
  fashionColors,
} from "../components/FashionUI";
import { BodyModel, BodyModelPreview, BodyRecommendationResponse } from "../types/body";

type Props = {
  recommendation: BodyRecommendationResponse;
  onSelect: (model: BodyModel) => void;
};

export function BodyModelSelectionScreen({ recommendation, onSelect }: Props) {
  const [previews, setPreviews] = useState<BodyModelPreview[]>([]);
  const [loadingPreviews, setLoadingPreviews] = useState(true);

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
      })
      .finally(() => {
        if (mounted) {
          setLoadingPreviews(false);
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
    <AppScreen>
      <ScrollView contentContainerStyle={{ padding: 24, gap: 14 }}>
        <StepHeader
          eyebrow="Silhueta"
          step="2 de 5"
          title="Escolha uma silhueta de partida"
          subtitle="Selecione a base que mais parece com você hoje. Ela é só o ponto inicial: as medidas refinam o provador na próxima etapa."
        />
        <JourneyStepper activeStep="silhouette" />

        {loadingPreviews ? (
          <FashionCard>
            <ActivityIndicator color={fashionColors.text} />
            <Text style={{ color: fashionColors.textSoft, textAlign: "center" }}>
              Carregando miniaturas das silhuetas...
            </Text>
          </FashionCard>
        ) : null}

        {recommendation.models.map((model) => (
          <ModelCard
            key={model.id}
            model={model}
            previewUrl={resolveApiUrl(previewsByModel.get(model.id)?.preview_url)}
            onPress={() => onSelect(model)}
          />
        ))}
      </ScrollView>
    </AppScreen>
  );
}

function ModelCard(props: {
  model: BodyModel;
  previewUrl: string | null;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity onPress={props.onPress} activeOpacity={0.88}>
      <FashionCard highlighted={props.model.recommended} style={{ flexDirection: "row", gap: 12 }}>
        <View
          style={{
            width: 96,
            height: 132,
            borderRadius: 16,
            backgroundColor: "#170b25",
            overflow: "hidden",
            borderWidth: 1,
            borderColor: "#3f2458",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {props.previewUrl ? (
            <Image
              source={{ uri: props.previewUrl }}
              style={{ width: "100%", height: "100%" }}
              resizeMode="cover"
            />
          ) : (
            <Text style={{ color: fashionColors.textMuted, textAlign: "center", fontSize: 12 }}>
              Prévia em breve
            </Text>
          )}
        </View>

        <View style={{ flex: 1, justifyContent: "center", gap: 8 }}>
          <Text style={{ color: fashionColors.text, fontSize: 18, fontWeight: "900" }}>
            {props.model.label}
          </Text>

          <Text style={{ color: fashionColors.textSoft, lineHeight: 20 }}>
            {props.model.description}
          </Text>

          {props.model.recommended ? (
            <InfoPill label="Mais próximo do seu perfil" tone="gold" />
          ) : null}
        </View>
      </FashionCard>
    </TouchableOpacity>
  );
}
