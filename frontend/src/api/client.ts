import Constants from "expo-constants";
import {
  API_REQUEST_TIMEOUT_MS,
  DEFAULT_API_BASE_URL,
  VTON_TASK_TIMEOUT_MS,
} from "../config/api";
import {
  BodyRecommendationResponse,
  FineTuneInput,
  InitialBodyInput,
  MannequinParams,
} from "../types/body";
import {
  ProductScrapeResult,
  GarmentUploadResult,
  FitCheckInput,
  FitCheckResult,
} from "../types/product";
import {
  VtonPrepareInput,
  VtonPayload,
  VtonMockInput,
  VtonMockResult,
  VtonRunInput,
  VtonRunResult,
  VtonTaskCreated,
  VtonTaskStatusResponse,
} from "../types/vton";
import {
  MannequinRenderInput,
  MannequinRenderResult,
} from "../types/mannequin";

function normalizeBaseUrl(value: unknown): string | null {
  if (typeof value !== "string") return null;

  const trimmed = value.trim();
  if (!trimmed) return null;

  return trimmed.replace(/\/+$/, "");
}

export const API_BASE_URL =
  normalizeBaseUrl(Constants?.expoConfig?.extra?.apiUrl) ??
  normalizeBaseUrl(Constants?.manifest?.extra?.apiUrl) ??
  DEFAULT_API_BASE_URL;

async function fetchWithTimeout(
  input: string,
  options: RequestInit,
  timeoutMs = API_REQUEST_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(input, {
      ...options,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error("Tempo de conexao esgotado. Verifique sua internet.");
    }

    if (
      error instanceof TypeError &&
      /network request failed|failed to fetch|networkerror/i.test(error.message)
    ) {
      throw new Error(
        `Falha de rede ao conectar a API em ${API_BASE_URL}. ` +
          "Verifique sua conexao ou aguarde o servidor em nuvem iniciar e tente novamente."
      );
    }

    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export function resolveApiUrl(path?: string | null): string | null {
  if (!path) return null;

  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }

  return `${API_BASE_URL}${path}`;
}

async function request<T>(path: string, options: RequestInit): Promise<T> {
  const response = await fetchWithTimeout(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Erro na API");
  }

  return response.json() as Promise<T>;
}

export async function recommendBodyModels(
  data: InitialBodyInput
): Promise<BodyRecommendationResponse> {
  return request<BodyRecommendationResponse>("/body/recommend", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function generateMannequin(
  data: FineTuneInput
): Promise<MannequinParams> {
  return request<MannequinParams>("/body/mannequin", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function renderMannequinFront(
  data: MannequinRenderInput
): Promise<MannequinRenderResult> {
  return request<MannequinRenderResult>("/mannequin/render-front", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function scrapeProduct(
  url: string
): Promise<ProductScrapeResult> {
  return request<ProductScrapeResult>("/product/scrape", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export async function uploadGarmentImage(
  file: {
    uri: string;
    name: string;
    type: string;
  }
): Promise<GarmentUploadResult> {
  const formData = new FormData();

  formData.append("file", {
    uri: file.uri,
    name: file.name,
    type: file.type,
  } as unknown as Blob);

  const response = await fetchWithTimeout(`${API_BASE_URL}/garment/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Erro ao enviar imagem");
  }

  return response.json() as Promise<GarmentUploadResult>;
}

export async function checkFit(
  data: FitCheckInput
): Promise<FitCheckResult> {
  return request<FitCheckResult>("/fit/check", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function prepareVton(
  data: VtonPrepareInput
): Promise<VtonPayload> {
  return request<VtonPayload>("/vton/prepare", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function createMockVton(
  data: VtonMockInput
): Promise<VtonMockResult> {
  return request<VtonMockResult>("/vton/mock", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function runVton(
  data: VtonRunInput
): Promise<VtonRunResult> {
  return request<VtonRunResult>("/vton/run", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function createVtonTask(
  data: VtonRunInput
): Promise<VtonTaskCreated> {
  return request<VtonTaskCreated>("/vton/tasks", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getVtonTask(
  taskId: string
): Promise<VtonTaskStatusResponse> {
  return request<VtonTaskStatusResponse>(`/vton/tasks/${taskId}`, {
    method: "GET",
  });
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function runVtonTaskWithPolling(
  data: VtonRunInput,
  onStatus?: (status: VtonTaskStatusResponse | VtonTaskCreated) => void,
  timeoutMs = VTON_TASK_TIMEOUT_MS
): Promise<VtonRunResult> {
  const startedAt = Date.now();
  const created = await createVtonTask(data);
  let pollAfterSeconds = Math.max(1, created.poll_after_seconds ?? 2);
  onStatus?.(created);

  while (Date.now() - startedAt < timeoutMs) {
    await sleep(pollAfterSeconds * 1000);

    const status = await getVtonTask(created.task_id);
    pollAfterSeconds = Math.max(1, status.poll_after_seconds ?? pollAfterSeconds);
    onStatus?.(status);

    if (status.state === "succeeded") {
      if (!status.result) {
        throw new Error("Tarefa VTON finalizada sem resultado.");
      }

      return status.result;
    }

    if (status.state === "failed") {
      throw new Error(status.error ?? "Tarefa VTON falhou sem detalhe.");
    }
  }

  throw new Error("Tempo limite da tarefa VTON esgotado. Tente novamente em instantes.");
}
