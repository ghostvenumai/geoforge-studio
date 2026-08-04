import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { ColumnDef } from '@tanstack/react-table'
import CodeMirror from '@uiw/react-codemirror'
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
} from '@xyflow/react'
import {
  Activity,
  AlertTriangle,
  Archive,
  ArrowDownToLine,
  BarChart3,
  CheckCircle2,
  Clock3,
  Cpu,
  Database,
  FileCheck2,
  FileUp,
  Gauge,
  HardDrive,
  MemoryStick,
  Network,
  Play,
  Plus,
  Redo2,
  RefreshCw,
  Save,
  ShieldCheck,
  Trash2,
  Undo2,
  Users,
  XCircle,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { DataTable } from '../components/data-table'
import { useToast } from '../components/context-hooks'
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  LoadingState,
  MetricCard,
  PageHeader,
  Panel,
  SkeletonGrid,
} from '../components/ui'
import { JsonPreview, LocalPointMap } from '../components/visuals'
import { api, uploadDataset } from '../lib/api'
import { displayValue, formatBytes, formatDate, formatNumber, shortId } from '../lib/utils'
import type { Artifact, ColumnProfile, Dataset, DuplicateGroup, Pipeline, Run } from '../types'

const chartColors = ['#159a85', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#64748b']

function statusTone(status: string): 'neutral' | 'good' | 'warn' | 'bad' | 'info' {
  if (['completed', 'healthy', 'ready', 'profiled'].includes(status)) return 'good'
  if (['failed', 'timed_out'].includes(status)) return 'bad'
  if (['running', 'queued'].includes(status)) return 'info'
  if (['cancelled', 'duplicate'].includes(status)) return 'warn'
  return 'neutral'
}

const statusLabels: Record<string, string> = {
  completed: 'Abgeschlossen', healthy: 'Fehlerfrei', ready: 'Bereit', profiled: 'Profiliert',
  failed: 'Fehlgeschlagen', timed_out: 'Zeitüberschreitung', running: 'Läuft', queued: 'Eingereiht',
  cancelled: 'Abgebrochen', duplicate: 'Dublettenfund', accepted: 'Angenommen', rejected: 'Abgelehnt',
}

function statusLabel(status: string): string {
  return statusLabels[status] ?? status
}

const stepLabels: Record<string, string> = {
  load_dataset: 'Datensatz laden', select_columns: 'Spalten auswählen', rename_columns: 'Spalten umbenennen',
  cast_types: 'Datentypen konvertieren', normalize_unicode: 'Unicode normalisieren', trim_whitespace: 'Leerzeichen bereinigen',
  replace_values: 'Werte ersetzen', parse_dates: 'Datumswerte parsen', handle_missing_values: 'Fehlende Werte behandeln',
  normalize_address: 'Adresse normalisieren', validate_postal_code: 'Postleitzahl prüfen', validate_coordinates: 'Koordinaten prüfen',
  transform_crs: 'Koordinatensystem transformieren', calculate_distance: 'Distanz berechnen', detect_duplicates: 'Dubletten erkennen',
  quarantine_invalid_rows: 'Ungültige Zeilen quarantänisieren', filter_rows: 'Zeilen filtern',
  add_calculated_column: 'Berechnete Spalte ergänzen', export_dataset: 'Datensatz exportieren',
}

function stepLabel(value: unknown): string {
  const key = displayValue(value)
  return stepLabels[key] ?? key.replaceAll('_', ' ')
}

const pipelineLabels: Record<string, string> = {
  'German Address Cleanup': 'Bereinigung deutscher Adressen',
  'Coordinate Validation and Transformation': 'Koordinatenprüfung und -transformation',
  'Full Data Quality and Deduplication': 'Vollständige Datenqualität und Deduplizierung',
}

function pipelineLabel(name: string): string {
  return pipelineLabels[name] ?? name
}

const recommendationLabels: Record<string, string> = {
  'Validate and quarantine invalid values': 'Ungültige Werte prüfen und quarantänisieren',
  'Define a missing-value strategy': 'Strategie für fehlende Werte festlegen',
  'Consider categorical encoding or value normalization': 'Kategorische Kodierung oder Wertnormalisierung erwägen',
  'Trim whitespace and normalize Unicode': 'Leerzeichen bereinigen und Unicode normalisieren',
  'No transformation required': 'Keine Transformation erforderlich',
}

function recommendationLabel(value: string): string {
  return recommendationLabels[value] ?? value
}

const artifactLabels: Record<string, string> = {
  result_parquet: 'Ergebnis (Parquet)', result_csv: 'Ergebnis (CSV)', result_jsonl: 'Ergebnis (JSONL)',
  quarantine: 'Quarantänedatensatz', quality_report: 'Qualitätsbericht', performance_report: 'Leistungsbericht',
  pipeline_yaml: 'Pipeline-YAML', audit_log: 'Audit-Protokoll', run_manifest: 'Laufmanifest', checksums: 'Prüfsummen',
}

function artifactLabel(kind: string): string {
  return artifactLabels[kind] ?? kind.replaceAll('_', ' ')
}

function SelectField({ label, value, onChange, children }: { label: string; value: string; onChange: (value: string) => void; children: React.ReactNode }) {
  return <label className="block text-sm font-medium text-gray-700 dark:text-gray-300"><span className="mb-1.5 block">{label}</span><select className="field" value={value} onChange={(event) => onChange(event.target.value)}>{children}</select></label>
}

export function OverviewPage() {
  const overview = useQuery({ queryKey: ['overview'], queryFn: api.overview, refetchInterval: 10_000 })
  const health = useQuery({ queryKey: ['health'], queryFn: api.health, refetchInterval: 15_000 })
  if (overview.isLoading) return <><PageHeader title="Übersicht" description="Betriebsübersicht zu Datensätzen, Qualität, Durchsatz und Systemstatus." /><SkeletonGrid /></>
  if (overview.error) return <ErrorState error={overview.error} retry={() => void overview.refetch()} />
  const data = overview.data!
  const summary = data.summary
  const statusData = Object.entries(data.run_status).map(([name, value]) => ({ name: statusLabel(name), value }))
  return (
    <>
      <PageHeader title="Übersicht" description="Aktuelle Betriebsübersicht über importierte Daten, gemessene Laufqualität, Durchsatz und Systemstatus." actions={<Badge tone={health.data?.status === 'healthy' ? 'good' : 'warn'}>{health.data?.status ? statusLabel(health.data.status) : 'Status wird geprüft'}</Badge>} />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Importierte Datensätze" value={formatNumber(summary.datasets)} detail={`${summary.processed_datasets} verarbeitet`} icon={<Database className="h-5 w-5" />} />
        <MetricCard label="Läufe" value={formatNumber(summary.completed_runs)} detail={`${summary.active_runs} aktiv`} icon={<Play className="h-5 w-5" />} />
        <MetricCard label="Durchschnittliche Qualität" value={`${summary.average_quality_score.toFixed(1)}/100`} detail="Abgeschlossene Läufe" icon={<Gauge className="h-5 w-5" />} />
        <MetricCard label="Dubletten" value={formatNumber(summary.duplicates)} detail="Datensätze in erkannten Gruppen" icon={<Users className="h-5 w-5" />} />
        <MetricCard label="Quarantänisierte Zeilen" value={formatNumber(summary.quarantined_rows)} icon={<AlertTriangle className="h-5 w-5" />} />
        <MetricCard label="Letzter Durchsatz" value={`${formatNumber(summary.latest_throughput)} r/s`} detail={`${summary.latest_runtime.toFixed(3)} s Laufzeit`} icon={<Activity className="h-5 w-5" />} />
        <MetricCard label="Spitzenspeicher" value={formatBytes(summary.latest_peak_memory)} detail="Gemessener Prozess-RSS" icon={<MemoryStick className="h-5 w-5" />} />
        <MetricCard label="E/A-Größe" value={formatBytes(summary.latest_output_size)} detail={`${formatBytes(summary.latest_input_size)} Eingabe`} icon={<HardDrive className="h-5 w-5" />} />
      </div>
      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Panel><h2 className="mb-4 font-semibold">Qualitätswert vor und nach der Verarbeitung</h2>{data.quality.length ? <ResponsiveContainer width="100%" height={280}><BarChart data={data.quality}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="run_id" tickFormatter={shortId} /><YAxis domain={[0, 100]} /><Tooltip /><Legend /><Bar name="Vorher" dataKey="before" fill="#94a3b8" radius={[4, 4, 0, 0]} /><Bar name="Nachher" dataKey="after" fill="#159a85" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer> : <p className="py-24 text-center text-sm text-gray-500">Führen Sie eine Pipeline aus, um die Qualität zu vergleichen.</p>}</Panel>
        <Panel><h2 className="mb-4 font-semibold">Durchsatzentwicklung</h2>{data.throughput.length ? <ResponsiveContainer width="100%" height={280}><AreaChart data={data.throughput}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="run_id" tickFormatter={shortId} /><YAxis /><Tooltip /><Area name="Zeilen pro Sekunde" type="monotone" dataKey="rows_per_second" stroke="#159a85" fill="#d6f5ed" /></AreaChart></ResponsiveContainer> : <p className="py-24 text-center text-sm text-gray-500">Noch kein gemessener Durchsatz vorhanden.</p>}</Panel>
        <Panel><h2 className="mb-4 font-semibold">Datensatzvolumen</h2><ResponsiveContainer width="100%" height={280}><BarChart data={data.dataset_volumes}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" /><YAxis /><Tooltip /><Bar name="Zeilen" dataKey="rows" fill="#3b82f6" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></Panel>
        <Panel><h2 className="mb-4 font-semibold">Verteilung der Laufstatus</h2>{statusData.length ? <ResponsiveContainer width="100%" height={280}><PieChart><Pie data={statusData} dataKey="value" nameKey="name" innerRadius={60} outerRadius={95} label>{statusData.map((entry, index) => <Cell key={entry.name} aria-label={entry.name + ' Läufe: ' + entry.value} fill={chartColors[index % chartColors.length]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer> : <p className="py-24 text-center text-sm text-gray-500">Noch keine Läufe vorhanden.</p>}</Panel>
      </div>
      <Panel className="mt-6"><h2 className="mb-4 font-semibold">Laufzeit je Pipeline-Schritt</h2><ResponsiveContainer width="100%" height={300}><BarChart data={data.step_durations.slice(-20)} layout="vertical"><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" /><YAxis type="category" dataKey="step" width={150} /><Tooltip /><Bar name="Dauer" dataKey="duration" fill="#159a85" radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer></Panel>
    </>
  )
}

export function DatasetsPage() {
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const datasets = useQuery({ queryKey: ['datasets'], queryFn: api.datasets })
  const [progress, setProgress] = useState<number | null>(null)
  const [dragging, setDragging] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const upload = useMutation({
    mutationFn: (file: File) => {
      abortRef.current = new AbortController()
      return uploadDataset(file, setProgress, abortRef.current.signal)
    },
    onSuccess: (dataset) => { notify(`${dataset.name} hochgeladen`); setProgress(null); void queryClient.invalidateQueries({ queryKey: ['datasets'] }) },
    onError: () => setProgress(null),
  })
  const remove = useMutation({ mutationFn: api.deleteDataset, onSuccess: () => { notify('Datensatz gelöscht'); void queryClient.invalidateQueries({ queryKey: ['datasets'] }) } })
  const handleFile = (file?: File) => { if (file) upload.mutate(file) }
  const columns = useMemo<Array<ColumnDef<Dataset>>>(() => [
    { accessorKey: 'name', header: 'Datensatz', cell: ({ row }) => <div><p className="font-semibold">{row.original.name}</p><p className="text-xs text-gray-500">{row.original.original_filename}</p></div> },
    { accessorKey: 'format', header: 'Format', cell: ({ getValue }) => <Badge>{String(getValue()).toUpperCase()}</Badge> },
    { accessorKey: 'row_count', header: 'Zeilen', cell: ({ getValue }) => formatNumber(Number(getValue())) },
    { accessorKey: 'column_count', header: 'Spalten' },
    { accessorKey: 'size_bytes', header: 'Größe', cell: ({ getValue }) => formatBytes(Number(getValue())) },
    { accessorKey: 'status', header: 'Status', cell: ({ getValue }) => <Badge tone={statusTone(String(getValue()))}>{statusLabel(String(getValue()))}</Badge> },
    { accessorKey: 'created_at', header: 'Importiert', cell: ({ getValue }) => formatDate(String(getValue())) },
    { id: 'actions', header: '', cell: ({ row }) => <Button className="bg-transparent px-2 text-red-600 shadow-none hover:bg-red-50 dark:hover:bg-red-950" aria-label={`Löschen: ${row.original.name}`} onClick={() => { if (window.confirm(`Löschen: ${row.original.name}, einschließlich Originaldatei, wirklich löschen?`)) remove.mutate(row.original.id) }}><Trash2 className="h-4 w-4" /></Button> },
  ], [remove])
  return (
    <>
      <PageHeader title="Datensätze" description="Unveränderte Quelldateien mit Typ-, Kodierungs-, Schema-, Prüfsummen- und Dateidublettenprüfung importieren." />
      <label className={`focus-within:ring-2 focus-within:ring-brand-500 mb-6 flex min-h-52 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-6 text-center transition ${dragging ? 'border-brand-500 bg-brand-50 dark:bg-brand-950' : 'border-gray-300 bg-white dark:border-gray-700 dark:bg-gray-900'}`} onDragEnter={(event) => { event.preventDefault(); setDragging(true) }} onDragOver={(event) => event.preventDefault()} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); handleFile(event.dataTransfer.files[0]) }}>
        <FileUp className="mb-3 h-9 w-9 text-brand-600" aria-hidden="true" /><span className="font-semibold">CSV-, JSON-, JSONL-, Parquet- oder XLSX-Datei hier ablegen</span><span className="mt-1 text-sm text-gray-500">oder eine lokale synthetische Datei auswählen · Größenlimit wird vom Backend geprüft</span>
        <input className="sr-only" type="file" accept=".csv,.json,.jsonl,.ndjson,.parquet,.xlsx" onChange={(event) => handleFile(event.target.files?.[0])} />
        {progress !== null && <div className="mt-5 w-full max-w-md" role="status" aria-label={`Upload ${progress}% complete`}><div className="mb-1 flex justify-between text-xs"><span>Wird hochgeladen</span><span>{progress}%</span></div><div className="h-2 overflow-hidden rounded bg-gray-200 dark:bg-gray-700"><div className="h-full bg-brand-600 transition-all" style={{ width: `${progress}%` }} /></div><Button className="mt-3 bg-gray-700" onClick={(event) => { event.preventDefault(); abortRef.current?.abort() }}>Upload abbrechen</Button></div>}
      </label>
      {upload.error && <ErrorState error={upload.error} />}
      {datasets.isLoading ? <LoadingState /> : datasets.error ? <ErrorState error={datasets.error} retry={() => void datasets.refetch()} /> : datasets.data?.items.length ? <DataTable data={datasets.data.items} columns={columns} label="Importierte Datensätze" /> : <EmptyState title="Noch keine Datensätze" description="Laden Sie synthetische Demodaten hoch, um Profiling und Transformation zu starten." />}
    </>
  )
}

export function ProfilingPage() {
  const { notify } = useToast()
  const queryClient = useQueryClient()
  const datasets = useQuery({ queryKey: ['datasets'], queryFn: api.datasets })
  const [datasetId, setDatasetId] = useState('')
  const [profileRequested, setProfileRequested] = useState(false)
  useEffect(() => { if (!datasetId && datasets.data?.items[0]) setDatasetId(datasets.data.items[0].id) }, [datasetId, datasets.data])
  useEffect(() => setProfileRequested(false), [datasetId])
  const selectedDataset = datasets.data?.items.find((dataset) => dataset.id === datasetId)
  const profile = useQuery({ queryKey: ['profile', datasetId], queryFn: () => api.profile(datasetId), enabled: Boolean(datasetId) && (profileRequested || selectedDataset?.status === 'profiled'), retry: false })
  const start = useMutation({ mutationFn: () => api.profileDataset(datasetId), onSuccess: () => { setProfileRequested(true); notify('Profiling abgeschlossen'); void queryClient.invalidateQueries({ queryKey: ['profile', datasetId] }) } })
  const columnDefs = useMemo<Array<ColumnDef<ColumnProfile>>>(() => [
    { accessorKey: 'name', header: 'Spalte', cell: ({ row }) => <div><p className="font-semibold">{row.original.name}</p><p className="text-xs text-gray-500">{row.original.sample_values.map(String).join(' · ') || 'Keine Beispiele'}</p></div> },
    { accessorKey: 'dtype', header: 'Typ', cell: ({ getValue }) => <Badge>{String(getValue())}</Badge> },
    { accessorKey: 'null_ratio', header: 'Nullwertquote', cell: ({ getValue }) => `${(Number(getValue()) * 100).toFixed(1)}%` },
    { accessorKey: 'unique_ratio', header: 'Eindeutigkeitsquote', cell: ({ getValue }) => `${(Number(getValue()) * 100).toFixed(1)}%` },
    { accessorKey: 'invalid_count', header: 'Ungültig', cell: ({ getValue }) => <span className={Number(getValue()) ? 'font-semibold text-red-600' : 'text-emerald-600'}>{String(getValue())}</span> },
    { accessorKey: 'recommendation', header: 'Empfohlene Transformation', cell: ({ getValue }) => recommendationLabel(String(getValue())) },
  ], [])
  const data = profile.data?.profile
  return <><PageHeader title="Datenprofiling" description="Stichprobenfähige, spaltenbasierte Statistiken und konkrete Transformationsempfehlungen aus dem Backend." actions={<Button disabled={!datasetId || start.isPending} onClick={() => start.mutate()}><RefreshCw className="h-4 w-4" />{start.isPending ? 'Profiling…' : 'Profiling starten'}</Button>} />
    <Panel className="mb-6"><SelectField label="Datensatz" value={datasetId} onChange={setDatasetId}><option value="">Datensatz auswählen</option>{datasets.data?.items.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.name} · {formatNumber(dataset.row_count)} Zeilen</option>)}</SelectField></Panel>
    {profile.isLoading ? <LoadingState label="Profil wird geladen" /> : profile.error && !data ? <EmptyState title="Kein Profil verfügbar" description="Starten Sie das Profiling, um Qualität, Verteilungen, Nullwerte, Eindeutigkeit, ungültige Werte und Empfehlungen zu berechnen." /> : data ? <><div className="grid grid-cols-2 gap-4 lg:grid-cols-5"><MetricCard label="Qualitätswert" value={`${data.quality_score}/100`} /><MetricCard label="Zeilen" value={formatNumber(data.row_count)} detail={data.sampled ? `${formatNumber(data.sampled_rows)} in Stichprobe` : 'Vollständiger Datensatz'} /><MetricCard label="Nullwerte" value={formatNumber(data.total_null_count)} /><MetricCard label="Ungültige Werte" value={formatNumber(data.total_invalid_count)} /><MetricCard label="Exakte Dubletten" value={formatNumber(data.exact_duplicate_count)} /></div><div className="mt-6"><DataTable data={data.columns} columns={columnDefs} label="Spaltenprofil" /></div></> : <EmptyState title="Datensatz auswählen" description="Wählen Sie einen importierten Datensatz, um sein Profil zu untersuchen." />}
  </>
}

const stepTypes = ['load_dataset', 'select_columns', 'rename_columns', 'cast_types', 'normalize_unicode', 'trim_whitespace', 'replace_values', 'parse_dates', 'handle_missing_values', 'normalize_address', 'validate_postal_code', 'validate_coordinates', 'transform_crs', 'calculate_distance', 'detect_duplicates', 'quarantine_invalid_rows', 'filter_rows', 'add_calculated_column', 'export_dataset']

function pipelineNodes(pipeline?: Pipeline): Node[] {
  return pipeline?.definition_json.steps.map((step, index) => ({ id: step.id, position: step.position ?? { x: 100 + (index % 3) * 240, y: 70 + Math.floor(index / 3) * 130 }, data: { label: stepLabel(step.type), stepType: step.type, config: step.config }, className: 'rounded-xl border-2 border-brand-500 bg-white px-4 py-3 text-sm font-semibold shadow-lg dark:bg-gray-900' })) ?? []
}

function pipelineEdges(pipeline?: Pipeline): Edge[] {
  return pipeline?.definition_json.edges.map((edge) => ({ ...edge, animated: true })) ?? []
}

export function PipelineBuilderPage() {
  const { notify } = useToast()
  const queryClient = useQueryClient()
  const pipelines = useQuery({ queryKey: ['pipelines'], queryFn: api.pipelines })
  const datasets = useQuery({ queryKey: ['datasets'], queryFn: api.datasets })
  const [pipelineId, setPipelineId] = useState('')
  const [datasetId, setDatasetId] = useState('')
  const selected = pipelines.data?.items.find((pipeline) => pipeline.id === pipelineId)
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const [yamlText, setYamlText] = useState('')
  const [mode, setMode] = useState<'visual' | 'yaml'>('visual')
  const history = useRef<Array<{ nodes: Node[]; edges: Edge[] }>>([])
  const redo = useRef<Array<{ nodes: Node[]; edges: Edge[] }>>([])
  useEffect(() => { if (!pipelineId && pipelines.data?.items[0]) setPipelineId(pipelines.data.items[0].id) }, [pipelineId, pipelines.data])
  useEffect(() => { if (!datasetId && datasets.data?.items[0]) setDatasetId(datasets.data.items[0].id) }, [datasetId, datasets.data])
  useEffect(() => { if (selected) { setNodes(pipelineNodes(selected)); setEdges(pipelineEdges(selected)); setYamlText(selected.yaml_text); history.current = []; redo.current = [] } }, [selected, setEdges, setNodes])
  const visualYaml = useCallback(() => JSON.stringify({
    name: selected?.name ?? 'Visuelle Pipeline',
    description: selected?.description ?? 'Im visuellen GeoForge-Pipeline-Builder erstellt.',
    version: (selected?.version ?? 0) + 1,
    steps: nodes.map((node) => ({ id: node.id, type: node.data.stepType, name: node.data.label, config: node.data.config ?? {}, position: node.position })),
    edges: edges.map((edge, index) => ({ id: edge.id || 'edge-' + index, source: edge.source, target: edge.target })),
  }, null, 2), [edges, nodes, selected])
  const activeDefinition = useCallback(() => mode === 'visual' ? visualYaml() : yamlText, [mode, visualYaml, yamlText])
  const snapshot = useCallback(() => { history.current.push({ nodes: structuredClone(nodes), edges: structuredClone(edges) }); redo.current = [] }, [edges, nodes])
  const onConnect = useCallback((connection: Connection) => { snapshot(); setEdges((current) => addEdge({ ...connection, animated: true }, current)) }, [setEdges, snapshot])
  const addStep = (type: string, position = { x: 120 + (nodes.length % 3) * 180, y: 100 + Math.floor(nodes.length / 3) * 120 }) => { snapshot(); const id = `${type.replaceAll('_', '-')}-${Date.now()}`; setNodes((current) => [...current, { id, position, data: { label: stepLabel(type), stepType: type, config: {} }, className: 'rounded-xl border-2 border-brand-500 bg-white px-4 py-3 text-sm font-semibold shadow-lg dark:bg-gray-900' }]) }
  const validate = useMutation({ mutationFn: () => api.validatePipeline(activeDefinition()), onSuccess: (result) => notify(`Pipeline gültig · ${result.checksum.slice(0, 12)}`) })
  const save = useMutation({ mutationFn: () => api.createPipeline(activeDefinition()), onSuccess: (pipeline) => { notify(`Gespeichert: ${pipelineLabel(pipeline.name)} · Version ${pipeline.version}`); void queryClient.invalidateQueries({ queryKey: ['pipelines'] }) } })
  const run = useMutation({ mutationFn: () => api.startRun(pipelineId, datasetId), onSuccess: (started) => { notify(`Lauf ${shortId(started.id)} wurde eingereiht`); void queryClient.invalidateQueries({ queryKey: ['runs'] }) } })
  const undoAction = () => { const previous = history.current.pop(); if (previous) { redo.current.push({ nodes, edges }); setNodes(previous.nodes); setEdges(previous.edges) } }
  const redoAction = () => { const next = redo.current.pop(); if (next) { history.current.push({ nodes, edges }); setNodes(next.nodes); setEdges(next.edges) } }
  const exportYaml = () => { const url = URL.createObjectURL(new Blob([yamlText], { type: 'application/yaml' })); const anchor = document.createElement('a'); anchor.href = url; anchor.download = `${selected?.name ?? 'pipeline'}.yaml`; anchor.click(); URL.revokeObjectURL(url) }
  const importYaml = (file?: File) => { if (file) void file.text().then(setYamlText) }
  return <><PageHeader title="Pipeline-Builder" description="Erstellen Sie validierte, versionierte Transformationsgraphen ohne ausführbaren Code. YAML wird im Backend sicher geparst." actions={<><Button className="bg-white text-gray-700 ring-1 ring-gray-300 hover:bg-gray-50 dark:bg-gray-900 dark:text-gray-200 dark:ring-gray-700" onClick={() => setMode((current) => current === 'visual' ? 'yaml' : 'visual')}>{mode === 'visual' ? 'YAML-Ansicht' : 'Visuelle Ansicht'}</Button><Button disabled={!pipelineId || !datasetId || run.isPending} onClick={() => run.mutate()}><Play className="h-4 w-4" />Pipeline ausführen</Button></>} />
    <div className="mb-4 grid gap-4 md:grid-cols-2"><SelectField label="Pipeline-Version" value={pipelineId} onChange={setPipelineId}><option value="">Pipeline auswählen</option>{pipelines.data?.items.map((pipeline) => <option key={pipeline.id} value={pipeline.id}>{pipelineLabel(pipeline.name)} · v{pipeline.version}</option>)}</SelectField><SelectField label="Eingabedatensatz" value={datasetId} onChange={setDatasetId}><option value="">Datensatz auswählen</option>{datasets.data?.items.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.name}</option>)}</SelectField></div>
    <div className="mb-4 flex flex-wrap gap-2"><Button className="bg-white px-3 text-gray-700 ring-1 ring-gray-300 hover:bg-gray-50 dark:bg-gray-900 dark:text-gray-200 dark:ring-gray-700" disabled={!history.current.length} onClick={undoAction}><Undo2 className="h-4 w-4" />Rückgängig</Button><Button className="bg-white px-3 text-gray-700 ring-1 ring-gray-300 hover:bg-gray-50 dark:bg-gray-900 dark:text-gray-200 dark:ring-gray-700" disabled={!redo.current.length} onClick={redoAction}><Redo2 className="h-4 w-4" />Wiederholen</Button><Button className="bg-white px-3 text-gray-700 ring-1 ring-gray-300 hover:bg-gray-50 dark:bg-gray-900 dark:text-gray-200 dark:ring-gray-700" onClick={() => validate.mutate()}><ShieldCheck className="h-4 w-4" />Validieren</Button><Button className="bg-white px-3 text-gray-700 ring-1 ring-gray-300 hover:bg-gray-50 dark:bg-gray-900 dark:text-gray-200 dark:ring-gray-700" onClick={() => save.mutate()}><Save className="h-4 w-4" />Als Version speichern</Button><Button className="bg-white px-3 text-gray-700 ring-1 ring-gray-300 hover:bg-gray-50 dark:bg-gray-900 dark:text-gray-200 dark:ring-gray-700" onClick={exportYaml}><ArrowDownToLine className="h-4 w-4" />YAML exportieren</Button><label className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-gray-700 ring-1 ring-gray-300 dark:bg-gray-900 dark:text-gray-200 dark:ring-gray-700"><FileUp className="h-4 w-4" />YAML importieren<input className="sr-only" type="file" accept=".yaml,.yml" onChange={(event) => importYaml(event.target.files?.[0])} /></label></div>
    {validate.error && <div className="mb-4"><ErrorState error={validate.error} /></div>}
    {mode === 'yaml' ? <Panel><CodeMirror value={yamlText} height="650px" theme="dark" onChange={setYamlText} basicSetup={{ lineNumbers: true, foldGutter: true }} aria-label="Pipeline-YAML-Editor" /></Panel> : <div className="grid min-h-[680px] grid-cols-1 gap-4 xl:grid-cols-[220px_minmax(0,1fr)_300px]"><Panel className="max-h-[680px] overflow-y-auto"><h2 className="mb-3 font-semibold">Schrittauswahl</h2><p className="mb-3 text-xs text-gray-500">Ziehen Sie einen Schritt auf die Arbeitsfläche.</p>{stepTypes.map((type) => <button key={type} draggable onDragStart={(event) => event.dataTransfer.setData('application/geoforge-step', type)} onClick={() => addStep(type)} className="focus-ring mb-2 flex w-full items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-left text-xs font-medium hover:border-brand-500 hover:bg-brand-50 dark:border-gray-700 dark:hover:bg-brand-950"><Plus className="h-3.5 w-3.5" />{stepLabel(type)}</button>)}</Panel><Panel className="h-[680px] overflow-hidden p-0" onDragOver={(event) => event.preventDefault()} onDrop={(event: DragEvent<HTMLDivElement>) => { event.preventDefault(); const type = event.dataTransfer.getData('application/geoforge-step'); if (type) addStep(type, { x: event.nativeEvent.offsetX, y: event.nativeEvent.offsetY }) }}><ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect} onNodeClick={(_, node) => setSelectedNode(node)} fitView><Background /><MiniMap pannable zoomable /><Controls /></ReactFlow></Panel><Panel className="max-h-[680px] overflow-y-auto"><h2 className="font-semibold">Schrittkonfiguration</h2>{selectedNode ? <><label className="mt-4 block text-sm font-medium">Name<input className="field mt-1" value={displayValue(selectedNode.data.label)} onChange={(event) => { const label = event.target.value; setNodes((current) => current.map((node) => node.id === selectedNode.id ? { ...node, data: { ...node.data, label } } : node)); setSelectedNode((current) => current ? { ...current, data: { ...current.data, label } } : null) }} /></label><label className="mt-4 block text-sm font-medium">Validierte JSON-Konfiguration<textarea className="field mt-1 min-h-72 font-mono text-xs" defaultValue={JSON.stringify(selectedNode.data.config ?? {}, null, 2)} onBlur={(event) => { try { const config = JSON.parse(event.target.value) as Record<string, unknown>; setNodes((current) => current.map((node) => node.id === selectedNode.id ? { ...node, data: { ...node.data, config } } : node)); } catch { notify('Die Konfiguration muss gültiges JSON sein') } }} /></label><p className="mt-3 text-xs text-gray-500">Typ: {stepLabel(selectedNode.data.stepType)}</p></> : <p className="mt-4 text-sm text-gray-500">Wählen Sie einen Knoten aus, um Schema und Konfiguration zu prüfen.</p>}</Panel></div>}
  </>
}

function useCompletedRuns() {
  return useQuery({ queryKey: ['runs'], queryFn: api.runs, refetchInterval: (query) => query.state.data?.items.some((run) => ['queued', 'running'].includes(run.status)) ? 1500 : false })
}

export function AddressPage() {
  const runs = useCompletedRuns()
  const [runId, setRunId] = useState('')
  const completed = useMemo(() => runs.data?.items.filter((run) => run.status === 'completed' && run.metrics_json.result_preview) ?? [], [runs.data?.items])
  useEffect(() => { if (!runId && completed[0]) setRunId(completed[0].id) }, [completed, runId])
  const run = completed.find((item) => item.id === runId)
  const records = run?.metrics_json.result_preview ?? []
  return <><PageHeader title="Adressverarbeitung" description="Vorher-Nachher-Auditfelder für Unicode, Straßenschreibweisen, Hausnummern, Postleitzahlen, Orte und Ländercodes." /><Panel className="mb-6"><SelectField label="Abgeschlossener Lauf" value={runId} onChange={setRunId}><option value="">Lauf auswählen</option>{completed.map((item) => <option key={item.id} value={item.id}>{shortId(item.id)} · {formatDate(item.finished_at)}</option>)}</SelectField></Panel>{records.length ? <><div className="grid grid-cols-1 gap-4 md:grid-cols-3"><MetricCard label="Ausgabezeilen" value={formatNumber(run?.output_rows ?? 0)} /><MetricCard label="Qualitätsänderung" value={`${(run?.quality_before ?? 0).toFixed(1)} → ${(run?.quality_after ?? 0).toFixed(1)}`} /><MetricCard label="Quarantänisiert" value={formatNumber(run?.quarantine_rows ?? 0)} /></div><Panel className="mt-6"><h2 className="mb-4 font-semibold">Originale und normalisierte Adresswerte</h2><JsonPreview records={records} /></Panel></> : <EmptyState title="Noch kein Adressergebnis" description="Führen Sie die Pipeline „Bereinigung deutscher Adressen“ aus, um den Vorher-Nachher-Vergleich zu füllen." />}</>
}

export function GeoPage() {
  const runs = useCompletedRuns()
  const [runId, setRunId] = useState('')
  const completed = useMemo(() => runs.data?.items.filter((run) => run.status === 'completed') ?? [], [runs.data?.items])
  useEffect(() => { if (!runId && completed[0]) setRunId(completed[0].id) }, [completed, runId])
  const run = completed.find((item) => item.id === runId)
  const records = run?.metrics_json.result_preview ?? []
  const valid = records.filter((record) => record.coordinates_valid === true).length
  const swapped = records.filter((record) => record.coordinates_swapped === true).length
  return <><PageHeader title="Geoverarbeitung" description="Lokale Koordinatenvalidierung, Vertauschungserkennung, CRS-Transformation, Distanzberechnung und Punktvisualisierung ohne externen Kartendienst." /><Panel className="mb-6"><SelectField label="Abgeschlossener Lauf" value={runId} onChange={setRunId}><option value="">Lauf auswählen</option>{completed.map((item) => <option key={item.id} value={item.id}>{shortId(item.id)} · {formatDate(item.finished_at)}</option>)}</SelectField></Panel>{records.length ? <><div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4"><MetricCard label="Vorschaupunkte" value={records.length} /><MetricCard label="Gültige Koordinaten" value={valid} /><MetricCard label="Vertauscht und korrigiert" value={swapped} /><MetricCard label="Ungültig/quarantänisiert" value={run?.quarantine_rows ?? 0} /></div><LocalPointMap records={records} /><Panel className="mt-6"><JsonPreview records={records} /></Panel></> : <EmptyState title="Noch kein Koordinatenergebnis" description="Führen Sie die Beispielpipeline zur Koordinatenvalidierung aus, um lokale Punktdaten darzustellen." />}</>
}

function DifferenceTable({ records, canonicalId }: { records: Array<Record<string, unknown>>; canonicalId?: string }) {
  const columns = Array.from(new Set(records.flatMap(Object.keys))).filter((column) => !['matched_columns'].includes(column)).slice(0, 14)
  return <div className="focus-ring max-w-full overflow-x-auto" role="region" aria-label="Scrollbarer Dublettenvergleich" tabIndex={0}><table className="data-table" aria-label="Vergleich doppelter Datensätze"><thead><tr><th>Feld</th>{records.map((record, index) => <th key={index}>{displayValue(record.record_id ?? index)}{String(record.record_id) === canonicalId && <Badge tone="good">Kanonisch</Badge>}</th>)}</tr></thead><tbody>{columns.map((column) => { const values = records.map((record) => displayValue(record[column])); const differs = new Set(values).size > 1; return <tr key={column}><td className="font-semibold">{column}</td>{values.map((value, index) => <td key={index} className={differs ? 'bg-amber-50 font-medium text-amber-900 dark:bg-amber-950 dark:text-amber-200' : ''}>{value}</td>)}</tr> })}</tbody></table></div>
}

export function DuplicatesPage() {
  const { notify } = useToast()
  const runs = useCompletedRuns()
  const [runId, setRunId] = useState('')
  const candidates = useMemo(() => runs.data?.items.filter((run) => run.status === 'completed' && run.duplicate_count > 0) ?? [], [runs.data?.items])
  useEffect(() => { if (!runId && candidates[0]) setRunId(candidates[0].id) }, [candidates, runId])
  const groups = useQuery({ queryKey: ['duplicates', runId], queryFn: () => api.duplicates(runId), enabled: Boolean(runId) })
  const [selectedGroup, setSelectedGroup] = useState<DuplicateGroup | null>(null)
  const [canonical, setCanonical] = useState('')
  useEffect(() => { const first = groups.data?.items[0]; if (first) { setSelectedGroup(first); setCanonical(displayValue(first.records[0]?.canonical_record_id ?? first.records[0]?.record_id ?? '')) } }, [groups.data])
  const decision = useMutation({ mutationFn: (value: 'accepted' | 'rejected') => api.decideDuplicate(runId, selectedGroup!.group_id, value, canonical || undefined), onSuccess: (_, value) => notify(`Dublettenentscheidung: ${statusLabel(value)}`) })
  return <><PageHeader title="Dublettenprüfung" description="Vergleichen Sie vorselektierte Fuzzy-Kandidaten nebeneinander, heben Sie Unterschiede hervor und dokumentieren Sie die kanonische Entscheidung." /><Panel className="mb-6"><SelectField label="Lauf mit Dublettenkandidaten" value={runId} onChange={setRunId}><option value="">Lauf auswählen</option>{candidates.map((run) => <option key={run.id} value={run.id}>{shortId(run.id)} · {run.duplicate_count} übereinstimmende Datensätze</option>)}</SelectField></Panel>{groups.isLoading ? <LoadingState /> : !groups.data?.items.length ? <EmptyState title="Keine Dublettengruppen" description="Führen Sie „Vollständige Datenqualität und Deduplizierung“ aus, um Prüfkandidaten zu erzeugen." /> : <div className="grid min-w-0 gap-6 xl:grid-cols-[280px_minmax(0,1fr)]"><Panel className="max-h-[680px] overflow-y-auto"><h2 className="mb-3 font-semibold">Unsichere Treffer</h2>{groups.data.items.map((group) => <button key={group.group_id} className={`focus-ring mb-2 w-full rounded-lg border p-3 text-left ${selectedGroup?.group_id === group.group_id ? 'border-brand-500 bg-brand-50 dark:bg-brand-950' : 'border-gray-200 dark:border-gray-700'}`} onClick={() => { setSelectedGroup(group); setCanonical(displayValue(group.records[0]?.canonical_record_id ?? group.records[0]?.record_id ?? '')) }}><span className="block font-mono text-xs">{group.group_id}</span><span className="mt-1 flex justify-between text-xs"><span>{group.records.length} Datensätze</span><Badge tone={group.review_required ? 'warn' : 'good'}>{group.best_score.toFixed(1)}</Badge></span></button>)}</Panel>{selectedGroup && <Panel className="min-w-0"><div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center"><div><h2 className="font-semibold">Gruppe {selectedGroup.group_id}</h2><p className="text-sm text-gray-500">Unterschiede sind hervorgehoben. Der Vergleich wurde durch Kandidaten-Blocking begrenzt.</p></div><div className="flex gap-2"><Button className="bg-red-700 hover:bg-red-800" onClick={() => decision.mutate('rejected')}><XCircle className="h-4 w-4" />Ablehnen</Button><Button onClick={() => decision.mutate('accepted')}><CheckCircle2 className="h-4 w-4" />Annehmen</Button></div></div><label className="mb-4 block text-sm font-medium">Kanonischer Datensatz<select className="field mt-1" value={canonical} onChange={(event) => setCanonical(event.target.value)}>{selectedGroup.records.map((record, index) => <option key={index} value={displayValue(record.record_id ?? index)}>{displayValue(record.record_id ?? index)}</option>)}</select></label><DifferenceTable records={selectedGroup.records} canonicalId={canonical} /></Panel>}</div>}</>
}

export function QualityPage() {
  const runs = useCompletedRuns()
  const completed = useMemo(() => runs.data?.items.filter((run) => run.status === 'completed') ?? [], [runs.data?.items])
  const chart = completed.slice().reverse().map((run) => ({ run: shortId(run.id), before: run.quality_before, after: run.quality_after, quarantine: run.quarantine_rows, rowLoss: Math.max(0, run.input_rows - run.output_rows - run.quarantine_rows) }))
  const latest = completed[0]
  return <><PageHeader title="Qualitätsanalyse" description="Qualitätsverbesserungen werden zusammen mit Quarantäne und Schutz vor unerklärtem Datenverlust dargestellt." />{latest ? <><div className="grid grid-cols-2 gap-4 lg:grid-cols-4"><MetricCard label="Vorher" value={latest.quality_before?.toFixed(1) ?? '—'} /><MetricCard label="Nachher" value={latest.quality_after?.toFixed(1) ?? '—'} /><MetricCard label="Absolute Änderung" value={`${((latest.quality_after ?? 0) - (latest.quality_before ?? 0)).toFixed(1)}`} /><MetricCard label="Quarantäne" value={latest.quarantine_rows} detail={`${Math.max(0, latest.input_rows - latest.output_rows - latest.quarantine_rows)} unerklärter Zeilenverlust`} /></div><Panel className="mt-6"><h2 className="mb-4 font-semibold">Vergleich der Laufqualität</h2><ResponsiveContainer width="100%" height={320}><BarChart data={chart}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="run" /><YAxis domain={[0, 100]} /><Tooltip /><Legend /><Bar name="Vorher" dataKey="before" fill="#94a3b8" /><Bar name="Nachher" dataKey="after" fill="#159a85" /></BarChart></ResponsiveContainer></Panel><Panel className="mt-6"><h2 className="mb-4 font-semibold">Quarantäne- und Zeilenverlustkontrolle</h2><ResponsiveContainer width="100%" height={260}><BarChart data={chart}><XAxis dataKey="run" /><YAxis /><Tooltip /><Legend /><Bar name="Quarantäne" dataKey="quarantine" fill="#f59e0b" /><Bar name="Zeilenverlust" dataKey="rowLoss" fill="#ef4444" /></BarChart></ResponsiveContainer></Panel></> : <EmptyState title="Kein Qualitätsvergleich" description="Schließen Sie einen Pipeline-Lauf ab, um die Qualität vorher und nachher zu vergleichen." />}</>
}

export function PerformancePage() {
  const runs = useCompletedRuns()
  const benchmarks = useQuery({ queryKey: ['benchmarks'], queryFn: api.benchmarks })
  const completed = useMemo(() => runs.data?.items.filter((run) => run.status === 'completed') ?? [], [runs.data?.items])
  const selected = completed[0]
  const series = completed.slice().reverse().map((run) => ({ run: shortId(run.id), throughput: run.metrics_json.rows_per_second ?? 0, runtime: run.metrics_json.total_runtime_seconds ?? 0, memory: (run.metrics_json.peak_memory_bytes ?? 0) / 1024 / 1024 }))
  const benchmarkSeries = benchmarks.data?.results.map((result) => ({ rows: result.rows, csvRead: result.formats.csv.read_rows_per_second, parquetRead: result.formats.parquet.read_rows_per_second, csvSize: result.formats.csv.size_bytes / 1024 / 1024, parquetSize: result.formats.parquet.size_bytes / 1024 / 1024, pipeline: result.pipeline_rows_per_second })) ?? []
  return <><PageHeader title="Performance" description="Tatsächlich gemessene Gesamtlaufzeit, Schrittdauer, Durchsatz, CPU, RSS-Speicher, E/A, Kompression und reproduzierbare Formatbenchmarks." />
    {selected ? <><div className="grid grid-cols-2 gap-4 lg:grid-cols-4"><MetricCard label="Laufzeit" value={(selected.metrics_json.total_runtime_seconds?.toFixed(3) ?? '0') + ' s'} icon={<Clock3 className="h-5 w-5" />} /><MetricCard label="Durchsatz" value={formatNumber(selected.metrics_json.rows_per_second ?? 0) + ' r/s'} icon={<Activity className="h-5 w-5" />} /><MetricCard label="Spitzenspeicher" value={formatBytes(selected.metrics_json.peak_memory_bytes ?? 0)} icon={<MemoryStick className="h-5 w-5" />} /><MetricCard label="Durchschnittliche CPU" value={(selected.metrics_json.average_cpu_percent?.toFixed(1) ?? '0') + '%'} icon={<Cpu className="h-5 w-5" />} /></div><div className="mt-6 grid gap-6 xl:grid-cols-2"><Panel><h2 className="mb-4 font-semibold">Durchsatztrend</h2><ResponsiveContainer width="100%" height={300}><LineChart data={series}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="run" /><YAxis /><Tooltip /><Line name="Durchsatz" type="monotone" dataKey="throughput" stroke="#159a85" strokeWidth={2} /></LineChart></ResponsiveContainer></Panel><Panel><h2 className="mb-4 font-semibold">Speicher und Laufzeit</h2><ResponsiveContainer width="100%" height={300}><LineChart data={series}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="run" /><YAxis /><Tooltip /><Legend /><Line name="Speicher" type="monotone" dataKey="memory" stroke="#8b5cf6" /><Line name="Laufzeit" type="monotone" dataKey="runtime" stroke="#f59e0b" /></LineChart></ResponsiveContainer></Panel></div><Panel className="mt-6"><h2 className="mb-4 font-semibold">Letzte Laufzeit je Schritt</h2><ResponsiveContainer width="100%" height={320}><BarChart data={selected.metrics_json.steps ?? []} layout="vertical"><XAxis type="number" /><YAxis type="category" dataKey="name" width={180} /><Tooltip /><Bar name="Dauer in Sekunden" dataKey="duration_seconds" fill="#3b82f6" radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer></Panel></> : <EmptyState title="Noch keine gemessene Laufleistung" description="Schließen Sie einen Pipeline-Lauf ab, um reale Prozessmetriken zu erfassen." />}
    {benchmarkSeries.length ? <div className="mt-6 grid gap-6 xl:grid-cols-2"><Panel><h2 className="font-semibold">CSV- und Parquet-Lesedurchsatz</h2><p className="mb-4 mt-1 text-xs text-gray-600 dark:text-gray-400">Gemessen am {formatDate(benchmarks.data?.measured_at ?? null)}</p><ResponsiveContainer width="100%" height={300}><BarChart data={benchmarkSeries}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="rows" /><YAxis /><Tooltip /><Legend /><Bar dataKey="csvRead" name="CSV Zeilen/s" fill="#3b82f6" /><Bar dataKey="parquetRead" name="Parquet Zeilen/s" fill="#159a85" /></BarChart></ResponsiveContainer></Panel><Panel><h2 className="font-semibold">CSV- und Parquet-Dateigröße</h2><p className="mb-4 mt-1 text-xs text-gray-600 dark:text-gray-400">MiB für dieselben deterministisch erzeugten synthetischen Zeilen</p><ResponsiveContainer width="100%" height={300}><BarChart data={benchmarkSeries}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="rows" /><YAxis /><Tooltip /><Legend /><Bar dataKey="csvSize" name="CSV MiB" fill="#f59e0b" /><Bar dataKey="parquetSize" name="Parquet MiB" fill="#8b5cf6" /></BarChart></ResponsiveContainer></Panel></div> : <Panel className="mt-6"><p className="text-sm text-gray-600 dark:text-gray-400">Noch keine Benchmark-Ergebnisdatei verfügbar.</p></Panel>}
  </>
}

export function RunsPage() {
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const runs = useCompletedRuns()
  const cancel = useMutation({ mutationFn: api.cancelRun, onSuccess: () => { notify('Abbruch angefordert'); void queryClient.invalidateQueries({ queryKey: ['runs'] }) } })
  const columns = useMemo<Array<ColumnDef<Run>>>(() => [
    { accessorKey: 'id', header: 'Lauf', cell: ({ getValue }) => <span className="font-mono text-xs">{shortId(String(getValue()))}</span> },
    { accessorKey: 'status', header: 'Status', cell: ({ getValue }) => <Badge tone={statusTone(String(getValue()))}>{statusLabel(String(getValue()))}</Badge> },
    { accessorKey: 'input_rows', header: 'Eingabe', cell: ({ getValue }) => formatNumber(Number(getValue())) },
    { accessorKey: 'output_rows', header: 'Ausgabe', cell: ({ getValue }) => formatNumber(Number(getValue())) },
    { accessorKey: 'quarantine_rows', header: 'Quarantäne' },
    { accessorKey: 'quality_after', header: 'Qualität', cell: ({ getValue }) => getValue() === null ? '—' : Number(getValue()).toFixed(1) },
    { accessorKey: 'created_at', header: 'Erstellt', cell: ({ getValue }) => formatDate(String(getValue())) },
    { id: 'action', header: '', cell: ({ row }) => ['queued', 'running'].includes(row.original.status) ? <Button className="bg-red-700" onClick={() => cancel.mutate(row.original.id)}>Abbrechen</Button> : null },
  ], [cancel])
  return <><PageHeader title="Läufe und Audit" description="Reproduzierbare Ausführungshistorie mit Status, Qualität, Zeilenzahlen, Warnungen, Fehlern und Abbruchmöglichkeit." />{runs.isLoading ? <LoadingState /> : runs.data?.items.length ? <DataTable data={runs.data.items} columns={columns} label="Pipeline-Läufe" /> : <EmptyState title="Noch keine Läufe" description="Starten Sie im Pipeline-Builder eine Beispielpipeline." />}</>
}

export function ExportsPage() {
  const runs = useCompletedRuns()
  const [runId, setRunId] = useState('')
  const completed = useMemo(() => runs.data?.items.filter((run) => run.status === 'completed') ?? [], [runs.data?.items])
  useEffect(() => { if (!runId && completed[0]) setRunId(completed[0].id) }, [completed, runId])
  const artifacts = useQuery({ queryKey: ['artifacts', runId], queryFn: () => api.artifacts(runId), enabled: Boolean(runId) })
  const columns = useMemo<Array<ColumnDef<Artifact>>>(() => [
    { accessorKey: 'kind', header: 'Artefakt', cell: ({ row }) => <div><p className="font-semibold">{artifactLabel(row.original.kind)}</p><p className="text-xs text-gray-500">{row.original.name}</p></div> },
    { accessorKey: 'media_type', header: 'Medientyp' },
    { accessorKey: 'size_bytes', header: 'Größe', cell: ({ getValue }) => formatBytes(Number(getValue())) },
    { accessorKey: 'checksum', header: 'SHA-256', cell: ({ getValue }) => <span className="font-mono text-xs">{String(getValue()).slice(0, 16)}…</span> },
    { id: 'download', header: '', cell: ({ row }) => <a className="focus-ring inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-50 dark:text-brand-300" href={api.artifactUrl(row.original.id)}><ArrowDownToLine className="h-4 w-4" />Herunterladen</a> },
  ], [])
  return <><PageHeader title="Exporte" description="Bereinigte CSV-, JSONL- und Parquet-Dateien sowie Qualitäts-/Leistungsberichte, Quarantäne, Audit, Manifeste, YAML und Prüfsummen." /><Panel className="mb-6"><SelectField label="Abgeschlossener Lauf" value={runId} onChange={setRunId}><option value="">Lauf auswählen</option>{completed.map((run) => <option key={run.id} value={run.id}>{shortId(run.id)} · {formatDate(run.finished_at)}</option>)}</SelectField></Panel>{artifacts.isLoading ? <LoadingState /> : artifacts.data?.items.length ? <DataTable data={artifacts.data.items} columns={columns} label="Laufartefakte" /> : <EmptyState title="Keine Exportartefakte" description="Schließen Sie einen Lauf ab, um Artefakte mit Prüfsummen zu erzeugen." />}</>
}

export function HealthPage() {
  const health = useQuery({ queryKey: ['health'], queryFn: api.health, refetchInterval: 5000 })
  const system = useQuery({ queryKey: ['system-info'], queryFn: api.systemInfo, refetchInterval: 5000 })
  if (health.isLoading || system.isLoading) return <LoadingState />
  if (health.error) return <ErrorState error={health.error} retry={() => void health.refetch()} />
  return <><PageHeader title="Systemstatus" description="Live-Diagnose für lokale API, Datenbank, Speicher, Prozessspeicher, Plattform und Abhängigkeiten." actions={<Button className="bg-white text-gray-700 ring-1 ring-gray-300 hover:bg-gray-50 dark:bg-gray-900 dark:text-gray-200 dark:ring-gray-700" onClick={() => { void health.refetch(); void system.refetch() }}><RefreshCw className="h-4 w-4" />Aktualisieren</Button>} /><div className="grid grid-cols-2 gap-4 lg:grid-cols-4"><MetricCard label="API" value={<Badge tone={statusTone(health.data!.status)}>{statusLabel(health.data!.status)}</Badge>} /><MetricCard label="Datenbank" value={statusLabel(health.data!.database)} /><MetricCard label="Speicher" value={statusLabel(health.data!.storage)} /><MetricCard label="Betriebszeit" value={`${Math.floor(system.data!.uptime_seconds)} s`} /></div><div className="mt-6 grid gap-6 lg:grid-cols-2"><Panel><h2 className="mb-4 font-semibold">Laufzeitumgebung</h2><dl className="space-y-3 text-sm"><div className="flex justify-between gap-4"><dt className="text-gray-500">Python</dt><dd>{system.data!.python_version}</dd></div><div className="flex justify-between gap-4"><dt className="text-gray-500">Plattform</dt><dd className="text-right">{system.data!.platform}</dd></div><div className="flex justify-between gap-4"><dt className="text-gray-500">Logische CPUs</dt><dd>{system.data!.cpu_count}</dd></div><div className="flex justify-between gap-4"><dt className="text-gray-500">Prozess-RSS</dt><dd>{formatBytes(system.data!.process_memory_bytes)}</dd></div><div className="flex justify-between gap-4"><dt className="text-gray-500">Verfügbarer Speicher</dt><dd>{formatBytes(system.data!.memory_available_bytes)}</dd></div></dl></Panel><Panel><h2 className="mb-4 font-semibold">Kernabhängigkeiten</h2><dl className="space-y-3 text-sm">{Object.entries(system.data!.dependencies).map(([name, version]) => <div key={name} className="flex justify-between"><dt className="font-medium">{name}</dt><dd className="font-mono text-gray-500">{version}</dd></div>)}</dl></Panel></div><Panel className="mt-6 border-emerald-200 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/30"><div className="flex gap-3"><ShieldCheck className="h-6 w-6 text-emerald-600" /><div><h2 className="font-semibold">Offline-Betrieb aktiv</h2><p className="mt-1 text-sm text-gray-600 dark:text-gray-300">Es werden weder API-Schlüssel noch Geocoder, Analyse-Endpunkte oder externe Kartendienste benötigt.</p></div></div></Panel></>
}

export function ArchitecturePage() {
  const layers = [
    { icon: BarChart3, title: 'React-Oberfläche', body: 'Typisierte Query-Adapter, React Flow, TanStack Table, Recharts, barrierearme Themes und lokale Punktkarten.' },
    { icon: Network, title: 'FastAPI-Schnittstelle', body: 'Validierte OpenAPI-Routen, Request-IDs, einheitliche Fehler, lokale CORS-Freigabeliste sowie sichere Header und Downloads.' },
    { icon: Gauge, title: 'Spaltenbasierte Engine', body: 'Auf Polars, PyArrow und DuckDB ausgerichteter Import, typisiertes Schrittregister, Quarantäne und begrenzte Ausführung.' },
    { icon: ShieldCheck, title: 'Fachliche Verarbeitung', body: 'Unicode-/Adressnormalisierung, pyproj-CRS-Transformationen, Haversine, Kandidaten-Blocking und RapidFuzz.' },
    { icon: Database, title: 'Nachweisebene', body: 'SQLAlchemy-/SQLite-Metadaten, unveränderte Uploads sowie Manifeste, Metriken, Berichte, Prüfsummen und Exporte je Lauf.' },
  ]
  return <><PageHeader title="Architektur" description="Ein modularer Monolith für lokale Reproduzierbarkeit, belastbare Nachweise und einen klaren Migrationspfad zu verteilten Workern." /><Panel><div className="mx-auto max-w-4xl space-y-4">{layers.map(({ icon: Icon, title, body }, index) => <div key={title} className="relative flex gap-4 rounded-xl border border-gray-200 p-5 dark:border-gray-700"><div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-200"><Icon className="h-5 w-5" /></div><div><p className="text-xs font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-400">Ebene {index + 1}</p><h2 className="font-semibold">{title}</h2><p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{body}</p></div>{index < layers.length - 1 && <div className="absolute -bottom-5 left-10 h-5 border-l-2 border-dashed border-brand-300" />}</div>)}</div></Panel><div className="mt-6 grid gap-6 md:grid-cols-3"><Panel><FileCheck2 className="mb-3 h-6 w-6 text-brand-600" /><h2 className="font-semibold">Deterministisch</h2><p className="mt-2 text-sm text-gray-500">Datensatz- und Pipeline-Prüfsummen machen jede Laufkonfiguration reproduzierbar.</p></Panel><Panel><ShieldCheck className="mb-3 h-6 w-6 text-brand-600" /><h2 className="font-semibold">Begrenzt</h2><p className="mt-2 text-sm text-gray-500">Fest definierte Operatoren ersetzen beliebigen Code; Pfade und Uploads bleiben im vorgesehenen Bereich.</p></Panel><Panel><Archive className="mb-3 h-6 w-6 text-brand-600" /><h2 className="font-semibold">Auditierbar</h2><p className="mt-2 text-sm text-gray-500">Jeder abgeschlossene Lauf erzeugt Qualitäts-, Leistungs-, Audit-, Manifest- und Prüfsummennachweise.</p></Panel></div></>
}
