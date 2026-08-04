import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState, type PropsWithChildren } from 'react'
import { CheckCircle2, X } from 'lucide-react'
import { ThemeContext, ToastContext, type Theme } from './context-hooks'

interface Toast { id: number; message: string }
export function AppProviders({ children }: PropsWithChildren) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 10_000, retry: false }, mutations: { retry: 0 } },
  }))
  const [theme, setTheme] = useState<Theme>(() => (localStorage.getItem('geoforge-theme') === 'dark' ? 'dark' : 'light'))
  const [toasts, setToasts] = useState<Toast[]>([])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('geoforge-theme', theme)
  }, [theme])

  const notify = useCallback((message: string) => {
    const id = Date.now()
    setToasts((current) => [...current, { id, message }])
    window.setTimeout(() => setToasts((current) => current.filter((toast) => toast.id !== id)), 4000)
  }, [])

  const themeValue = useMemo(() => ({ theme, toggle: () => setTheme((current) => (current === 'dark' ? 'light' : 'dark')) }), [theme])
  const toastValue = useMemo(() => ({ notify }), [notify])

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeContext.Provider value={themeValue}>
        <ToastContext.Provider value={toastValue}>
          {children}
          <div className="fixed bottom-4 right-4 z-50 flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2" aria-live="polite">
            {toasts.map((toast) => (
              <div key={toast.id} className="flex items-center gap-3 rounded-lg border border-emerald-200 bg-white p-3 text-sm shadow-lg dark:border-emerald-900 dark:bg-gray-900">
                <CheckCircle2 className="h-5 w-5 text-emerald-600" aria-hidden="true" />
                <span className="flex-1">{toast.message}</span>
                <button aria-label="Benachrichtigung schließen" onClick={() => setToasts((current) => current.filter((item) => item.id !== toast.id))}><X className="h-4 w-4" /></button>
              </div>
            ))}
          </div>
        </ToastContext.Provider>
      </ThemeContext.Provider>
    </QueryClientProvider>
  )
}
