import React from "react";
import { ScrollView, Text, View } from "react-native";
import {
  AppScreen,
  FashionCard,
  InfoPill,
  JourneyStepper,
  PrimaryButton,
  SecondaryButton,
  StepHeader,
  fashionColors,
} from "../components/FashionUI";
import { LookSource } from "../types/look";
import { MannequinParams } from "../types/body";
import { MannequinPreviewScreen } from "./MannequinPreviewScreen";

type Props = {
  mannequin: MannequinParams;
  productUrl?: string | null;
  source?: LookSource | null;
  hasGarment: boolean;
  onEditMeasurements: () => void;
  onOpenCloset: () => void;
  onAddByLink: () => void;
  onUploadPhoto: () => void;
  onCheckFit: () => void;
};

export function ProvadorHubScreen({
  mannequin,
  productUrl,
  source,
  hasGarment,
  onEditMeasurements,
  onOpenCloset,
  onAddByLink,
  onUploadPhoto,
  onCheckFit,
}: Props) {
  const pieceLabel = source?.product_title ?? source?.source_name ?? productUrl;

  return (
    <AppScreen>
      <ScrollView contentContainerStyle={{ padding: 20, gap: 14 }}>
        <StepHeader
          eyebrow="Provador"
          title="Seu provador"
          subtitle="A base visual está pronta. Agora adicione uma peça para comparar caimento e montar uma prévia do look."
        />
        <JourneyStepper activeStep="piece" />

        <MannequinPreviewScreen mannequin={mannequin} showHeader={false} />

        <FashionCard highlighted>
          <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
            <Text style={{ color: fashionColors.text, fontSize: 18, fontWeight: "900", flex: 1 }}>
              Próximo passo
            </Text>
            <InfoPill label={pieceLabel ? "Peça selecionada" : "Escolha uma peça"} tone={pieceLabel ? "purple" : "gold"} />
          </View>

          <Text style={{ color: fashionColors.textSoft, lineHeight: 22 }}>
            {pieceLabel
              ? pieceLabel
              : "Adicione um link de loja ou envie uma foto em fundo claro para preparar a prévia."}
          </Text>

          {hasGarment || pieceLabel ? (
            <PrimaryButton label="Ver caimento" onPress={onCheckFit} />
          ) : null}
        </FashionCard>

        <View style={{ flexDirection: "row", gap: 10 }}>
          <View style={{ flex: 1 }}>
            <PrimaryButton label="Adicionar por link" onPress={onAddByLink} tone="secondary" />
          </View>
          <View style={{ flex: 1 }}>
            <PrimaryButton label="Enviar foto da peça" onPress={onUploadPhoto} />
          </View>
        </View>

        <View style={{ flexDirection: "row", gap: 10 }}>
          <View style={{ flex: 1 }}>
            <SecondaryButton label="Editar medidas" onPress={onEditMeasurements} />
          </View>
          <View style={{ flex: 1 }}>
            <SecondaryButton label="Meu armário" onPress={onOpenCloset} />
          </View>
        </View>
      </ScrollView>
    </AppScreen>
  );
}
