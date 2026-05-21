import React, { useState } from "react";
import {
  Alert,
  SafeAreaView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
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
      Alert.alert("Dados incompletos", "Preencha altura, peso e idade.");
      return;
    }

    onSubmit(data);
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#12071f" }}>
      <View style={{ padding: 24, gap: 18 }}>
        <Text style={{ color: "white", fontSize: 30, fontWeight: "800" }}>
          Crie seu manequim
        </Text>

        <Text style={{ color: "#d8c7ff", fontSize: 16 }}>
          Informe dados básicos para sugerirmos modelos corporais inclusivos e ajustáveis.
        </Text>

        <Input label="Altura em cm" value={height} onChangeText={setHeight} />
        <Input label="Peso em kg" value={weight} onChangeText={setWeight} />
        <Input label="Idade" value={age} onChangeText={setAge} />

        <TouchableOpacity
          onPress={submit}
          style={{
            backgroundColor: "#8b5cf6",
            padding: 16,
            borderRadius: 18,
            alignItems: "center",
          }}
        >
          <Text style={{ color: "white", fontSize: 16, fontWeight: "700" }}>
            Sugerir modelos
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

function Input(props: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
}) {
  return (
    <View style={{ gap: 6 }}>
      <Text style={{ color: "#f5edff", fontWeight: "700" }}>{props.label}</Text>

      <TextInput
        value={props.value}
        onChangeText={props.onChangeText}
        keyboardType="numeric"
        style={{
          backgroundColor: "#241233",
          color: "white",
          padding: 14,
          borderRadius: 14,
          borderWidth: 1,
          borderColor: "#6d35b8",
        }}
      />
    </View>
  );
}
