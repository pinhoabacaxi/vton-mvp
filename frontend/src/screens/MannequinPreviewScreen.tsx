import React from "react";
import { SafeAreaView, Text, View } from "react-native";
import { Mannequin3D } from "../components/Mannequin3D";
import { MannequinParams } from "../types/body";

type Props = {
  mannequin: MannequinParams;
};

export function MannequinPreviewScreen({ mannequin }: Props) {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#12071f" }}>
      <View style={{ padding: 20, gap: 14 }}>
        <Text style={{ color: "white", fontSize: 28, fontWeight: "800" }}>
          Seu manequim 3D
        </Text>

        <Text style={{ color: "#d8c7ff" }}>
          Prévia paramétrica inicial. Depois esta base pode ser trocada por um modelo GLB com morph targets reais.
        </Text>

        <Mannequin3D params={mannequin} />

        <Text style={{ color: "#d8c7ff" }}>
          Tórax: {mannequin.chest_cm} cm • Cintura: {mannequin.waist_cm} cm • Quadril: {mannequin.hip_cm} cm
        </Text>
      </View>
    </SafeAreaView>
  );
}
