import React from "react";
import { ScrollView, Text, View } from "react-native";
import {
  AppScreen,
  FashionCard,
  InfoPill,
  PrimaryButton,
  SecondaryButton,
  StepHeader,
  fashionColors,
} from "../components/FashionUI";

type Props = {
  hasProfile: boolean;
  lookCount: number;
  closetCount: number;
  onStart: () => void;
  onContinue: () => void;
  onOpenCloset: () => void;
  onOpenHistory: () => void;
};

export function HomeScreen({
  hasProfile,
  lookCount,
  closetCount,
  onStart,
  onContinue,
  onOpenCloset,
  onOpenHistory,
}: Props) {
  return (
    <AppScreen>
      <ScrollView contentContainerStyle={{ padding: 24, gap: 18 }}>
        <View style={{ gap: 14, paddingTop: 8 }}>
          <InfoPill label="Provador virtual" tone="gold" />
          <StepHeader
            title="Monte seu provador virtual"
            subtitle="Visualize proporção, estilo e possíveis pontos de caimento antes de comprar. Tudo como estimativa visual, sem julgamento sobre corpo."
          />
        </View>

        <FashionCard highlighted>
          <Text style={{ color: fashionColors.text, fontSize: 18, fontWeight: "900" }}>
            Sua jornada de look
          </Text>
          <Text style={{ color: fashionColors.textSoft, lineHeight: 22 }}>
            Comece com uma silhueta base, refine medidas quando quiser e adicione uma peça por link ou foto para gerar uma prévia.
          </Text>
        </FashionCard>

        <View style={{ gap: 10 }}>
          {hasProfile ? (
            <PrimaryButton label="Continuar meu provador" onPress={onContinue} />
          ) : null}
          <PrimaryButton
            label={hasProfile ? "Refazer meu provador" : "Começar meu provador"}
            onPress={onStart}
            tone={hasProfile ? "secondary" : "primary"}
          />
        </View>

        <View style={{ flexDirection: "row", gap: 10 }}>
          <FashionCard style={{ flex: 1 }}>
            <Text style={{ color: fashionColors.text, fontWeight: "900", fontSize: 20 }}>
              {closetCount}
            </Text>
            <Text style={{ color: fashionColors.textSoft, fontWeight: "700" }}>
              peças no armário
            </Text>
          </FashionCard>

          <FashionCard style={{ flex: 1 }}>
            <Text style={{ color: fashionColors.text, fontWeight: "900", fontSize: 20 }}>
              {lookCount}
            </Text>
            <Text style={{ color: fashionColors.textSoft, fontWeight: "700" }}>
              looks salvos
            </Text>
          </FashionCard>
        </View>

        <View style={{ gap: 10 }}>
          <SecondaryButton label="Ver meu armário" onPress={onOpenCloset} disabled={!hasProfile} />
          <SecondaryButton label="Histórico de looks" onPress={onOpenHistory} />
        </View>

        <Text style={{ color: fashionColors.textMuted, fontSize: 12, lineHeight: 18, textAlign: "center" }}>
          O resultado ajuda na decisão, mas tecido, corte, iluminação e foto original podem alterar o caimento real.
        </Text>
      </ScrollView>
    </AppScreen>
  );
}
