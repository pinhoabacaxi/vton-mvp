import React from "react";
import { View, Text, Image, StyleSheet } from "react-native";

type Props = {
  resultImageUrl?: string | null;
  title?: string;
  sourceName?: string | null;
  productTitle?: string | null;
  fitSummary?: string | null;
};

export function SocialLookCard({
  resultImageUrl,
  title,
  sourceName,
  productTitle,
  fitSummary,
}: Props) {
  return (
    <View style={styles.card}>
      <Text style={styles.title}>{title ?? "Meu look virtual"}</Text>

      {resultImageUrl ? (
        <Image source={{ uri: resultImageUrl }} style={styles.image} resizeMode="cover" />
      ) : (
        <View style={styles.placeholder}>
          <Text style={styles.placeholderText}>Imagem não disponível</Text>
        </View>
      )}

      <View style={styles.metaContainer}>
        {productTitle ? (
          <Text style={styles.metaLine} numberOfLines={2}>
            <Text style={styles.metaLabel}>Produto: </Text>
            {productTitle}
          </Text>
        ) : null}

        {sourceName ? (
          <Text style={styles.metaLine} numberOfLines={1}>
            <Text style={styles.metaLabel}>Loja: </Text>
            {sourceName}
          </Text>
        ) : null}

        {fitSummary ? (
          <Text style={styles.metaLine} numberOfLines={3}>
            <Text style={styles.metaLabel}>Caimento: </Text>
            {fitSummary}
          </Text>
        ) : null}
      </View>

      <View style={styles.footer}>
        <Text style={styles.footerText}>Prévia visual estimada</Text>
        <Text style={styles.ctaText}>Meu provador virtual</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    width: "100%",
    maxWidth: 380,
    borderRadius: 28,
    padding: 18,
    backgroundColor: "#150b26",
    shadowColor: "#000",
    shadowOpacity: 0.15,
    shadowRadius: 18,
    elevation: 4,
  },
  title: {
    color: "#f8f3ff",
    fontSize: 22,
    fontWeight: "800",
    marginBottom: 12,
  },
  image: {
    width: "100%",
    height: 320,
    borderRadius: 20,
    backgroundColor: "#1c1131",
  },
  placeholder: {
    width: "100%",
    height: 320,
    borderRadius: 20,
    backgroundColor: "#241336",
    alignItems: "center",
    justifyContent: "center",
  },
  placeholderText: {
    color: "#b9a2ff",
    fontSize: 16,
    textAlign: "center",
  },
  metaContainer: {
    marginTop: 14,
    padding: 12,
    borderRadius: 18,
    backgroundColor: "#1e1333",
    gap: 8,
  },
  metaLine: {
    color: "#d8c7ff",
    fontSize: 14,
    lineHeight: 20,
  },
  metaLabel: {
    color: "#f8f3ff",
    fontWeight: "700",
  },
  footer: {
    marginTop: 16,
    borderTopWidth: 1,
    borderTopColor: "#3f2b61",
    paddingTop: 14,
  },
  footerText: {
    color: "#c4b5fd",
    fontSize: 12,
    marginBottom: 6,
  },
  ctaText: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "800",
  },
});
