import React from "react";
import { Text, View } from "react-native";
import { FashionCard, InfoPill, StepHeader, fashionColors } from "../components/FashionUI";
import { Mannequin3D } from "../components/Mannequin3D";
import { MannequinParams } from "../types/body";

type Props = {
  mannequin: MannequinParams;
  showHeader?: boolean;
};

export function MannequinPreviewScreen({ mannequin, showHeader = true }: Props) {
  return (
    <View style={{ gap: 14 }}>
      {showHeader ? (
        <StepHeader
          eyebrow="Provador"
          title="Seu provador está pronto"
          subtitle="Esta é uma base visual estimada para testar proporção, caimento e estilo. Você pode editar as medidas quando quiser."
        />
      ) : null}

      <InfoPill label="Prévia estimada" tone="gold" />

      <Mannequin3D params={mannequin} />

      <FashionCard>
        <Text style={{ color: fashionColors.text, fontWeight: "900" }}>
          Medidas principais
        </Text>
        <Text style={{ color: fashionColors.textSoft, lineHeight: 21 }}>
          Busto/tórax: {mannequin.chest_cm} cm • Cintura: {mannequin.waist_cm} cm • Quadril: {mannequin.hip_cm} cm
        </Text>
        <Text style={{ color: fashionColors.textMuted, fontSize: 13, lineHeight: 19 }}>
          Medidas extras ajudam em mangas, calças e peças mais ajustadas, mas podem ser refinadas depois.
        </Text>
      </FashionCard>
    </View>
  );
}
