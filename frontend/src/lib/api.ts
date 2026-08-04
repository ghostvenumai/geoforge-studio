import type {
  ApiErrorEnvelope,
  Artifact,
  BenchmarkResults,
  DataProfile,
  Dataset,
  DuplicateGroup,
  Health,
  ListResponse,
  OverviewData,
  Pipeline,
  Run,
  RunMetrics,
  SystemInfo,
} from '../types'

const configuredApiUrl: unknown = import.meta.env.VITE_API_URL
const API_BASE = typeof configuredApiUrl === 'string' ? configuredApiUrl : '/api'

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly requestId?: string,
  ) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { Accept: 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    let payload: ApiErrorEnvelope | undefined
    try {
      payload = (await response.json()) as ApiErrorEnvelope
    } catch {
      payload = undefined
    }
    throw new ApiError(payload?.error?.message ?? response.statusText, response.status, payload?.error?.request_id)
  }
  return (await response.json()) as T
}

export function uploadDataset(
  file: File,
  onProgress: (percentage: number) => void,
  signal?: AbortSignal,
): Promise<Dataset> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE}/datasets/upload`)
    xhr.setRequestHeader('Accept', 'application/json')
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100))
    })
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as Dataset)
      } else {
        try {
          const payload = JSON.parse(xhr.responseText) as ApiErrorEnvelope
          reject(new ApiError(payload.error.message, xhr.status, payload.error.request_id))
        } catch {
          reject(new ApiError('Upload fehlgeschlagen', xhr.status))
        }
      }
    })
    xhr.addEventListener('error', () => reject(new ApiError('Netzwerkfehler beim Upload', 0)))
    xhr.addEventListener('abort', () => reject(new ApiError('Upload abgebrochen', 0)))
    signal?.addEventListener('abort', () => xhr.abort(), { once: true })
    const body = new FormData()
    body.append('file', file)
    xhr.send(body)
  })
}

export const api = {
  overview: () => request<OverviewData>('/overview'),
  benchmarks: () => request<BenchmarkResults>('/benchmarks'),
  health: () => request<Health>('/health'),
  systemInfo: () => request<SystemInfo>('/system/info'),
  datasets: () => request<ListResponse<Dataset>>('/datasets'),
  dataset: (id: string) => request<Dataset>(`/datasets/${id}`),
  deleteDataset: (id: string) => request<{ message: string }>(`/datasets/${id}`, { method: 'DELETE' }),
  profileDataset: (id: string) =>
    request<{ dataset_id: string; profile: DataProfile }>(`/datasets/${id}/profile`, { method: 'POST' }),
  profile: (id: string) => request<{ dataset_id: string; profile: DataProfile }>(`/datasets/${id}/profile`),
  pipelines: () => request<ListResponse<Pipeline>>('/pipelines'),
  pipeline: (id: string) => request<Pipeline>(`/pipelines/${id}`),
  validatePipeline: (yamlText: string) =>
    request<{ valid: boolean; checksum: string; definition: Pipeline['definition_json']; warnings: string[] }>(
      '/pipelines/validate',
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ yaml_text: yamlText }) },
    ),
  createPipeline: (yamlText: string) =>
    request<Pipeline>('/pipelines', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ yaml_text: yamlText }),
    }),
  runs: () => request<ListResponse<Run>>('/runs'),
  run: (id: string) => request<Run>(`/runs/${id}`),
  startRun: (pipelineId: string, datasetId: string) =>
    request<Run>(`/pipelines/${pipelineId}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_id: datasetId }),
    }),
  cancelRun: (runId: string) => request<{ message: string }>(`/runs/${runId}/cancel`, { method: 'POST' }),
  metrics: (runId: string) => request<{ metrics: RunMetrics }>(`/runs/${runId}/metrics`),
  artifacts: (runId: string) => request<ListResponse<Artifact>>(`/runs/${runId}/artifacts`),
  duplicates: (runId: string) => request<ListResponse<DuplicateGroup>>(`/runs/${runId}/duplicates`),
  decideDuplicate: (runId: string, groupId: string, decision: 'accepted' | 'rejected', canonicalId?: string) =>
    request<{ message: string }>(`/runs/${runId}/duplicates/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ duplicate_group_id: groupId, decision, canonical_record_id: canonicalId }),
    }),
  artifactUrl: (id: string) => `${API_BASE}/artifacts/${id}/download`,
}
