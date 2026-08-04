import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AppProviders } from './providers'
import { Layout } from './layout'
import { EmptyState, ErrorState, LoadingState, MetricCard } from './ui'

function renderLayout() {
  return render(
    <AppProviders>
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<h1>Dashboard content</h1>} />
            <Route path="datasets" element={<h1>Dataset content</h1>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </AppProviders>,
  )
}

describe('shared interface', () => {
  test('renders semantic loading, empty, and error states', () => {
    const { rerender } = render(<LoadingState label="Loading records" />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading records')
    rerender(<EmptyState title="Nothing here" description="Import a file." />)
    expect(screen.getByText('Nothing here')).toBeVisible()
    rerender(<ErrorState error={new Error('Backend unavailable')} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Backend unavailable')
  })

  test('renders metric content', () => {
    render(<MetricCard label="Quality" value="98.5/100" detail="Measured after run" />)
    expect(screen.getByText('98.5/100')).toBeVisible()
    expect(screen.getByText('Measured after run')).toBeVisible()
  })

  test('provides all navigation and changes routes', () => {
    renderLayout()
    expect(screen.getByRole('navigation', { name: 'Hauptnavigation' })).toBeInTheDocument()
    expect(screen.getAllByRole('link')).toHaveLength(14)
    fireEvent.click(screen.getByRole('link', { name: 'Datensätze' }))
    expect(screen.getByRole('heading', { name: 'Dataset content' })).toBeVisible()
  })

  test('persists dark mode selection', () => {
    renderLayout()
    fireEvent.click(screen.getByRole('button', { name: 'Zum dunklen Modus wechseln' }))
    expect(document.documentElement).toHaveClass('dark')
    expect(localStorage.getItem('geoforge-theme')).toBe('dark')
  })
})
