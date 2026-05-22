import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { checkFit } from "../api/client";
import {
  AppScreen,
  FashionCard,
  JourneyStepper,
  PrimaryButton,
  StepHeader,
  fashionColors,
} from "../components/FashionUI";
import { Mannequin3D } from "../components/Mannequin3D";
import { MannequinParams } from "../types/body";
import { FitCheckResult, ProductScrapeResult, SizeMeasurement } from "../types/product";
import { buildFitCacheKey, loadFitCache, saveFitCache } from "../storage/fitCacheStorage";
import { buildFitInsight, buildFitSummaryForUser, buildSizeRecommendationText, fitColorToHex, fitZoneLabel } from "../utils/fitCopy";

type Props = {
  mannequin: MannequinParams;
  product?: ProductScrapeResult | null;
  onContinue: () => void;
  onFitComplete?: (result: FitCheckResult) => void;
};

export function FitCheckScreen({ mannequin, product, onContinue, onFitComplete }: Props) {
  const [sizeLabel, setSizeLabel] = useState("M");
  const [chest, setChest] = useState(String(Math.round(mannequin.chest_cm + 4)));
  const [waist, setWaist] = useState(String(Math.round(mannequin.waist_cm + 4)));
  const [hip, setHip] = useState(String(Math.round(mannequin.hip_cm + 4)));
  const [length, setLength] = useState("");
  const [sleeve, setSleeve] = useState("");
  const [biceps, setBiceps] = useState("");
  const [inseam, setInseam] = useState("");
  const [thigh, setThigh] = useState("");
  const [shoulder, setShoulder] = useState("");
  const [category, setCategory] = useState("top");
  const [stretchLevel, setStretchLevel] = useState("none");
  const [loading, setLoading] = useState(false);
  const [fitResult, setFitResult] = useState<FitCheckResult | null>(null);
  const [activeSizeLabel, setActiveSizeLabel] = useState(
    product?.normalized_sizes?.[0]?.size_label ?? "M"
  );

  const candidateSizes = useMemo(() => {
    if (product?.normalized_sizes?.length) return product.normalized_sizes;

    return extrapolateManualSizes({
      size_label: sizeLabel.trim() || activeSizeLabel,
      chest_cm: optionalNumber(chest),
      waist_cm: optionalNumber(waist),
      hip_cm: optionalNumber(hip),
      length_cm: optionalNumber(length),
      sleeve_cm: optionalNumber(sleeve),
      biceps_cm: optionalNumber(biceps),
      inseam_cm: optionalNumber(inseam),
      thigh_cm: optionalNumber(thigh),
      shoulder_cm: optionalNumber(shoulder),
      garment_category: category,
      stretch_level: stretchLevel,
    });
  }, [activeSizeLabel, biceps, category, chest, hip, inseam, length, product, shoulder, sizeLabel, sleeve, stretchLevel, thigh, waist]);

  const displayResult = useMemo(
    () => resultForSize(fitResult, activeSizeLabel),
    [activeSizeLabel, fitResult]
  );

  useEffect(() => {
    const firstSize = product?.normalized_sizes?.[0]?.size_label;
    if (firstSize) setActiveSizeLabel(firstSize);
  }, [product]);

  useEffect(() => {
    if (product?.normalized_sizes?.length && !fitResult && !loading) {
      runFitCheck();
    }
  }, [product?.normalized_sizes?.length]);

  async function runFitCheck() {
    const optionalNumber = (value: string) => {
      const parsed = Number(value);
      return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
    };

    const manualSize: SizeMeasurement = {
      size_label: sizeLabel.trim() || "Manual",
      chest_cm: optionalNumber(chest),
      waist_cm: optionalNumber(waist),
      hip_cm: optionalNumber(hip),
      length_cm: optionalNumber(length),
      sleeve_cm: optionalNumber(sleeve),
      biceps_cm: optionalNumber(biceps),
      inseam_cm: optionalNumber(inseam),
      thigh_cm: optionalNumber(thigh),
      shoulder_cm: optionalNumber(shoulder),
      garment_category: category,
      stretch_level: stretchLevel,
    };
    const garmentSize =
      candidateSizes.find((item) => item.size_label === activeSizeLabel) ?? manualSize;

    const hasAnyMeasurement = Object.entries(garmentSize).some(
      ([key, value]) => key.endsWith("_cm") && typeof value === "number" && value > 0
    );

    if (!hasAnyMeasurement) {
      Alert.alert("Faltam medidas da peça", "Preencha pelo menos uma medida informada pela loja ou siga com uma estimativa.");
      return;
    }

    try {
      setLoading(true);

      const payload = {
        user_chest_cm: mannequin.chest_cm,
        user_waist_cm: mannequin.waist_cm,
        user_hip_cm: mannequin.hip_cm,
        user_length_cm: mannequin.top_length_cm ?? null,
        user_sleeve_cm: mannequin.sleeve_cm ?? null,
        user_biceps_cm: mannequin.biceps_cm ?? null,
        user_top_length_cm: mannequin.top_length_cm ?? null,
        user_inseam_cm: mannequin.inseam_cm ?? null,
        user_thigh_cm: mannequin.thigh_cm ?? null,
        user_shoulder_cm: mannequin.shoulder_cm ?? null,
        user_rise_cm: mannequin.rise_cm ?? null,
        user_wrist_cm: mannequin.wrist_cm ?? null,
        garment_size: garmentSize,
        candidate_sizes: candidateSizes,
        garment_category: category,
        stretch_level: stretchLevel,
        fabric_analysis: product?.fabric_analysis ?? null,
      };
      const cacheKey = buildFitCacheKey(payload);
      const cached = await loadFitCache(cacheKey);
      const response = cached ?? await checkFit(payload);
      if (!cached) {
        await saveFitCache(cacheKey, response);
      }

      setFitResult(response);
      const bestLabel = response.best_size_label ?? response.selected_size_label ?? activeSizeLabel;
      setActiveSizeLabel(bestLabel);
      onFitComplete?.(resultForSize(response, bestLabel) ?? response);
    } catch (error) {
      Alert.alert(
        "Não conseguimos calcular o caimento",
        error instanceof Error ? error.message : "Tente novamente em instantes."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppScreen>
      <ScrollView contentContainerStyle={{ padding: 24, gap: 16 }}>
        <StepHeader
          eyebrow="Caimento"
          step="4 de 5"
          title="Como pode vestir"
          subtitle="Compare a peça com seu provador e veja uma estimativa visual de folga, proporção e conforto."
        />
        <JourneyStepper activeStep="piece" />

        <Mannequin3D params={mannequin} fitZones={displayResult?.zones} />

        <FashionCard>
          <Text style={{ color: fashionColors.text, fontSize: 18, fontWeight: "900" }}>
            Medidas da peça
          </Text>

          <SizeToggle
            sizes={candidateSizes}
            activeSizeLabel={activeSizeLabel}
            bestSizeLabel={fitResult?.best_size_label ?? null}
            onSelect={(label) => {
              setActiveSizeLabel(label);
              const nextResult = resultForSize(fitResult, label);
              if (nextResult) onFitComplete?.(nextResult);
            }}
          />
          <Input label="Tamanho" value={sizeLabel} onChangeText={setSizeLabel} keyboardType="default" />
          <SegmentedControl
            label="Categoria"
            value={category}
            options={[
              ["top", "Superior"],
              ["pants", "Inferior"],
              ["dress", "Vestido"],
              ["outerwear", "Casaco"],
              ["bodycon", "Justo"],
            ]}
            onChange={setCategory}
          />
          <SegmentedControl
            label="Elasticidade"
            value={stretchLevel}
            options={[
              ["none", "Sem"],
              ["low", "Baixa"],
              ["medium", "Média"],
              ["high", "Alta"],
            ]}
            onChange={setStretchLevel}
          />
          <Input label="Busto/tórax da peça em cm" value={chest} onChangeText={setChest} />
          <Input label="Cintura da peça em cm" value={waist} onChangeText={setWaist} />
          <Input label="Quadril da peça em cm" value={hip} onChangeText={setHip} />
          <Input label="Comprimento total em cm" value={length} onChangeText={setLength} />
          <Input label="Manga em cm" value={sleeve} onChangeText={setSleeve} />
          <Input label="Bíceps da peça em cm" value={biceps} onChangeText={setBiceps} />
          <Input label="Entrepernas em cm" value={inseam} onChangeText={setInseam} />
          <Input label="Coxa da peça em cm" value={thigh} onChangeText={setThigh} />
          <Input label="Ombro da peça em cm" value={shoulder} onChangeText={setShoulder} />

          <PrimaryButton label="Ver caimento" onPress={runFitCheck} loading={loading} />
        </FashionCard>

        {displayResult && (
          <FashionCard highlighted>
            <Text style={{ color: fashionColors.text, fontSize: 18, fontWeight: "900" }}>
              Resumo de caimento
            </Text>

            <Text style={{ color: "#d8c7ff" }}>
              {buildFitSummaryForUser(displayResult.zones)}
            </Text>

            <Text style={{ color: fashionColors.gold, fontWeight: "800", lineHeight: 20 }}>
              {buildSizeRecommendationText(displayResult)}
            </Text>

            {displayResult.best_size_label ? (
              <View style={{ backgroundColor: "#facc15", borderRadius: 999, paddingHorizontal: 12, paddingVertical: 7, alignSelf: "flex-start" }}>
                <Text style={{ color: "#2d1640", fontWeight: "900" }}>
                  Melhor opção: {displayResult.best_size_label}
                </Text>
              </View>
            ) : null}

            {displayResult.fabric_warnings?.map((warning) => (
              <Text key={warning} style={{ color: "#facc15", fontWeight: "700" }}>
                {warning}
              </Text>
            ))}

            <Legend />

            {displayResult.zones.map((zone) => (
              <View
                key={zone.zone}
                style={{
                  backgroundColor: "#2d1640",
                  borderRadius: 14,
                  padding: 12,
                  borderLeftWidth: 6,
                  borderLeftColor: fitColorToHex(zone.color),
                }}
              >
                <Text style={{ color: "white", fontWeight: "800" }}>
                  {fitZoneLabel(zone.zone)}
                </Text>

                <Text style={{ color: "#d8c7ff", marginTop: 4 }}>
                  {buildFitInsight(zone)}
                </Text>

                <Text style={{ color: "#c4b5fd", marginTop: 4 }}>
                  Diferença estimada: {zone.difference_cm ?? "-"} cm
                  {zone.ease_allowance_cm != null ? ` • Margem de conforto: ${zone.ease_allowance_cm} cm` : ""}
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
                Gerar prévia do look
              </Text>
            </TouchableOpacity>
          </FashionCard>
        )}
      </ScrollView>
    </AppScreen>
  );
}

function SegmentedControl(props: {
  label: string;
  value: string;
  options: Array<[string, string]>;
  onChange: (value: string) => void;
}) {
  return (
    <View style={{ gap: 8 }}>
      <Text style={{ color: "#f5edff", fontWeight: "700" }}>{props.label}</Text>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
        {props.options.map(([value, label]) => (
          <TouchableOpacity
            key={value}
            onPress={() => props.onChange(value)}
            style={{
              backgroundColor: props.value === value ? "#8b5cf6" : "#241233",
              borderColor: "#6d35b8",
              borderWidth: 1,
              borderRadius: 12,
              paddingHorizontal: 10,
              paddingVertical: 8,
              minHeight: 48,
              justifyContent: "center",
            }}
          >
            <Text style={{ color: "white", fontWeight: "700" }}>{label}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

function SizeToggle(props: {
  sizes: SizeMeasurement[];
  activeSizeLabel: string;
  bestSizeLabel?: string | null;
  onSelect: (label: string) => void;
}) {
  if (props.sizes.length === 0) return null;

  return (
    <View style={{ gap: 8 }}>
      <Text style={{ color: "#f5edff", fontWeight: "700" }}>Tamanhos</Text>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
        {props.sizes.map((size) => {
          const active = props.activeSizeLabel === size.size_label;
          const best = props.bestSizeLabel === size.size_label;
          return (
            <TouchableOpacity
              key={size.size_label}
              onPress={() => props.onSelect(size.size_label)}
              style={{
                backgroundColor: active ? "#8b5cf6" : "#241233",
                borderColor: best ? "#facc15" : "#6d35b8",
                borderWidth: best ? 2 : 1,
                borderRadius: 12,
                paddingHorizontal: 10,
                paddingVertical: 8,
                minHeight: 48,
                justifyContent: "center",
              }}
            >
              <Text style={{ color: "white", fontWeight: "800" }}>
                {size.size_label}{best ? "  Ideal" : ""}{size.is_estimated ? "  est." : ""}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
}

function optionalNumber(value: string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function extrapolateManualSizes(base: SizeMeasurement): SizeMeasurement[] {
  const labels = ["P", "M", "G", "GG"];
  const anchorIndex = Math.max(0, labels.indexOf(base.size_label.toUpperCase()));
  const resolvedAnchor = anchorIndex >= 0 ? anchorIndex : 1;

  return labels.map((label, index) => {
    const offset = index - resolvedAnchor;
    return {
      ...base,
      size_label: label,
      chest_cm: addStep(base.chest_cm, offset, 4),
      waist_cm: addStep(base.waist_cm, offset, 4),
      hip_cm: addStep(base.hip_cm, offset, 4),
      biceps_cm: addStep(base.biceps_cm, offset, 2),
      thigh_cm: addStep(base.thigh_cm, offset, 3),
      shoulder_cm: addStep(base.shoulder_cm, offset, 1.2),
      sleeve_cm: addStep(base.sleeve_cm, offset, 1),
      length_cm: addStep(base.length_cm, offset, 1),
      inseam_cm: addStep(base.inseam_cm, offset, 1),
      is_estimated: label !== base.size_label.toUpperCase(),
      estimated_from_size: base.size_label,
    };
  });
}

function addStep(value: number | null | undefined, offset: number, step: number) {
  return value == null ? null : Math.round((value + offset * step) * 10) / 10;
}

function resultForSize(result: FitCheckResult | null, sizeLabel: string): FitCheckResult | null {
  if (!result) return null;
  const option = result.size_options?.find((item) => item.size_label === sizeLabel);
  if (!option) return result;

  return {
    ...result,
    zones: option.zones,
    summary: option.summary,
    selected_size_label: option.size_label,
  };
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

      <LegendItem color="#ef4444" label="Pouca folga: pode ficar mais ajustado" />
      <LegendItem color="#f59e0b" label="Caimento próximo ao corpo" />
      <LegendItem color="#22c55e" label="Folga confortável" />
      <LegendItem color="#38bdf8" label="Caimento solto" />
      <LegendItem color="#9ca3af" label="Medida não informada pela loja" />
      <Text style={{ color: "#d8c7ff", fontSize: 12, lineHeight: 18 }}>
        Padrões no manequim: hachuras indicam pouca folga; traços indicam folga; pontos indicam medida não informada.
      </Text>
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
