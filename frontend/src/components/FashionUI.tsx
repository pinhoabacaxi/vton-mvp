import React, { useState } from "react";
import {
  ActivityIndicator,
  KeyboardTypeOptions,
  SafeAreaView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  ViewStyle,
} from "react-native";

export const fashionColors = {
  background: "#12071f",
  surface: "#21102f",
  surfaceSoft: "#2d1640",
  surfaceDeep: "#170b25",
  input: "#241233",
  border: "#4c2a69",
  borderStrong: "#7c3aed",
  primary: "#8b5cf6",
  primaryDark: "#6d28d9",
  secondary: "#3b1c5c",
  text: "#ffffff",
  textSoft: "#d8c7ff",
  textMuted: "#bca7df",
  gold: "#facc15",
  dangerSurface: "#3b0a1f",
  dangerText: "#fecdd3",
  success: "#16a34a",
  warning: "#f59e0b",
  info: "#38bdf8",
};

export const fashionSpacing = {
  xs: 6,
  sm: 10,
  md: 14,
  lg: 18,
  xl: 24,
};

export const fashionRadius = {
  sm: 12,
  md: 16,
  lg: 18,
  xl: 24,
  pill: 999,
};

export const fashionTypography = {
  title: { fontSize: 30, lineHeight: 36, fontWeight: "900" as const },
  section: { fontSize: 18, lineHeight: 24, fontWeight: "900" as const },
  body: { fontSize: 15, lineHeight: 22 },
  caption: { fontSize: 12, lineHeight: 18 },
};

export const fashionShadows = {
  soft: {
    shadowColor: "#000000",
    shadowOpacity: 0.2,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 8 },
    elevation: 4,
  },
};

export const guidedJourneySteps = [
  { key: "profile", label: "Perfil" },
  { key: "silhouette", label: "Silhueta" },
  { key: "refine", label: "Medidas" },
  { key: "piece", label: "Peça" },
  { key: "look", label: "Look" },
] as const;

type GuidedJourneyStepKey = (typeof guidedJourneySteps)[number]["key"];

export function AppScreen(props: {
  children: React.ReactNode;
  padded?: boolean;
  style?: ViewStyle;
}) {
  return (
    <SafeAreaView
      style={[
        { flex: 1, backgroundColor: fashionColors.background },
        props.padded === false ? null : { padding: 0 },
        props.style,
      ]}
    >
      {props.children}
    </SafeAreaView>
  );
}

export function StepHeader(props: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  step?: string;
}) {
  return (
    <View style={{ gap: fashionSpacing.sm }}>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        {props.eyebrow ? (
          <Text style={{ color: fashionColors.gold, fontSize: 12, fontWeight: "800", letterSpacing: 0 }}>
            {props.eyebrow.toUpperCase()}
          </Text>
        ) : null}

        {props.step ? (
          <View
            style={{
              backgroundColor: fashionColors.surfaceSoft,
              borderColor: fashionColors.border,
              borderWidth: 1,
              borderRadius: fashionRadius.pill,
              paddingHorizontal: 10,
              paddingVertical: 5,
            }}
          >
            <Text style={{ color: fashionColors.textSoft, fontSize: 12, fontWeight: "800" }}>
              {props.step}
            </Text>
          </View>
        ) : null}
      </View>

      <Text style={{ color: fashionColors.text, ...fashionTypography.title }}>
        {props.title}
      </Text>

      {props.subtitle ? (
        <Text style={{ color: fashionColors.textSoft, ...fashionTypography.body }}>
          {props.subtitle}
        </Text>
      ) : null}
    </View>
  );
}

export function JourneyStepper(props: {
  activeStep: GuidedJourneyStepKey;
}) {
  const activeIndex = guidedJourneySteps.findIndex((step) => step.key === props.activeStep);

  return (
    <View style={{ gap: fashionSpacing.sm }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
        {guidedJourneySteps.map((step, index) => {
          const isActive = step.key === props.activeStep;
          const isDone = activeIndex >= 0 && index < activeIndex;

          return (
            <View
              key={step.key}
              style={{
                flex: 1,
                height: 6,
                borderRadius: 999,
                backgroundColor: isActive || isDone ? fashionColors.primary : fashionColors.surfaceSoft,
                borderWidth: 1,
                borderColor: isActive ? "#c4b5fd" : fashionColors.border,
              }}
            />
          );
        })}
      </View>

      <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 6 }}>
        {guidedJourneySteps.map((step) => {
          const isActive = step.key === props.activeStep;

          return (
            <Text
              key={step.key}
              numberOfLines={1}
              style={{
                flex: 1,
                color: isActive ? fashionColors.text : fashionColors.textMuted,
                fontSize: 10,
                fontWeight: isActive ? "900" : "700",
                textAlign: "center",
              }}
            >
              {step.label}
            </Text>
          );
        })}
      </View>
    </View>
  );
}

export function FashionCard(props: {
  children: React.ReactNode;
  style?: ViewStyle;
  highlighted?: boolean;
}) {
  return (
    <View
      style={[
        {
          backgroundColor: props.highlighted ? "#2f1550" : fashionColors.surface,
          borderRadius: fashionRadius.lg,
          padding: fashionSpacing.md,
          borderWidth: 1,
          borderColor: props.highlighted ? "#a78bfa" : fashionColors.border,
          gap: fashionSpacing.sm,
          ...fashionShadows.soft,
        },
        props.style,
      ]}
    >
      {props.children}
    </View>
  );
}

export function PrimaryButton(props: {
  label: string;
  onPress: () => void;
  loading?: boolean;
  disabled?: boolean;
  tone?: "primary" | "secondary" | "success" | "danger";
}) {
  const disabled = props.disabled || props.loading;
  const color =
    props.tone === "secondary"
      ? fashionColors.secondary
      : props.tone === "success"
        ? "#16a34a"
        : props.tone === "danger"
          ? "#7f1d1d"
          : fashionColors.primary;

  return (
    <TouchableOpacity
      onPress={props.onPress}
      disabled={disabled}
      style={{
        backgroundColor: disabled ? "#5b3d87" : color,
        padding: 16,
        borderRadius: fashionRadius.lg,
        alignItems: "center",
        justifyContent: "center",
        minHeight: 52,
      }}
    >
      {props.loading ? (
        <ActivityIndicator color="white" />
      ) : (
        <Text style={{ color: "white", fontWeight: "900", fontSize: 15, textAlign: "center" }}>
          {props.label}
        </Text>
      )}
    </TouchableOpacity>
  );
}

export function SecondaryButton(props: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  return (
    <TouchableOpacity
      onPress={props.onPress}
      disabled={props.disabled}
      style={{
        backgroundColor: fashionColors.input,
        borderColor: fashionColors.border,
        borderWidth: 1,
        padding: 14,
        borderRadius: fashionRadius.md,
        alignItems: "center",
        justifyContent: "center",
        minHeight: 50,
        opacity: props.disabled ? 0.56 : 1,
      }}
    >
      <Text style={{ color: fashionColors.text, fontWeight: "800", textAlign: "center" }}>
        {props.label}
      </Text>
    </TouchableOpacity>
  );
}

export function MeasurementInput(props: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  hint?: string;
  placeholder?: string;
  keyboardType?: KeyboardTypeOptions;
  estimatedValue?: number;
}) {
  const isEstimated = !props.value && props.estimatedValue != null;

  return (
    <View style={{ gap: 7, opacity: isEstimated ? 0.78 : 1 }}>
      <Text style={{ color: "#f5edff", fontWeight: "800" }}>{props.label}</Text>

      {props.hint ? (
        <Text style={{ color: fashionColors.textMuted, fontSize: 12, lineHeight: 18 }}>
          {props.hint}
        </Text>
      ) : null}

      {isEstimated ? (
        <Text style={{ color: fashionColors.gold, fontSize: 12, fontWeight: "800" }}>
          Estimativa inicial: {props.estimatedValue} cm. Você pode ajustar quando quiser.
        </Text>
      ) : null}

      <TextInput
        value={props.value}
        onChangeText={props.onChangeText}
        keyboardType={props.keyboardType ?? "numeric"}
        placeholder={props.placeholder ?? (props.estimatedValue != null ? String(props.estimatedValue) : undefined)}
        placeholderTextColor="#9b86b8"
        style={{
          backgroundColor: fashionColors.input,
          color: fashionColors.text,
          padding: 14,
          borderRadius: fashionRadius.md,
          borderWidth: 1,
          borderColor: fashionColors.borderStrong,
          minHeight: 52,
        }}
      />
    </View>
  );
}

export function FriendlyError(props: { title?: string; message: string }) {
  return (
    <View
      style={{
        backgroundColor: fashionColors.dangerSurface,
        borderRadius: fashionRadius.md,
        padding: 14,
        borderWidth: 1,
        borderColor: "#be123c",
        gap: 6,
      }}
    >
      <Text style={{ color: "#fff1f2", fontWeight: "900" }}>
        {props.title ?? "Algo não saiu como esperado"}
      </Text>
      <Text style={{ color: fashionColors.dangerText, lineHeight: 20 }}>
        {props.message}
      </Text>
    </View>
  );
}

export function LoadingState(props: { title: string; message?: string }) {
  return (
    <FashionCard>
      <ActivityIndicator color={fashionColors.text} />
      <Text style={{ color: fashionColors.text, fontWeight: "900", fontSize: 16, textAlign: "center" }}>
        {props.title}
      </Text>
      {props.message ? (
        <Text style={{ color: fashionColors.textSoft, textAlign: "center", lineHeight: 20 }}>
          {props.message}
        </Text>
      ) : null}
    </FashionCard>
  );
}

export function InfoPill(props: { label: string; tone?: "gold" | "purple" | "neutral" }) {
  const background =
    props.tone === "gold" ? "#facc15" : props.tone === "neutral" ? "#374151" : "#3b1c5c";
  const color = props.tone === "gold" ? "#2d1640" : "#f8f3ff";

  return (
    <View
      style={{
        backgroundColor: background,
        borderRadius: fashionRadius.pill,
        paddingHorizontal: 12,
        paddingVertical: 7,
        alignSelf: "flex-start",
      }}
    >
      <Text style={{ color, fontWeight: "900", fontSize: 12 }}>
        {props.label}
      </Text>
    </View>
  );
}

export function PremiumEmptyState(props: {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  secondaryActionLabel?: string;
  onSecondaryAction?: () => void;
  variant?: "closet" | "history" | "linkError" | "generic";
}) {
  const symbol =
    props.variant === "closet"
      ? "◇"
      : props.variant === "history"
        ? "◎"
        : props.variant === "linkError"
          ? "!"
          : "✦";

  return (
    <FashionCard highlighted style={{ alignItems: "center", paddingVertical: 22 }}>
      <View
        style={{
          width: 54,
          height: 54,
          borderRadius: 27,
          backgroundColor: fashionColors.surfaceSoft,
          borderWidth: 1,
          borderColor: "#a78bfa",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Text style={{ color: fashionColors.gold, fontSize: 24, fontWeight: "900" }}>
          {symbol}
        </Text>
      </View>
      <Text style={{ color: fashionColors.text, ...fashionTypography.section, textAlign: "center" }}>
        {props.title}
      </Text>
      <Text style={{ color: fashionColors.textSoft, ...fashionTypography.body, textAlign: "center" }}>
        {props.description}
      </Text>
      {props.actionLabel && props.onAction ? (
        <PrimaryButton label={props.actionLabel} onPress={props.onAction} />
      ) : null}
      {props.secondaryActionLabel && props.onSecondaryAction ? (
        <SecondaryButton label={props.secondaryActionLabel} onPress={props.onSecondaryAction} />
      ) : null}
    </FashionCard>
  );
}

export function MeasurementGuideAccordion(props: {
  title: string;
  description: string;
  initiallyExpanded?: boolean;
  illustrationKey?: string;
}) {
  const [expanded, setExpanded] = useState(Boolean(props.initiallyExpanded));

  return (
    <View
      style={{
        backgroundColor: fashionColors.surfaceSoft,
        borderColor: fashionColors.border,
        borderWidth: 1,
        borderRadius: fashionRadius.md,
        overflow: "hidden",
      }}
    >
      <TouchableOpacity
        onPress={() => setExpanded((value) => !value)}
        style={{
          minHeight: 48,
          paddingHorizontal: fashionSpacing.md,
          paddingVertical: fashionSpacing.sm,
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-between",
          gap: fashionSpacing.sm,
        }}
      >
        <View style={{ flex: 1 }}>
          <Text style={{ color: fashionColors.text, fontWeight: "900" }}>{props.title}</Text>
          {props.illustrationKey ? (
            <Text style={{ color: fashionColors.textMuted, ...fashionTypography.caption }}>
              Guia visual preparado: {props.illustrationKey}
            </Text>
          ) : null}
        </View>
        <Text style={{ color: fashionColors.gold, fontWeight: "900" }}>
          {expanded ? "Fechar" : "Como medir"}
        </Text>
      </TouchableOpacity>

      {expanded ? (
        <View style={{ paddingHorizontal: fashionSpacing.md, paddingBottom: fashionSpacing.md }}>
          <Text style={{ color: fashionColors.textSoft, ...fashionTypography.body }}>
            {props.description}
          </Text>
        </View>
      ) : null}
    </View>
  );
}

export function DebugPanel(props: {
  title?: string;
  children: React.ReactNode;
  enabled?: boolean;
}) {
  if (!__DEV__ && !props.enabled) return null;

  return (
    <FashionCard>
      <Text style={{ color: fashionColors.gold, fontWeight: "900" }}>
        {props.title ?? "Debug"}
      </Text>
      {props.children}
    </FashionCard>
  );
}
