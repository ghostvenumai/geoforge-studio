import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { Layout } from './components/layout'
import { AppProviders } from './components/providers'
import {
  AddressPage,
  ArchitecturePage,
  DatasetsPage,
  DuplicatesPage,
  ExportsPage,
  GeoPage,
  HealthPage,
  OverviewPage,
  PerformancePage,
  PipelineBuilderPage,
  ProfilingPage,
  QualityPage,
  RunsPage,
} from './pages'
import './index.css'
import '@xyflow/react/dist/style.css'

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <OverviewPage /> },
      { path: 'datasets', element: <DatasetsPage /> },
      { path: 'profiling', element: <ProfilingPage /> },
      { path: 'pipelines', element: <PipelineBuilderPage /> },
      { path: 'address', element: <AddressPage /> },
      { path: 'geo', element: <GeoPage /> },
      { path: 'duplicates', element: <DuplicatesPage /> },
      { path: 'quality', element: <QualityPage /> },
      { path: 'performance', element: <PerformancePage /> },
      { path: 'runs', element: <RunsPage /> },
      { path: 'exports', element: <ExportsPage /> },
      { path: 'health', element: <HealthPage /> },
      { path: 'architecture', element: <ArchitecturePage /> },
    ],
  },
])

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><AppProviders><RouterProvider router={router} /></AppProviders></React.StrictMode>,
)
