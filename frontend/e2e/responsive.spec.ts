import { expect, test } from '@playwright/test'

const routes = [
  ['/', 'Übersicht'],
  ['/datasets', 'Datensätze'],
  ['/pipelines', 'Pipeline-Builder'],
  ['/duplicates', 'Dublettenprüfung'],
  ['/health', 'Systemstatus'],
] as const

test('tablet and mobile layouts remain navigable without page overflow', async ({ page }, testInfo) => {
  const consoleErrors: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })
  page.on('pageerror', (error) => consoleErrors.push(error.message))
  await page.emulateMedia({ reducedMotion: 'reduce' })

  for (const [path, title] of routes) {
    await page.goto(path)
    await expect(page.getByRole('heading', { level: 1, name: title })).toBeVisible()
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      ),
    ).toBeLessThanOrEqual(1)
  }

  const menuButton = page.getByRole('button', { name: 'Navigation öffnen' })
  if (await menuButton.isVisible()) await menuButton.click()
  await expect(page.getByRole('navigation', { name: 'Hauptnavigation' })).toBeVisible()
  await page.getByRole('link', { name: 'Übersicht' }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'Übersicht' })).toBeVisible()
  await page.screenshot({
    path: `../artifacts/ui-review/responsive-${testInfo.project.name}.png`,
    fullPage: true,
    animations: 'disabled',
  })
  expect(consoleErrors).toEqual([])
})
