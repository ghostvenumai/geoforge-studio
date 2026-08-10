import { expect, test, type Page } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

type Scene = {
  id: string
  order: number
  action: string
  route: string
  planned_duration: number
  narration: string
  overlay: string
}

type Timeline = {
  title: string
  language: string
  width: number
  height: number
  fps: number
  scenes: Scene[]
}

const timeline = JSON.parse(
  fs.readFileSync(path.resolve('../video/script/timeline.json'), 'utf8'),
) as Timeline

function scene(id: string): Scene {
  const selected = timeline.scenes.find((candidate) => candidate.id === id)
  if (!selected) throw new Error(`Timeline-Szene fehlt: ${id}`)
  return selected
}

async function addOverlay(page: Page, selected: Scene) {
  await page.evaluate(
    ({ text, order }) => {
      document.querySelector('[data-video-overlay]')?.remove()
      const overlay = document.createElement('div')
      overlay.dataset.videoOverlay = 'true'
      overlay.setAttribute('aria-hidden', 'true')
      overlay.style.cssText = [
        'position:fixed',
        'left:332px',
        'top:92px',
        'z-index:2147483647',
        'padding:10px 16px',
        'border-radius:8px',
        'background:rgba(15,23,42,.92)',
        'color:#f8fafc',
        'font:600 15px/1.2 Inter,system-ui,sans-serif',
        'letter-spacing:.08em',
        'box-shadow:0 10px 30px rgba(15,23,42,.2)',
      ].join(';')
      overlay.textContent = `${String(order).padStart(2, '0')}  ${text}`
      document.body.appendChild(overlay)
    },
    { text: selected.overlay, order: selected.order },
  )
}

async function holdScene(page: Page, selected: Scene, action: () => Promise<void>) {
  const started = Date.now()
  await action()
  if (!page.isClosed() && !page.url().startsWith('about:')) await addOverlay(page, selected)
  const remaining = selected.planned_duration * 1_000 - (Date.now() - started)
  if (remaining > 0) await page.waitForTimeout(remaining)
}

async function titleCard(page: Page, title: string, subtitle: string) {
  await page.setContent(`
    <!doctype html><html lang="de"><head><meta charset="utf-8"><style>
      *{box-sizing:border-box}body{margin:0;width:100vw;height:100vh;display:grid;place-items:center;
      background:#0f172a;color:#f8fafc;font-family:Inter,system-ui,sans-serif}
      main{text-align:center}.mark{display:inline-grid;place-items:center;width:78px;height:78px;border-radius:20px;
      background:#0f9f8f;font-size:30px;font-weight:800;margin-bottom:28px}
      h1{font-size:58px;letter-spacing:-.03em;margin:0 0 18px}p{font-size:23px;color:#94a3b8;
      letter-spacing:.08em;margin:0;text-transform:uppercase}
    </style></head><body><main><div class="mark">GF</div><h1>${title}</h1><p>${subtitle}</p></main></body></html>
  `)
}

function property(value: unknown, key: string): string {
  if (typeof value !== 'object' || value === null || !(key in value)) {
    throw new Error(`API-Antwort enthält ${key} nicht`)
  }
  return String((value as Record<string, unknown>)[key])
}

test('records the deterministic GeoForge product demo', async ({ page }) => {
  const recording = page.video()
  await page.emulateMedia({ reducedMotion: 'reduce', colorScheme: 'light' })

  await holdScene(page, scene('intro'), async () => {
    await titleCard(page, 'GeoForge Studio', 'Address · Geo · Data Transformation')
  })

  await holdScene(page, scene('overview'), async () => {
    await page.goto('/')
    await expect(page.getByRole('heading', { level: 1, name: 'Übersicht' })).toBeVisible()
  })

  await holdScene(page, scene('import'), async () => {
    await page.goto('/datasets')
    const marketingDemo = page.locator('article').filter({
      has: page.getByRole('heading', { level: 3, name: 'Marketing & CRM' }),
    })
    await expect(marketingDemo).toBeVisible()
    await marketingDemo.getByRole('button', { name: 'Demo laden' }).click()
    await expect(page.getByText('geoforge-demo-marketing als Demo geladen')).toBeVisible()
    await expect(page.getByRole('table', { name: 'Importierte Datensätze' })).toContainText(
      'geoforge-demo-marketing',
    )
  })

  await holdScene(page, scene('profiling'), async () => {
    await page.goto('/profiling')
    await page.getByRole('button', { name: 'Profiling starten' }).click()
    await expect(page.getByText('Profiling abgeschlossen')).toBeVisible()
    await expect(page.getByRole('table', { name: 'Spaltenprofil' })).toBeVisible()
  })

  let runId = ''
  await holdScene(page, scene('pipeline'), async () => {
    await page.goto('/pipelines')
    const pipelineSelect = page.getByLabel('Pipeline-Version')
    const option = pipelineSelect
      .locator('option')
      .filter({ hasText: 'Vollständige Datenqualität und Deduplizierung' })
    const pipelineId = await option.getAttribute('value')
    if (!pipelineId) throw new Error('Demo-Pipeline fehlt')
    await pipelineSelect.selectOption(pipelineId)
    await expect(page.getByTestId('rf__node-duplicates')).toBeVisible()
    await page.getByRole('button', { name: 'Validieren', exact: true }).click()
    await expect(page.getByText(/Pipeline gültig/)).toBeVisible()
    const responsePromise = page.waitForResponse(
      (response) => response.url().endsWith('/run') && response.request().method() === 'POST',
    )
    await page.getByRole('button', { name: 'Pipeline ausführen' }).click()
    runId = property(await (await responsePromise).json(), 'id')
    await expect
      .poll(
        async () => {
          const response = await page.request.get(`http://127.0.0.1:18082/api/runs/${runId}`)
          return property(await response.json(), 'status')
        },
        { timeout: 60_000 },
      )
      .toBe('completed')
  })

  await holdScene(page, scene('quality'), async () => {
    await page.goto('/quality')
    await expect(page.getByRole('heading', { level: 1, name: 'Qualitätsanalyse' })).toBeVisible()
    await expect(page.getByText('Absolute Änderung')).toBeVisible()
  })

  await holdScene(page, scene('duplicates'), async () => {
    await page.goto('/duplicates')
    await expect(page.getByRole('heading', { level: 1, name: 'Dublettenprüfung' })).toBeVisible()
    await expect(page.getByRole('table', { name: 'Vergleich doppelter Datensätze' })).toBeVisible()
  })

  await holdScene(page, scene('performance'), async () => {
    await page.goto('/performance')
    await expect(page.getByText('Durchsatz', { exact: true })).toBeVisible()
    await expect(page.getByText('Spitzenspeicher', { exact: true })).toBeVisible()
  })

  await holdScene(page, scene('exports'), async () => {
    await page.goto('/exports')
    await expect(page.getByRole('row').filter({ hasText: 'Ergebnis (Parquet)' })).toBeVisible()
    await expect(page.getByRole('row').filter({ hasText: 'Laufmanifest' })).toBeVisible()
  })

  await holdScene(page, scene('architecture'), async () => {
    await page.goto('/architecture')
    await expect(page.getByRole('heading', { level: 1, name: 'Architektur' })).toBeVisible()
  })

  await holdScene(page, scene('outro'), async () => {
    await titleCard(page, 'GeoForge Studio', 'Python · Data Engineering · Automation')
  })

  await page.close()
  if (!recording) throw new Error('Playwright-Videoaufnahme ist nicht aktiviert')
  await recording.saveAs('../video/tmp/capture.webm')
  expect(runId).not.toBe('')
})
