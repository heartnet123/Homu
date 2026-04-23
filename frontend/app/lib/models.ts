export const API_BASE_URL = "http://localhost:8000/api/v1";

export type ModelOption = {
  id: string;
  name: string;
  company: string;
  color: string;
  bgColor: string;
  textColor: string;
  borderColor: string;
};

type BackendCapabilities = {
  models?: string[];
  default_model?: string;
};

const MODEL_METADATA: Record<string, Omit<ModelOption, "id">> = {
  "gpt-5.4": {
    name: "GPT-5.4",
    company: "OpenAI",
    color: "bg-emerald-600",
    bgColor: "bg-emerald-50",
    textColor: "text-emerald-800",
    borderColor: "border-emerald-200",
  },
  "gpt-5.4-mini": {
    name: "GPT-5.4 Mini",
    company: "OpenAI",
    color: "bg-emerald-400",
    bgColor: "bg-emerald-50",
    textColor: "text-emerald-600",
    borderColor: "border-emerald-100",
  },
  "gpt-4o": {
    name: "GPT-4o",
    company: "OpenAI",
    color: "bg-emerald-500",
    bgColor: "bg-emerald-50",
    textColor: "text-emerald-700",
    borderColor: "border-emerald-100",
  },
};

export function getModelOption(id: string): ModelOption {
  const model = MODEL_METADATA[id];
  if (model) {
    return { id, ...model };
  }

  return {
    id,
    name: id,
    company: "Backend configured",
    color: "bg-slate-500",
    bgColor: "bg-slate-50",
    textColor: "text-slate-700",
    borderColor: "border-slate-200",
  };
}

export function getSupportedModelOptions(ids: string[]): ModelOption[] {
  return ids.map(getModelOption);
}

export async function fetchBackendCapabilities(): Promise<BackendCapabilities> {
  const response = await fetch(`${API_BASE_URL}/capabilities`);
  if (!response.ok) {
    throw new Error("Failed to load backend capabilities.");
  }

  return response.json();
}
