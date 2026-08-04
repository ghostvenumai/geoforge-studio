import type { ButtonHTMLAttributes, HTMLAttributes, PropsWithChildren, ReactNode } from 'react'
import { AlertTriangle, Inbox, LoaderCircle } from 'lucide-react'
import { cn } from '../lib/utils'

export function Button({ className, type = 'button', ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type={type}
      className={cn(
        'inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:ring-offset-gray-950',
        className,
      )}
      {...props}
    />
  )
}

export function Panel({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('rounded-xl border border-gray-200 bg-white p-5 shadow-panel dark:border-gray-800 dark:bg-gray-900', className)} {...props} />
}

export function Badge({ children, tone = 'neutral' }: PropsWithChildren<{ tone?: 'neutral' | 'good' | 'warn' | 'bad' | 'info' }>) {
  const colors = {
    neutral: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    good: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
    warn: 'bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
    bad: 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300',
    info: 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
  }
  return <span className={cn('inline-flex rounded-full px-2.5 py-1 text-xs font-semibold', colors[tone])}>{children}</span>
}

export function PageHeader({ title, description, actions }: { title: string; description: string; actions?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-gray-950 dark:text-white">{title}</h1>
        <p className="mt-1 max-w-3xl text-sm text-gray-600 dark:text-gray-400">{description}</p>
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  )
}

export function MetricCard({ label, value, detail, icon }: { label: string; value: ReactNode; detail?: string; icon?: ReactNode }) {
  return (
    <Panel className="min-w-0">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">{label}</p>
          <p className="mt-2 truncate text-2xl font-bold text-gray-950 dark:text-white">{value}</p>
          {detail && <p className="mt-1 truncate text-xs text-gray-500 dark:text-gray-400">{detail}</p>}
        </div>
        {icon && <span className="rounded-lg bg-brand-50 p-2 text-brand-700 dark:bg-brand-950 dark:text-brand-100">{icon}</span>}
      </div>
    </Panel>
  )
}

export function LoadingState({ label = 'Daten werden geladen' }: { label?: string }) {
  return (
    <div className="flex min-h-48 items-center justify-center gap-3 text-sm text-gray-500" role="status">
      <LoaderCircle className="h-5 w-5 animate-spin motion-reduce:animate-none" aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}

export function SkeletonGrid() {
  return (
    <div className="grid animate-pulse grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Dashboard wird geladen" role="status">
      {Array.from({ length: 8 }, (_, index) => <div key={index} className="h-28 rounded-xl bg-gray-200 dark:bg-gray-800" />)}
    </div>
  )
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <Panel className="flex min-h-56 flex-col items-center justify-center text-center">
      <Inbox className="mb-3 h-8 w-8 text-gray-400" aria-hidden="true" />
      <h2 className="font-semibold text-gray-900 dark:text-white">{title}</h2>
      <p className="mt-1 max-w-md text-sm text-gray-500">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </Panel>
  )
}

export function ErrorState({ error, retry }: { error: Error; retry?: () => void }) {
  return (
    <Panel className="border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/40" role="alert">
      <div className="flex gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 text-red-600" aria-hidden="true" />
        <div>
          <h2 className="font-semibold text-red-900 dark:text-red-200">Diese Ansicht konnte nicht geladen werden</h2>
          <p className="mt-1 text-sm text-red-700 dark:text-red-300">{error.message}</p>
          {retry && <Button className="mt-3 bg-red-700 hover:bg-red-800" onClick={retry}>Erneut versuchen</Button>}
        </div>
      </div>
    </Panel>
  )
}

export function TableFrame({ children, ...props }: PropsWithChildren<HTMLAttributes<HTMLDivElement>>) {
  return <div tabIndex={0} role="region" className="focus-ring overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-panel dark:border-gray-800 dark:bg-gray-900" {...props}>{children}</div>
}
