import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="mx-auto max-w-5xl p-6">
      <h1 className="mb-2 text-2xl font-semibold">EEG MVP Phase 1</h1>
      <p className="mb-4 text-sm text-slate-600">Каталог и single-file viewer работают с локальной библиотекой ./eeg.</p>
      <Link href="/catalog" className="rounded bg-slate-900 px-4 py-2 text-white">Open file catalog</Link>
'use client';

import { useEffect, useState } from 'react';
import { fetchJSON } from '@/lib/api';
import { RawViewer } from '@/components/RawViewer';

type FileRow = { id: number; file_name: string; subject_code: string; record_type: string };
type RawPayload = { times: number[]; stacked: Array<{ channel: string; values: number[] }> };

export default function HomePage() {
  const [files, setFiles] = useState<FileRow[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [raw, setRaw] = useState<RawPayload | null>(null);

  useEffect(() => {
    fetchJSON<FileRow[]>('/api/files').then((rows) => {
      setFiles(rows);
      setSelectedId(rows[0]?.id ?? null);
    });
  }, []);

  async function loadRaw() {
    if (!selectedId) return;
    const payload = await fetchJSON<RawPayload>(`/api/files/${selectedId}/raw`);
    setRaw(payload);
  }

  return (
    <main className="mx-auto max-w-7xl p-6">
      <h1 className="mb-2 text-2xl font-semibold">EEG Research UI (Next.js + TS + Tailwind + Plotly)</h1>
      <p className="mb-4 text-sm text-slate-600">Не диагностическая система. Исследовательский интерфейс.</p>

      <div className="mb-4 flex items-center gap-2">
        <select
          className="rounded border bg-white px-3 py-2"
          value={selectedId ?? ''}
          onChange={(e) => setSelectedId(Number(e.target.value))}
        >
          {files.map((f) => (
            <option key={f.id} value={f.id}>{`${f.id} | ${f.file_name} | ${f.subject_code} | ${f.record_type}`}</option>
          ))}
        </select>
        <button className="rounded bg-slate-900 px-3 py-2 text-white" onClick={loadRaw}>Load raw</button>
      </div>

      {raw ? <RawViewer times={raw.times} stacked={raw.stacked} /> : <div className="text-sm text-slate-500">Выберите файл и нажмите Load raw</div>}
    </main>
  );
}
