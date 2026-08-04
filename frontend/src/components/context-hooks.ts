import { createContext, useContext } from 'react'

export type Theme = 'light' | 'dark'

export const ThemeContext = createContext<{ theme: Theme; toggle: () => void } | undefined>(undefined)
export const ToastContext = createContext<{ notify: (message: string) => void } | undefined>(undefined)

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) throw new Error('useTheme must be used within AppProviders')
  return context
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within AppProviders')
  return context
}
