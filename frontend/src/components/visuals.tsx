import { useMemo } from 'react'
import { displayValue } from '../lib/utils'
import { Panel } from './ui'

export function LocalPointMap({ records, latitude = 'latitude_validated', longitude = 'longitude_validated' }: { records: Array<Record<string, unknown>>; latitude?: string; longitude?: string }) {
  const points = useMemo(
    () => records.map((record) => ({ lat: Number(record[latitude] ?? record.latitude), lon: Number(record[longitude] ?? record.longitude) })).filter((point) => Number.isFinite(point.lat) && Number.isFinite(point.lon) && Math.abs(point.lat) <= 90 && Math.abs(point.lon) <= 180),
    [records, latitude, longitude],
  )
  return (
    <Panel>
      <div className="mb-3 flex items-center justify-between"><h2 className="font-semibold">Lokale Koordinatenansicht</h2><span className="text-xs text-gray-500">Kein externer Kartendienst</span></div>
      <svg viewBox="0 0 600 320" className="h-auto w-full rounded-lg border border-gray-200 bg-slate-50 dark:border-gray-700 dark:bg-gray-950" role="img" aria-label={`Punktkarte mit ${points.length} gültigen Koordinatenpunkten`}>
        <defs><pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse"><path d="M 50 0 L 0 0 0 50" fill="none" stroke="currentColor" strokeOpacity=".08" /></pattern></defs>
        <rect width="600" height="320" fill="url(#grid)" />
        <path d="M120 250 C170 190 170 100 250 85 C330 55 420 100 475 60 L520 210 C430 250 315 285 220 260 Z" fill="currentColor" className="text-brand-100 dark:text-brand-950" stroke="currentColor" strokeOpacity=".25" />
        {points.map((point, index) => <circle key={`${point.lat}-${point.lon}-${index}`} cx={((point.lon + 180) / 360) * 600} cy={((90 - point.lat) / 180) * 320} r="4" className="fill-brand-600" opacity=".8"><title>{point.lat.toFixed(5)}, {point.lon.toFixed(5)}</title></circle>)}
      </svg>
    </Panel>
  )
}

export function JsonPreview({ records, empty = 'Keine Vorschauzeilen verfügbar.' }: { records: Array<Record<string, unknown>>; empty?: string }) {
  if (!records.length) return <p className="py-10 text-center text-sm text-gray-500">{empty}</p>
  const columns = Object.keys(records[0] ?? {}).slice(0, 12)
  return (
    <div className="focus-ring overflow-x-auto" role="region" aria-label="Scrollbare Datenvorschau" tabIndex={0}><table className="data-table" aria-label="Datenvorschau"><thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{records.slice(0, 10).map((record, index) => <tr key={index}>{columns.map((column) => <td key={column} className="max-w-48 truncate" title={displayValue(record[column])}>{displayValue(record[column])}</td>)}</tr>)}</tbody></table></div>
  )
}
