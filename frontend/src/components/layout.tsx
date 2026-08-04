import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  Activity,
  Archive,
  BarChart3,
  Boxes,
  Braces,
  Database,
  FileSearch,
  Gauge,
  GitCompareArrows,
  HeartPulse,
  MapPinned,
  Menu,
  Moon,
  Network,
  Sun,
  X,
} from 'lucide-react'
import { cn } from '../lib/utils'
import { useTheme } from './context-hooks'

const navigation = [
  { label: 'Übersicht', path: '/', icon: BarChart3 },
  { label: 'Datensätze', path: '/datasets', icon: Database },
  { label: 'Datenprofiling', path: '/profiling', icon: FileSearch },
  { label: 'Pipeline-Builder', path: '/pipelines', icon: Network },
  { label: 'Adressverarbeitung', path: '/address', icon: Braces },
  { label: 'Geoverarbeitung', path: '/geo', icon: MapPinned },
  { label: 'Dublettenprüfung', path: '/duplicates', icon: GitCompareArrows },
  { label: 'Qualitätsanalyse', path: '/quality', icon: Gauge },
  { label: 'Performance', path: '/performance', icon: Activity },
  { label: 'Läufe und Audit', path: '/runs', icon: Boxes },
  { label: 'Exporte', path: '/exports', icon: Archive },
  { label: 'Systemstatus', path: '/health', icon: HeartPulse },
  { label: 'Architektur', path: '/architecture', icon: Network },
]

export function Layout() {
  const [open, setOpen] = useState(false)
  const { theme, toggle } = useTheme()
  return (
    <div className="min-h-screen bg-canvas text-gray-900 dark:bg-gray-950 dark:text-gray-100">
      <a href="#main-content" className="sr-only z-[100] rounded bg-white p-3 focus:not-sr-only focus:fixed focus:left-3 focus:top-3">Zum Hauptinhalt springen</a>
      {open && <button className="fixed inset-0 z-30 bg-gray-950/50 lg:hidden" aria-label="Navigationsbereich schließen" onClick={() => setOpen(false)} />}
      <aside className={cn('fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-gray-800 bg-ink text-gray-300 transition-transform lg:translate-x-0', open ? 'translate-x-0' : '-translate-x-full')}>
        <div className="flex h-20 items-center gap-3 border-b border-gray-800 px-5">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-brand-500 text-lg font-black text-white">GF</div>
          <div><p className="font-bold tracking-wide text-white">GEOFORGE</p><p className="text-xs text-gray-400">STUDIO FÜR DATENTRANSFORMATION</p></div>
          <button className="ml-auto rounded p-2 lg:hidden" aria-label="Navigation schließen" onClick={() => setOpen(false)}><X className="h-5 w-5" /></button>
        </div>
        <nav className="flex-1 overflow-y-auto p-3" aria-label="Hauptnavigation">
          {navigation.map(({ label, path, icon: Icon }) => (
            <NavLink key={path} to={path} end={path === '/'} onClick={() => setOpen(false)} className={({ isActive }) => cn('mb-1 flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm font-medium transition hover:bg-gray-800 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500', isActive && 'bg-brand-600 text-white')}>
              <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />{label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-gray-800 p-4 text-xs text-gray-500">Offline-fähig · Keine externen Karten<br />Version 0.1.0</div>
      </aside>
      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 flex h-16 items-center border-b border-gray-200 bg-white/95 px-4 backdrop-blur dark:border-gray-800 dark:bg-gray-950/95 sm:px-6">
          <button className="rounded-lg p-2 hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-brand-500 lg:hidden" aria-label="Navigation öffnen" onClick={() => setOpen(true)}><Menu className="h-5 w-5" /></button>
          <div className="ml-auto flex items-center gap-3">
            <span className="hidden items-center gap-2 text-xs text-gray-500 sm:flex"><span className="h-2 w-2 rounded-full bg-emerald-500" />Lokaler Arbeitsbereich</span>
            <button className="rounded-lg border border-gray-200 p-2 hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:border-gray-800 dark:hover:bg-gray-800" aria-label={`Zum ${theme === 'dark' ? 'hellen' : 'dunklen'} Modus wechseln`} onClick={toggle}>
              {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
          </div>
        </header>
        <main id="main-content" className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8"><Outlet /></main>
      </div>
    </div>
  )
}
