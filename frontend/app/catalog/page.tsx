'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { fetchJSON } from '@/lib/api';

type FileRow = {
  id: number;
  file_name: string;
  file_path: string;
  subject_code: string;
  age: string;
  sex: string;
  record_type: string;
  parser_type: string;
};

export default function CatalogPage() {
  const [rows, setRows] = useState<FileRow[]>([]);

  useEffect(() => {
    fetchJSON<FileRow[]>('/api/files').then(setRows).catch(() => setRows([]));
  }, []);

  return (
    <main className="mx-auto max-w-7xl p-6">
      <h1 className="mb-2 text-2xl font-semibold">EEG File Catalog</h1>
      <p className="mb-4 text-sm text-slate-600">Источник данных: локальная библиотека ./eeg (без ручного upload).</p>

      <div className="overflow-auto rounded border bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="p-2 text-left">ID</th>
              <th className="p-2 text-left">file</th>
              <th className="p-2 text-left">subject</th>
              <th className="p-2 text-left">age</th>
              <th className="p-2 text-left">sex</th>
              <th className="p-2 text-left">record</th>
              <th className="p-2 text-left">parser</th>
              <th className="p-2 text-left">open</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t">
                <td className="p-2">{r.id}</td>
                <td className="p-2">{r.file_name}</td>
                <td className="p-2">{r.subject_code}</td>
                <td className="p-2">{r.age}</td>
                <td className="p-2">{r.sex}</td>
                <td className="p-2">{r.record_type}</td>
                <td className="p-2">{r.parser_type}</td>
                <td className="p-2">
                  <Link href={`/viewer/${r.id}`} className="text-blue-600 underline">viewer</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
