import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  SafeAreaView,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { checkFit } from "../api/client";
import { Mannequin3D } from "../components/Mannequin3D";
import { MannequinParams } from "../types/body";
import { FitCheckResult, SizeMeasurement } from "../types/product";

type Props = {
  mannequin: MannequinParams;
  onContinue: () => void;
  onFitComplete?: (result: FitCheckResult) => void;
};

export function FitCheckScreen({ mannequin, onContinue, onFitComplete }: Props) {
  const [sizeLabel, setSizeLabel] = useState("M");
  const [chest, setChest] = useState(String(Math.round(mannequin.chest_cm + 4)));
  const [waist, setWaist] = useState(String(Math.round(mannequin.waist_cm + 4)));
  const [hip, setHip] = useState(String(Math.round(mannequin.hip_cm + 4)));

  const [loading, setLoading] = useState(false);
  const [fitResult, setFitResult] = useState<FitCheckResult | null>(null);

  async function runFitCheck() {
    const garmentSize: SizeMeasurement = {
      size_label: sizeLabel.trim() || "Manual",
      chest_cm: Number(chest),
      waist_cm: Number(waist),
      hip_cm: Number(hip),
    };

    if (!garmentSize.chest_cm || !garmentSize.waist_cm || !garmentSize.hip_cm) {
      Alert.alert("Medidas incompletas", "Preencha tórax, cintura e quadril da peça.");
      return;
    }

    try {
      setLoading(true);

      const response = await checkFit({
        user_chest_cm: mannequin.chest_cm,
        user_waist_cm: mannequin.waist_cm,
        user_hip_cm: mannequin.hip_cm,
        garment_size: garmentSize,
      });

      setFitResult(response);
      onFitComplete && onFitComplete(response);
    } catch (error) {
      Alert.alert(
        "Erro no Fit Check",
        error instanceof Error ? error.message : "Erro inesperado"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: "#12071f" }}>
      <ScrollView contentContainerStyle={{ padding: 24, gap: 16 }}>
        <Text style={{ color: "white", fontSize: 28, fontWeight: "800" }}>
          Fit Check
        </Text>

        <Text style={{ color: "#d8c7ff", fontSize: 15 }}>
          Compare suas medidas com as medidas da peça e veja o mapa de caimento no manequim.
        </Text>

        <Mannequin3D params={mannequin} fitZones={fitResult?.zones} />

        <View
          style={{
            backgroundColor: "#21102f",
            borderRadius: 18,
            padding: 14,
            gap: 12,
            borderWidth: 1,
            borderColor: "#4c2a69",
          }}
        >
          <Text style={{ color: "white", fontSize: 18, fontWeight: "800" }}>
            Medidas da peça
          </Text>

          <Input label="Tamanho" value={sizeLabel} onChangeText={setSizeLabel} keyboardType="default" />
          <Input label="Busto/Tórax da peça em cm" value={chest} onChangeText={setChest} />
          <Input label="Cintura da peça em cm" value={waist} onChangeText={setWaist} />
          <Input label="Quadril da peça em cm" value={hip} onChangeText={setHip} />

          <TouchableOpacity
            onPress={runFitCheck}
            disabled={loading}
            style={{
              backgroundColor: loading ? "#5b3d87" : "#8b5cf6",
              padding: 16,
              borderRadius: 18,
              alignItems: "center",
            }}
          >
            {loading ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text style={{ color: "white", fontWeight: "800" }}>
                Calcular caimento
              </Text>
            )}
          </TouchableOpacity>
        </View>

        {fitResult && (
          <View
            style={{
              backgroundColor: "#21102f",
              borderRadius: 18,
              padding: 14,
              gap: 10,
              borderWidth: 1,
              borderColor: "#4c2a69",
            }}
          >
            <Text style={{ color: "white", fontSize: 18, fontWeight: "800" }}>
              Resultado
            </Text>

            <Text style={{ color: "#d8c7ff" }}>
              {fitResult.summary}
            </Text>

            <Legend />

            {fitResult.zones.map((zone) => (
              <View
                key={zone.zone}
                style={{
                  backgroundColor: "#2d1640",
                  borderRadius: 14,
                  padding: 12,
                  borderLeftWidth: 6,
                  borderLeftColor: colorToHex(zone.color),
                }}
              >
                <Text style={{ color: "white", fontWeight: "800" }}>
                  {zoneLabel(zone.zone)}
                </Text>

                <Text style={{ color: "#d8c7ff", marginTop: 4 }}>
                  {zone.message}
                </Text>

                <Text style={{ color: "#c4b5fd", marginTop: 4 }}>
                  Diferença: {zone.difference_cm ?? "-"} cm
                </Text>
              </View>
            ))}

            <TouchableOpacity
              onPress={onContinue}
              style={{
                backgroundColor: "#8b5cf6",
                padding: 14,
                borderRadius: 16,
                alignItems: "center",
              }}
            >
              <Text style={{ color: "white", fontWeight: "800" }}>
                Continuar para VTON
              </Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function Input(props: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: "numeric" | "default";
}) {
  return (
    <View style={{ gap: 6 }}>
      <Text style={{ color: "#f5edff", fontWeight: "700" }}>
        {props.label}
      </Text>

      <TextInput
        value={props.value}
        onChangeText={props.onChangeText}
        keyboardType={props.keyboardType ?? "numeric"}
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

function Legend() {
  return (
    <View style={{ gap: 6 }}>
      <Text style={{ color: "white", fontWeight: "800" }}>
        Legenda
      </Text>

      <LegendItem color="#ef4444" label="Vermelho: apertado ou pequeno" />
      <LegendItem color="#facc15" label="Amarelo: justo/próximo ao corpo" />
      <LegendItem color="#22c55e" label="Verde: folga confortável" />
      <LegendItem color="#9ca3af" label="Cinza: medida desconhecida" />
    </View>
  );
}

function LegendItem(props: { color: string; label: string }) {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
      <View
        style={{
          width: 14,
          height: 14,
          borderRadius: 7,
          backgroundColor: props.color,
        }}
      />

      <Text style={{ color: "#d8c7ff" }}>
        {props.label}
      </Text>
    </View>
  );
}

function colorToHex(color: string): string {
  switch (color) {
    case "red":
      return "#ef4444";
    case "yellow":
      return "#facc15";
    case "green":
      return "#22c55e";
    case "gray":
      return "#9ca3af";
    default:
      return "#8b5cf6";
  }
}

function zoneLabel(zone: string): string {
  switch (zone) {
    case "chest":
      return "Busto/Tórax";
    case "waist":
      return "Cintura";
    case "hip":
      return "Quadril";
    default:
      return zone;
  }
}
