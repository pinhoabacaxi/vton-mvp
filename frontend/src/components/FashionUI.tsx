import React from "react";
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
};

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
    <View style={{ gap: 8 }}>
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
              borderRadius: 999,
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

      <Text style={{ color: fashionColors.text, fontSize: 30, fontWeight: "900", lineHeight: 36 }}>
        {props.title}
      </Text>

      {props.subtitle ? (
        <Text style={{ color: fashionColors.textSoft, fontSize: 15, lineHeight: 22 }}>
          {props.subtitle}
        </Text>
      ) : null}
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
          borderRadius: 18,
          padding: 14,
          borderWidth: 1,
          borderColor: props.highlighted ? "#a78bfa" : fashionColors.border,
          gap: 10,
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
        borderRadius: 18,
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
        backgroundColor: "#241233",
        borderColor: fashionColors.border,
        borderWidth: 1,
        padding: 14,
        borderRadius: 16,
        alignItems: "center",
        justifyContent: "center",
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
          backgroundColor: "#241233",
          color: fashionColors.text,
          padding: 14,
          borderRadius: 14,
          borderWidth: 1,
          borderColor: fashionColors.borderStrong,
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
        borderRadius: 16,
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
        borderRadius: 999,
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
