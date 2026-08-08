
"use client";

import type { ReactNode } from "react";

interface TableProps {
  headers: string[];
  rows: ReactNode[][];
  onRowClick?: (rowIndex: number, event: React.MouseEvent) => void;
  isRowClickable?: (rowIndex: number) => boolean;
}

export default function Table({ headers, rows, onRowClick, isRowClickable }: TableProps) {
  const safeRows = rows ?? [];
  const safeHeaders = headers ?? [];

  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-card">
      <table className="w-full text-sm text-left border-collapse">
        <thead className="bg-subtle/60">
          <tr className="border-b border-border">
            {safeHeaders.map((header, i) => (
              <th
                key={i}
                className="px-4 py-2.5 font-semibold text-xs uppercase tracking-wider text-muted-foreground"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {safeRows.length === 0 ? (
            <tr>
              <td
                colSpan={safeHeaders.length || 1}
                className="px-4 py-8 text-center text-muted-foreground italic"
              >
                No data
              </td>
            </tr>
          ) : (
            safeRows.map((row, i) => {
              const clickable = isRowClickable ? isRowClickable(i) : !!onRowClick;
              return (
                <tr
                  key={i}
                  onClick={clickable && onRowClick ? (e) => onRowClick(i, e) : undefined}
                  className={
                    "border-b border-border/60 last:border-b-0 transition-colors " +
                    (clickable
                      ? "cursor-pointer hover:bg-primary/5 active:bg-primary/10"
                      : "hover:bg-subtle/70")
                  }
                >
                  {row.map((cell, j) => (
                    <td key={j} className="px-4 py-2.5 text-foreground">
                      {cell}
                    </td>
                  ))}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
