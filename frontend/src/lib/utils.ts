import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

export function formatBytes(value: number): string {
  if (!value) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1)
  return `${(value / 1024 ** index).toFixed(index ? 1 : 0)} ${units[index]}`
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat('de-DE', { maximumFractionDigits: 1 }).format(value)
}

export function shortId(value: string): string {
  return value.slice(0, 8)
}

export function formatDate(value: string | null): string {
  return value ? new Intl.DateTimeFormat('de-DE', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—'
}


export function displayValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') return String(value)
  if (value instanceof Date) return value.toISOString()
  try {
    return JSON.stringify(value) ?? '—'
  } catch {
    return '[Wert nicht verfügbar]'
  }
}
