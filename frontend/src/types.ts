export interface ListResponse<T> {
  items: T[]
  total: number
}

export interface ApiErrorEnvelope {
  error: { code: string; message: string; details?: unknown; request_id?: string }
}

export interface Dataset {
  id: string
  name: string
  original_filename: string
  format: string
  checksum: string
  size_bytes: number
  row_count: number
  column_count: number
  schema: Record<string, string>
  preview_json: Array<Record<string, unknown>>
  encoding: string | null
  delimiter: string | null
  status: string
  duplicate_of_dataset_id: string | null
  created_at: string
}

export interface ColumnProfile {
  name: string
  dtype: string
  null_count: number
  null_ratio: number
  unique_count: number
  unique_ratio: number
  cardinality: number
  invalid_count: number
  sample_values: unknown[]
  top_values: Array<{ value: unknown; count: number }>
  statistics: Record<string, unknown>
  recommendation: string
}

export interface DataProfile {
  row_count: number
  sampled_rows: number
  column_count: number
  memory_bytes: number
  exact_duplicate_count: number
  total_null_count: number
  total_invalid_count: number
  quality_score: number
  sampled: boolean
  columns: ColumnProfile[]
  warnings: string[]
}

export interface PipelineStep {
  id: string
  type: string
  name: string
  enabled: boolean
  config: Record<string, unknown>
  position?: { x: number; y: number }
}

export interface Pipeline {
  id: string
  name: string
  description: string
  version: number
  yaml_text: string
  definition_json: {
    name: string
    description: string
    version: number
    steps: PipelineStep[]
    edges: Array<{ id: string; source: string; target: string }>
  }
  checksum: string
  created_at: string
  updated_at: string
}

export interface StepMetric {
  step_id: string
  step_type: string
  name: string
  duration_seconds: number
  input_rows: number
  output_rows: number
  changed_rows: number
  quarantined_rows: number
  warnings: string[]
  error: string | null
}

export interface RunMetrics {
  total_runtime_seconds?: number
  rows_per_second?: number
  peak_memory_bytes?: number
  average_cpu_percent?: number
  input_size_bytes?: number
  output_size_bytes?: number
  compression_ratio?: number
  processed_rows?: number
  errors?: number
  warnings?: number
  steps?: StepMetric[]
  result_preview?: Array<Record<string, unknown>>
  quarantine_preview?: Array<Record<string, unknown>>
}

export interface Run {
  id: string
  dataset_id: string
  pipeline_id: string
  status: string
  started_at: string | null
  finished_at: string | null
  input_rows: number
  output_rows: number
  quarantine_rows: number
  duplicate_count: number
  quality_before: number | null
  quality_after: number | null
  error_count: number
  warning_count: number
  cancel_requested: boolean
  metrics_json: RunMetrics
  error_message: string | null
  created_at: string
}

export interface Artifact {
  id: string
  run_id: string
  kind: string
  name: string
  checksum: string
  size_bytes: number
  media_type: string
  created_at: string
}

export interface DuplicateGroup {
  group_id: string
  review_required: boolean
  best_score: number
  records: Array<Record<string, unknown>>
}

export interface Health {
  status: string
  version: string
  database: string
  storage: string
  timestamp: string
}

export interface SystemInfo {
  python_version: string
  platform: string
  cpu_count: number
  memory_total_bytes: number
  memory_available_bytes: number
  process_memory_bytes: number
  uptime_seconds: number
  dependencies: Record<string, string>
}

export interface OverviewData {
  summary: {
    datasets: number
    processed_datasets: number
    active_runs: number
    completed_runs: number
    average_quality_score: number
    duplicates: number
    quarantined_rows: number
    latest_throughput: number
    latest_runtime: number
    latest_peak_memory: number
    latest_input_size: number
    latest_output_size: number
  }
  quality: Array<{ run_id: string; before: number; after: number }>
  step_durations: Array<{ run_id: string; step: string; duration: number }>
  throughput: Array<{ run_id: string; created_at: string; rows_per_second: number }>
  dataset_volumes: Array<{ dataset_id: string; name: string; rows: number }>
  run_status: Record<string, number>
}


export interface BenchmarkResults {
  measured_at: string | null
  machine: { platform?: string; python?: string; cpu_count?: number; memory_total_bytes?: number }
  results: Array<{
    rows: number
    pipeline_seconds: number
    pipeline_rows_per_second: number
    pipeline_peak_observed_rss_bytes: number
    formats: {
      csv: { size_bytes: number; read_seconds: number; read_rows_per_second: number }
      parquet: { size_bytes: number; read_seconds: number; read_rows_per_second: number }
    }
  }>
}
