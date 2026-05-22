import { FitCheckResult, FitZone } from "../types/product";

export function fitZoneLabel(zone: string): string {
  switch (zone) {
    case "chest":
      return "Busto/tórax";
    case "waist":
      return "Cintura";
    case "hip":
      return "Quadril";
    case "length":
      return "Comprimento";
    case "sleeve":
      return "Manga";
    case "biceps":
      return "Bíceps";
    case "top_length":
      return "Comprimento superior";
    case "inseam":
      return "Entrepernas";
    case "thigh":
      return "Coxa";
    case "shoulder":
      return "Ombros";
    default:
      return zone;
  }
}

export function buildFitInsight(zone: FitZone): string {
  const label = fitZoneLabel(zone.zone).toLowerCase();

  if (zone.color === "gray" || zone.status === "sem_informacao" || zone.status === "unknown") {
    return `A loja não informou a medida de ${label}. O resultado pode ficar menos preciso nessa região.`;
  }

  if (zone.color === "red" || zone.status === "apertado" || zone.status === "too_small" || zone.status === "tight") {
    return `Essa peça pode ficar com pouca folga em ${label}. Se você prefere conforto, teste um tamanho acima.`;
  }

  if (zone.color === "yellow" || zone.status === "justo" || zone.status === "balanced") {
    return `A região de ${label} parece próxima ao corpo, com caimento mais ajustado.`;
  }

  if (zone.color === "green") {
    return `A região de ${label} deve ter folga confortável, boa para movimento.`;
  }

  if (zone.color === "blue" || zone.status === "folgado" || zone.status === "loose") {
    return `A região de ${label} tende a ficar mais solta, com sensação casual ou oversized.`;
  }

  return zone.message || `Caimento estimado para ${label}.`;
}

export function buildFitSummaryForUser(zones: FitZone[]): string {
  if (zones.length === 0) {
    return "Ainda não avaliamos o caimento desta peça.";
  }

  const hasLowEase = zones.some((zone) =>
    zone.color === "red" || zone.status === "apertado" || zone.status === "too_small" || zone.status === "tight"
  );
  const hasCloseFit = zones.some((zone) =>
    zone.color === "yellow" || zone.status === "justo" || zone.status === "balanced"
  );
  const hasUnknown = zones.some((zone) =>
    zone.color === "gray" || zone.status === "sem_informacao" || zone.status === "unknown"
  );
  const hasRelaxed = zones.some((zone) =>
    zone.color === "green" || zone.color === "blue" || zone.status === "folgado" || zone.status === "loose"
  );

  if (hasLowEase) {
    return "Algumas regiões podem ter pouca folga. Vale conferir tecido, elasticidade e sua preferência de caimento.";
  }
  if (hasCloseFit) {
    return "A peça tende a ficar próxima ao corpo em algumas regiões, com aparência mais ajustada.";
  }
  if (hasRelaxed) {
    return "A peça tende a ter folga confortável na maior parte do look.";
  }
  if (hasUnknown) {
    return "A loja não informou todas as medidas, então parte do caimento é estimada.";
  }
  return "Caimento estimado com as medidas disponíveis.";
}

export function buildSizeRecommendationText(result: FitCheckResult | null): string {
  if (!result) return "Veja o caimento para receber uma sugestão de tamanho.";

  if (result.best_size_label) {
    return `Melhor opção estimada: ${result.best_size_label}. Use como ponto de partida e considere sua preferência de caimento.`;
  }

  if (result.selected_size_label) {
    return `Tamanho analisado: ${result.selected_size_label}.`;
  }

  return "Tamanho analisado com as informações disponíveis.";
}

export function fitColorToHex(color: string): string {
  switch (color) {
    case "red":
      return "#ef4444";
    case "yellow":
      return "#f59e0b";
    case "green":
      return "#22c55e";
    case "blue":
      return "#38bdf8";
    case "gray":
      return "#9ca3af";
    default:
      return "#8b5cf6";
  }
}
