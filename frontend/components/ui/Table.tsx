"use client";

import type { ReactNode } from "react";

interface TableProps {
  headers: string[];
  rows: ReactNode[][];
}

export default function Table({ headers, rows }: TableProps) {
  const safeRows = rows ?? [];

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead>
          <tr className="border-b border-gray-200 dark:border-neutral-700">
            {(headers ?? []).map((header, i) => (
              <th key={i} className="px-3 py-2 font-medium text-gray-700 dark:text-gray-300">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {safeRows.length === 0 ? (
            <tr>
              <td colSpan={headers?.length ?? 1} className="px-3 py-4 text-center text-gray-400">
                No data
              </td>
            </tr>
          ) : (
            safeRows.map((row, i) => (
              <tr key={i} className="border-b border-gray-100 dark:border-neutral-800">
                {row.map((cell, j) => (
                  <td key={j} className="px-3 py-2 text-gray-900 dark:text-gray-100">
                    {cell}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}