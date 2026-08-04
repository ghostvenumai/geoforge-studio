import { flexRender, getCoreRowModel, useReactTable, type ColumnDef } from '@tanstack/react-table'
import { TableFrame } from './ui'

export function DataTable<T>({ data, columns, label }: { data: T[]; columns: Array<ColumnDef<T>>; label: string }) {
  const table = useReactTable({ data, columns, getCoreRowModel: getCoreRowModel() })
  return (
    <TableFrame aria-label={label + ' scroll area'}>
      <table className="data-table" aria-label={label}>
        <thead>
          {table.getHeaderGroups().map((group) => (
            <tr key={group.id}>{group.headers.map((header) => <th key={header.id} scope="col">{header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}</th>)}</tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">{row.getVisibleCells().map((cell) => <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </TableFrame>
  )
}
