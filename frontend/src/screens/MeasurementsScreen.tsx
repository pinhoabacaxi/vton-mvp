import React, { useState } from "react";
import { Alert, ScrollView, Text, View } from "react-native";
import {
  AppScreen,
  FashionCard,
  JourneyStepper,
  MeasurementInput,
  PrimaryButton,
  StepHeader,
  fashionColors,
} from "../components/FashionUI";
import { InitialBodyInput } from "../types/body";

type Props = {
  onSubmit: (data: InitialBodyInput) => void;
};

export function MeasurementsScreen({ onSubmit }: Props) {
  const [height, setHeight] = useState("170");
  const [weight, setWeight] = useState("70");
  const [age, setAge] = useState("25");

  function submit() {
    const data = {
      height_cm: Number(height),
      weight_kg: Number(weight),
      age: Number(age),
    };

    if (!data.height_cm || !data.weight_kg || !data.age) {
      Alert.alert("Faltam alguns dados", "Preencha altura, peso e idade para começarmos.");
      return;
    }

    if (data.height_cm < 120 || data.height_cm > 230 || data.weight_kg < 30 || data.weight_kg > 250) {
      Alert.alert(
        "Confira os valores",
        "Use medidas aproximadas e reais para que o provador fique mais parecido com você."
      );
      return;
    }

    onSubmit(data);
  }

  return (
    <AppScreen>
      <ScrollView contentContainerStyle={{ padding: 24, gap: 18 }}>
        <StepHeader
          eyebrow="Provador virtual"
          step="1 de 5"
          title="Monte seu provador"
          subtitle="Vamos criar uma base aproximada para visualizar caimento, proporção e estilo antes de comprar. Você poderá ajustar tudo depois."
        />
        <JourneyStepper activeStep="profile" />

        <FashionCard highlighted>
          <Text style={{ color: fashionColors.text, fontWeight: "900", fontSize: 17 }}>
            Um começo simples
          </Text>
          <Text style={{ color: fashionColors.textSoft, lineHeight: 21 }}>
            Nesta etapa usamos apenas dados gerais para sugerir silhuetas de partida. O resultado é uma estimativa visual, não uma medida perfeita do corpo.
          </Text>
        </FashionCard>

        <View style={{ gap: 14 }}>
          <MeasurementInput label="Altura" value={height} onChangeText={setHeight} placeholder="cm" />
          <MeasurementInput label="Peso aproximado" value={weight} onChangeText={setWeight} placeholder="kg" />
          <MeasurementInput label="Idade" value={age} onChangeText={setAge} />
        </View>

        <FashionCard>
          <Text style={{ color: fashionColors.text, fontWeight: "900" }}>
            Privacidade e controle
          </Text>
          <Text style={{ color: fashionColors.textSoft, lineHeight: 21 }}>
            Suas medidas servem para montar seu provador e podem ser editadas quando quiser. Evitamos linguagem de julgamento: a ideia é encontrar caimento e estilo.
          </Text>
        </FashionCard>

        <PrimaryButton label="Ver silhuetas sugeridas" onPress={submit} />
      </ScrollView>
    </AppScreen>
  );
}
