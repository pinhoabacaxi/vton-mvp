import React, { useState } from "react";
import {
  Alert,
  SafeAreaView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { BodyModel, FineTuneInput, InitialBodyInput } from "../types/body";

type Props = {
  initial: InitialBodyInput;
  selectedModel: BodyModel;
  onSubmit: (data: FineTuneInput) => void;
};

const skinTones = ["light", "medium", "dark", "deep"];

export function FineTuneScreen({ initial, selectedModel, onSubmit }: Props) {
  const [chest, setChest] = useState("95");
  const [waist, setWaist] = useState("80");
  const [hip, setHip] = useState("98");
  const [skinTone, setSkinTone] = useState("medium");

  function submit() {
    const data: FineTuneInput = {
      base_model_id: selectedModel.id,
      height_cm: initial.height_cm,
      weight_kg: initial.weight_kg,
      age: initial.age,
      chest_cm: Number(chest),
      waist_cm: Number(waist),
      hip_cm: Number(hip),
      skin_tone: skinTone,
    };

    if (!data.chest_cm || !data.waist_cm || !data.hip_cm) {
      Alert.alert("Dados incompletos", "Preencha busto/tórax, cintura e quadril.");
      return;
    }

    onSubmit(data);
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#12071f" }}>
      <View style={{ padding: 24, gap: 16 }}>
        <Text style={{ color: "white", fontSize: 28, fontWeight: "800" }}>
          Ajuste fino
        </Text>

        <Text style={{ color: "#d8c7ff", fontSize: 15 }}>
          Modelo base: {selectedModel.label}
        </Text>

        <Input label="Busto/Tórax em cm" value={chest} onChangeText={setChest} />
        <Input label="Cintura em cm" value={waist} onChangeText={setWaist} />
        <Input label="Quadril em cm" value={hip} onChangeText={setHip} />

        <Text style={{ color: "white", fontWeight: "800" }}>Tom de pele</Text>

        <View style={{ flexDirection: "row", gap: 8 }}>
          {skinTones.map((tone) => (
            <TouchableOpacity
              key={tone}
              onPress={() => setSkinTone(tone)}
              style={{
                paddingVertical: 10,
                paddingHorizontal: 12,
                borderRadius: 14,
                backgroundColor: skinTone === tone ? "#8b5cf6" : "#241233",
              }}
            >
              <Text style={{ color: "white" }}>{tone}</Text>
            </TouchableOpacity>
          ))}
        </View>

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
            Gerar manequim 3D
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
