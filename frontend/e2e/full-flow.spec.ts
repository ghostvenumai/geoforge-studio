import { expect, test, type Page, type TestInfo } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

function stringProperty(value: unknown, key: string): string {
  if (typeof value !== 'object' || value === null || !(key in value)) {
    throw new Error('Response is missing ' + key)
  }
  return String((value as Record<string, unknown>)[key])
}

const pages = [
  ['/', 'Übersicht', 'overview'],
  ['/datasets', 'Datensätze', 'datasets'],
  ['/profiling', 'Datenprofiling', 'profiling'],
  ['/pipelines', 'Pipeline-Builder', 'pipeline-builder'],
  ['/address', 'Adressverarbeitung', 'address-processing'],
  ['/geo', 'Geoverarbeitung', 'geo-processing'],
  ['/duplicates', 'Dublettenprüfung', 'duplicate-review'],
  ['/quality', 'Qualitätsanalyse', 'quality-analysis'],
  ['/performance', 'Performance', 'performance'],
  ['/runs', 'Läufe und Audit', 'runs-audit'],
  ['/exports', 'Exporte', 'exports'],
  ['/health', 'Systemstatus', 'system-health'],
  ['/architecture', 'Architektur', 'architecture'],
] as const

async function assertHealthyPage(page: Page, title: string) {
  await expect(page.getByRole('heading', { level: 1, name: title })).toBeVisible()
  await expect(page.locator('body')).not.toContainText('Diese Ansicht konnte nicht geladen werden')
  const horizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(horizontalOverflow).toBeLessThanOrEqual(1)
}

async function screenshot(page: Page, testInfo: TestInfo, name: string) {
  await page.screenshot({
    path: `../artifacts/ui-review/${name}-${testInfo.project.name}-light.png`,
    fullPage: true,
    animations: 'disabled',
  })
}

test('complete data quality workflow remains auditable after reload', async ({ page }, testInfo) => {
  const consoleErrors: string[] = []
  const failedRequests: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })
  page.on('pageerror', (error) => consoleErrors.push(error.message))
  page.on('requestfailed', (request) => {
    const expectedDownloadHandoff = request.url().includes('/api/artifacts/') && request.url().endsWith('/download') && request.failure()?.errorText.includes('ERR_ABORTED')
    if (!expectedDownloadHandoff) failedRequests.push(request.method() + ' ' + request.url())
  })
  await page.emulateMedia({ reducedMotion: 'reduce', colorScheme: 'light' })

  await page.goto('/datasets')
  await assertHealthyPage(page, 'Datensätze')
  await page.locator('input[type="file"]').setInputFiles('../data/samples/geoforge-demo.csv')
  await expect(page.getByText('geoforge-demo hochgeladen')).toBeVisible({ timeout: 30_000 })
  await expect(page.getByRole('table', { name: 'Importierte Datensätze' })).toContainText('geoforge-demo')

  await page.getByRole('link', { name: 'Datenprofiling' }).click()
  await assertHealthyPage(page, 'Datenprofiling')
  await page.getByRole('button', { name: 'Profiling starten' }).click()
  await expect(page.getByText('Profiling abgeschlossen')).toBeVisible({ timeout: 30_000 })
  await expect(page.getByText('Qualitätswert')).toBeVisible()
  await expect(page.getByRole('table', { name: 'Spaltenprofil' })).toBeVisible()

  await page.getByRole('link', { name: 'Pipeline-Builder' }).click()
  await assertHealthyPage(page, 'Pipeline-Builder')
  const pipelineSelect = page.getByLabel('Pipeline-Version')
  const pipelineValue = await pipelineSelect.locator('option').filter({ hasText: 'Vollständige Datenqualität und Deduplizierung' }).getAttribute('value')
  if (!pipelineValue) throw new Error('Vollständige Datenqualität und Deduplizierung Pipeline fehlt')
  await pipelineSelect.selectOption(pipelineValue)
  await expect(page.getByTestId('rf__node-duplicates')).toBeVisible()
  await page.getByRole('button', { name: 'Validieren', exact: true }).click()
  await expect(page.getByText(/Pipeline gültig/)).toBeVisible()
  const startResponse = page.waitForResponse(
    (response) => response.url().includes('/run') && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Pipeline ausführen' }).click()
  const started: unknown = await (await startResponse).json()
  const runId = stringProperty(started, 'id')
  await expect(page.getByText(/eingereiht/)).toBeVisible()

  await expect
    .poll(
      async () => {
        const response = await page.request.get(`http://127.0.0.1:18080/api/runs/${runId}`)
        const payload: unknown = await response.json()
        return stringProperty(payload, 'status')
      },
      { timeout: 60_000 },
    )
    .toBe('completed')

  await page.goto('/quality')
  await assertHealthyPage(page, 'Qualitätsanalyse')
  await expect(page.getByText('Absolute Änderung')).toBeVisible()
  await expect(page.getByText(/unerklärter Zeilenverlust/)).toBeVisible()

  await page.goto('/duplicates')
  await assertHealthyPage(page, 'Dublettenprüfung')
  await expect(page.getByRole('table', { name: 'Vergleich doppelter Datensätze' })).toBeVisible()
  await page.getByRole('button', { name: 'Annehmen' }).click()
  await expect(page.getByText('Dublettenentscheidung: Angenommen')).toBeVisible()

  await page.goto('/performance')
  await assertHealthyPage(page, 'Performance')
  await expect(page.getByText('Durchsatz', { exact: true })).toBeVisible()
  await expect(page.getByText('Spitzenspeicher', { exact: true })).toBeVisible()

  await page.goto('/exports')
  await assertHealthyPage(page, 'Exporte')
  const parquetRow = page.getByRole('row').filter({ hasText: 'Ergebnis (Parquet)' })
  const downloadPromise = page.waitForEvent('download')
  await parquetRow.getByRole('link', { name: 'Herunterladen' }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe('result.parquet')
  const manifestRow = page.getByRole('row').filter({ hasText: 'Laufmanifest' })
  const manifestUrl = await manifestRow.getByRole('link', { name: 'Herunterladen' }).getAttribute('href')
  expect(manifestUrl).toBeTruthy()
  const manifest = await page.request.get(new URL(manifestUrl!, page.url()).href)
  expect(manifest.ok()).toBeTruthy()
  const manifestPayload: unknown = await manifest.json()
  expect(stringProperty(manifestPayload, 'run_id')).toBe(runId)

  await page.goto('/runs')
  await page.reload()
  await assertHealthyPage(page, 'Läufe und Audit')
  await expect(page.getByRole('table', { name: 'Pipeline-Läufe' })).toContainText(runId.slice(0, 8))

  for (const [path, title, slug] of pages) {
    await page.goto(path)
    await assertHealthyPage(page, title)
    const accessibility = await new AxeBuilder({ page }).include('#main-content').analyze()
    expect(accessibility.violations.filter((item) => ['serious', 'critical'].includes(item.impact ?? '')))
      .toEqual([])
    await screenshot(page, testInfo, slug)
  }

  await page.goto('/')
  await page.getByRole('button', { name: 'Zum dunklen Modus wechseln' }).click()
  await expect(page.locator('html')).toHaveClass(/dark/)
  await page.screenshot({
    path: `../artifacts/ui-review/overview-${testInfo.project.name}-dark.png`,
    fullPage: true,
    animations: 'disabled',
  })
  await page.keyboard.press('Tab')
  await expect(page.locator(':focus')).toBeVisible()

  expect(consoleErrors).toEqual([])
  expect(failedRequests).toEqual([])
})
