import React, { useMemo, useState } from "react";
import {
  Alert,
  SafeAreaView,
  ScrollView,
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
  const [shoulder, setShoulder] = useState("");
  const [sleeve, setSleeve] = useState("");
  const [biceps, setBiceps] = useState("");
  const [inseam, setInseam] = useState("");
  const [thigh, setThigh] = useState("");
  const [topLength, setTopLength] = useState("");
  const [skinTone, setSkinTone] = useState("medium");
  const estimates = useMemo(
    () =>
      estimateAdvancedMeasurements({
        height: initial.height_cm,
        weight: initial.weight_kg,
        chest: Number(chest) || 95,
        hip: Number(hip) || 98,
      }),
    [chest, hip, initial.height_cm, initial.weight_kg]
  );

  function submit() {
    const optionalNumber = (value: string) => {
      const parsed = Number(value);
      return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
    };

    const data: FineTuneInput = {
      base_model_id: selectedModel.id,
      height_cm: initial.height_cm,
      weight_kg: initial.weight_kg,
      age: initial.age,
      chest_cm: Number(chest),
      waist_cm: Number(waist),
      hip_cm: Number(hip),
      shoulder_cm: optionalNumber(shoulder),
      sleeve_cm: optionalNumber(sleeve),
      biceps_cm: optionalNumber(biceps),
      top_length_cm: optionalNumber(topLength),
      inseam_cm: optionalNumber(inseam),
      thigh_cm: optionalNumber(thigh),
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
      <ScrollView contentContainerStyle={{ padding: 24, gap: 16 }}>
        <Text style={{ color: "white", fontSize: 28, fontWeight: "800" }}>
          Ajuste fino
        </Text>

        <Text style={{ color: "#d8c7ff", fontSize: 15 }}>
          Modelo base: {selectedModel.label}
        </Text>

        <Text style={{ color: "#bca7df", fontSize: 13 }}>
          Caminho rapido: confirme busto, cintura e quadril. O restante fica estimado e editavel.
        </Text>

        <Input label="Busto/Tórax em cm" value={chest} onChangeText={setChest} />
        <Input label="Cintura em cm" value={waist} onChangeText={setWaist} />
        <Input label="Quadril em cm" value={hip} onChangeText={setHip} />

        <View style={{ backgroundColor: "#21102f", borderRadius: 16, padding: 14, gap: 10, borderWidth: 1, borderColor: "#4c2a69" }}>
          <Text style={{ color: "white", fontWeight: "800", fontSize: 16 }}>
            Medidas avançadas
          </Text>
          <Text style={{ color: "#c4b5fd", fontSize: 13 }}>
            Use uma fita sem apertar o corpo. Bíceps mede a parte mais larga do braço; entrepernas vai da virilha ao tornozelo.
          </Text>
          <Text style={{ color: "#facc15", fontSize: 12, opacity: 0.78 }}>
            Estimativas IA: ombros {estimates.shoulder} cm, manga {estimates.sleeve} cm, biceps {estimates.biceps} cm, entrepernas {estimates.inseam} cm, coxa {estimates.thigh} cm.
          </Text>
          <Input label="Ombros em cm" value={shoulder} onChangeText={setShoulder} hint="Passe a fita de um ossinho do ombro ao outro." estimatedValue={estimates.shoulder} />
          <Input label="Manga/braço em cm" value={sleeve} onChangeText={setSleeve} hint="Do ossinho do ombro ao pulso." />
          <Input label="Bíceps em cm" value={biceps} onChangeText={setBiceps} hint="Circunferência da parte mais larga do braço." />
          <Input label="Comprimento superior em cm" value={topLength} onChangeText={setTopLength} hint="Do ombro até a barra de uma blusa." />
          <Input label="Entrepernas em cm" value={inseam} onChangeText={setInseam} hint="Da virilha até o tornozelo." />
          <Input label="Coxa em cm" value={thigh} onChangeText={setThigh} hint="Circunferência da parte alta da coxa." />
        </View>

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
      </ScrollView>
    </SafeAreaView>
  );
}

function estimateAdvancedMeasurements(input: {
  height: number;
  weight: number;
  chest: number;
  hip: number;
}) {
  const biceps = clamp(input.chest * 0.31 + input.weight * 0.025, 24, 52);
  return {
    shoulder: round(clamp(input.chest * 0.43, 34, 58)),
    sleeve: round(clamp(input.height * 0.35, 46, 76)),
    biceps: round(biceps),
    topLength: round(clamp(input.height * 0.36, 48, 82)),
    inseam: round(clamp(input.height * 0.46, 58, 96)),
    thigh: round(clamp(input.hip * 0.58, 42, 88)),
  };
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function round(value: number): number {
  return Math.round(value * 10) / 10;
}

function Input(props: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  hint?: string;
  estimatedValue?: number;
}) {
  const isEstimated = !props.value && props.estimatedValue != null;

  return (
    <View style={{ gap: 6, opacity: isEstimated ? 0.72 : 1 }}>
      <Text style={{ color: "#f5edff", fontWeight: "700" }}>{props.label}</Text>
      {isEstimated ? (
        <Text style={{ color: "#facc15", fontSize: 12, fontWeight: "700" }}>
          Estimativa da IA: {props.estimatedValue} cm. Toque para ajustar.
        </Text>
      ) : null}
      {props.hint ? (
        <Text style={{ color: "#bca7df", fontSize: 12 }}>{props.hint}</Text>
      ) : null}

      <TextInput
        value={props.value}
        onChangeText={props.onChangeText}
        keyboardType="numeric"
        placeholder={props.estimatedValue != null ? String(props.estimatedValue) : undefined}
        placeholderTextColor="#9b86b8"
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
