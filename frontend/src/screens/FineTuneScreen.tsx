import React, { useMemo, useState } from "react";
import { Alert, ScrollView, Text, TouchableOpacity, View } from "react-native";
import {
  AppScreen,
  FashionCard,
  JourneyStepper,
  MeasurementInput,
  PrimaryButton,
  StepHeader,
  fashionColors,
} from "../components/FashionUI";
import { BodyModel, FineTuneInput, InitialBodyInput } from "../types/body";

type Props = {
  initial: InitialBodyInput;
  selectedModel: BodyModel;
  onSubmit: (data: FineTuneInput) => void;
};

const skinTones = [
  { value: "light", label: "Claro", color: "#f2c7a5" },
  { value: "medium", label: "Médio", color: "#c6865a" },
  { value: "dark", label: "Escuro", color: "#6b3f2a" },
  { value: "deep", label: "Profundo", color: "#3a241c" },
];

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
  const [advancedOpen, setAdvancedOpen] = useState(false);

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
      Alert.alert("Faltam medidas essenciais", "Preencha busto/tórax, cintura e quadril para montar seu provador.");
      return;
    }

    onSubmit(data);
  }

  return (
    <AppScreen>
      <ScrollView contentContainerStyle={{ padding: 24, gap: 16 }}>
        <StepHeader
          eyebrow="Medidas"
          step="3 de 5"
          title="Refinar medidas"
          subtitle={`Base escolhida: ${selectedModel.label}. Confirme as medidas principais; o restante pode ficar como estimativa e ser ajustado depois.`}
        />
        <JourneyStepper activeStep="refine" />

        <FashionCard highlighted>
          <Text style={{ color: fashionColors.text, fontWeight: "900", fontSize: 16 }}>
            Medidas essenciais
          </Text>
          <Text style={{ color: fashionColors.textSoft, lineHeight: 21 }}>
            Use a fita sem apertar o corpo. Essas medidas ajudam o app a estimar proporção e caimento, sem julgamento.
          </Text>
        </FashionCard>

        <MeasurementInput label="Busto ou tórax" value={chest} onChangeText={setChest} />
        <MeasurementInput label="Cintura" value={waist} onChangeText={setWaist} />
        <MeasurementInput label="Quadril" value={hip} onChangeText={setHip} />

        <FashionCard>
          <TouchableOpacity
            onPress={() => setAdvancedOpen((value) => !value)}
            style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12 }}
          >
            <View style={{ flex: 1, gap: 4 }}>
              <Text style={{ color: fashionColors.text, fontWeight: "900", fontSize: 16 }}>
                Refinar mais medidas
              </Text>
              <Text style={{ color: fashionColors.textSoft, lineHeight: 20 }}>
                Opcional. Ajuda em mangas, calças, vestidos e peças ajustadas.
              </Text>
            </View>
            <Text style={{ color: fashionColors.gold, fontWeight: "900" }}>
              {advancedOpen ? "Fechar" : "Abrir"}
            </Text>
          </TouchableOpacity>

          {!advancedOpen ? (
            <Text style={{ color: fashionColors.textMuted, fontSize: 12, lineHeight: 18 }}>
              Estimativas iniciais: ombros {estimates.shoulder} cm, manga {estimates.sleeve} cm, bíceps {estimates.biceps} cm, entrepernas {estimates.inseam} cm, coxa {estimates.thigh} cm.
            </Text>
          ) : null}

          {advancedOpen ? (
            <View style={{ gap: 14 }}>
              <MeasurementInput label="Ombros" value={shoulder} onChangeText={setShoulder} hint="Meça de um ossinho do ombro ao outro." estimatedValue={estimates.shoulder} />
              <MeasurementInput label="Comprimento da manga" value={sleeve} onChangeText={setSleeve} hint="Do ossinho do ombro ao pulso." estimatedValue={estimates.sleeve} />
              <MeasurementInput label="Bíceps" value={biceps} onChangeText={setBiceps} hint="Circunferência da parte mais larga do braço." estimatedValue={estimates.biceps} />
              <MeasurementInput label="Comprimento superior" value={topLength} onChangeText={setTopLength} hint="Do ombro até a barra de uma blusa." estimatedValue={estimates.topLength} />
              <MeasurementInput label="Entrepernas" value={inseam} onChangeText={setInseam} hint="Da virilha até o tornozelo." estimatedValue={estimates.inseam} />
              <MeasurementInput label="Coxa" value={thigh} onChangeText={setThigh} hint="Circunferência da parte alta da coxa." estimatedValue={estimates.thigh} />
            </View>
          ) : null}
        </FashionCard>

        <View style={{ gap: 10 }}>
          <Text style={{ color: fashionColors.text, fontWeight: "900" }}>Tom visual do manequim</Text>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
            {skinTones.map((tone) => (
              <TouchableOpacity
                key={tone.value}
                onPress={() => setSkinTone(tone.value)}
                style={{
                  paddingVertical: 10,
                  paddingHorizontal: 12,
                  borderRadius: 14,
                  backgroundColor: skinTone === tone.value ? fashionColors.primary : "#241233",
                  borderWidth: 1,
                  borderColor: skinTone === tone.value ? "#c4b5fd" : fashionColors.border,
                  flexDirection: "row",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <View style={{ width: 18, height: 18, borderRadius: 9, backgroundColor: tone.color }} />
                <Text style={{ color: fashionColors.text, fontWeight: "800" }}>{tone.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <PrimaryButton label="Montar meu provador" onPress={submit} />
      </ScrollView>
    </AppScreen>
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
