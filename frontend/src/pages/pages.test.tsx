import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AppProviders } from '../components/providers'
import { DatasetsPage, OverviewPage, PipelineBuilderPage, QualityPage } from '.'

const emptyList = { items: [], total: 0 }
const overview = {
  summary: {
    datasets: 2, processed_datasets: 1, active_runs: 0, completed_runs: 1,
    average_quality_score: 94.5, duplicates: 3, quarantined_rows: 2,
    latest_throughput: 1200, latest_runtime: 0.5, latest_peak_memory: 1024,
    latest_input_size: 2000, latest_output_size: 1000,
  },
  quality: [{ run_id: 'abc123456', before: 70, after: 94.5 }],
  step_durations: [{ run_id: 'abc123456', step: 'Normalize', duration: 0.2 }],
  throughput: [{ run_id: 'abc123456', created_at: '2026-01-01', rows_per_second: 1200 }],
  dataset_volumes: [{ dataset_id: 'dataset', name: 'Demo', rows: 100 }],
  run_status: { completed: 1 },
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), { status, headers: { 'Content-Type': 'application/json' } })
}

function renderPage(page: React.ReactNode) {
  return render(<AppProviders><MemoryRouter>{page}</MemoryRouter></AppProviders>)
}

beforeEach(() => { localStorage.clear(); vi.restoreAllMocks() })

test('overview renders measured backend metrics', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
    if (url.endsWith('/overview')) return Promise.resolve(jsonResponse(overview))
    return Promise.resolve(jsonResponse({ status: 'Fehlerfrei', version: '0.1.0', database: 'ready', storage: 'ready', timestamp: '2026-01-01' }))
  })
  renderPage(<OverviewPage />)
  expect(await screen.findByText('94.5/100')).toBeVisible()
  expect(screen.getByText('1.200 r/s')).toBeVisible()
  expect(screen.getByText('Fehlerfrei')).toBeVisible()
})

test('dataset page exposes upload and empty state', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(emptyList))
  renderPage(<DatasetsPage />)
  expect(await screen.findByText('Noch keine Datensätze')).toBeVisible()
  expect(screen.getByLabelText(/CSV-, JSON-/i)).toHaveAttribute('accept', expect.stringContaining('.parquet'))
})

test('pipeline builder lists safe step palette', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(emptyList))
  renderPage(<PipelineBuilderPage />)
  expect(await screen.findByText('Schrittauswahl')).toBeVisible()
  expect(screen.getByRole('button', { name: /Adresse normalisieren/i })).toBeVisible()
  expect(screen.getByRole('button', { name: /Dubletten erkennen/i })).toBeVisible()
  expect(screen.getByRole('button', { name: /YAML-Ansicht/i })).toBeVisible()
})

test('quality page handles absent runs', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(emptyList))
  renderPage(<QualityPage />)
  expect(await screen.findByText('Kein Qualitätsvergleich')).toBeVisible()
})

test('request failures show a useful error state', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ error: { code: 'http_500', message: 'Synthetic backend failure', request_id: 'req-test' } }, 500))
  renderPage(<OverviewPage />)
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Synthetic backend failure'), { timeout: 5000 })
})
