'use client';

import { useEffect, useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import { API_BASE, fetchJSON } from '@/lib/api';

type RawPayload = { channels: string[]; times: number[]; stacked: Array<{ channel: string; values: number[] }> };
type AnalysisPayload = {
  psd: { selected_channel: string; by_channel: Record<string, { freqs: number[]; power: number[] }> };
  spectrogram: { times: number[]; frequencies: number[]; power: number[][] };
  metrics: Record<string, number | string>;
  text_description: string;
};

export default function ViewerPage({ params }: { params: { id: string } }) {
  const fileId = params.id;
  const [raw, setRaw] = useState<RawPayload | null>(null);
  const [start, setStart] = useState(0);
  const [end, setEnd] = useState(10);
  const [analysis, setAnalysis] = useState<AnalysisPayload | null>(null);

  useEffect(() => {
    fetchJSON<RawPayload>(`/api/files/${fileId}/raw`).then(setRaw).catch(() => setRaw(null));
  }, [fileId]);

  async function runAnalysis() {
    const payload = await fetchJSON<AnalysisPayload>('/api/analyze-selection', {
      method: 'POST',
      body: JSON.stringify({ file_id: Number(fileId), start_sec: start, end_sec: end, language: 'ru' }),
    });
    setAnalysis(payload);
  }

  const selectedPsd = useMemo(() => {
    if (!analysis) return null;
    const channel = analysis.psd.selected_channel;
    return analysis.psd.by_channel[channel] ?? null;
  }, [analysis]);

  return (
    <main className="mx-auto max-w-7xl p-6">
      <h1 className="mb-2 text-2xl font-semibold">Single-file EEG Viewer #{fileId}</h1>
      <p className="mb-4 text-sm text-slate-600">Backend выполняет весь processing; в браузер отправляется downsampled raw для визуализации.</p>

      <div className="mb-3 flex gap-2">
        <input type="number" className="rounded border px-2 py-1" value={start} onChange={(e) => setStart(Number(e.target.value))} />
        <input type="number" className="rounded border px-2 py-1" value={end} onChange={(e) => setEnd(Number(e.target.value))} />
        <button className="rounded bg-slate-900 px-3 py-1 text-white" onClick={runAnalysis}>Re-analyze interval</button>
        <a className="rounded bg-emerald-700 px-3 py-1 text-white" href={`${API_BASE}/api/export/file/${fileId}?format=csv`} target="_blank">CSV</a>
        <a className="rounded bg-emerald-700 px-3 py-1 text-white" href={`${API_BASE}/api/export/file/${fileId}?format=xlsx`} target="_blank">XLSX</a>
      </div>

      {raw && (
        <Plot
          data={raw.stacked.map((s) => ({ x: raw.times, y: s.values, type: 'scatter', mode: 'lines', name: s.channel }))}
          layout={{ title: 'Raw EEG', height: 320, dragmode: 'zoom' }}
          config={{ responsive: true }}
          className="w-full"
        />
      )}

      {selectedPsd && (
        <Plot
          data={[{ x: selectedPsd.freqs, y: selectedPsd.power, type: 'scatter', mode: 'lines', name: 'PSD' }]}
          layout={{ title: 'PSD', height: 280 }}
          config={{ responsive: true }}
          className="w-full"
        />
      )}

      {analysis && (
        <Plot
          data={[{ x: analysis.spectrogram.times, y: analysis.spectrogram.frequencies, z: analysis.spectrogram.power, type: 'heatmap' }]}
          layout={{ title: 'Spectrogram', height: 300 }}
          config={{ responsive: true }}
          className="w-full"
        />
      )}

      {analysis && (
        <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-4">
          {Object.entries(analysis.metrics).map(([k, v]) => (
            <div key={k} className="rounded border bg-white p-2 text-sm"><b>{k}</b><div>{String(v)}</div></div>
          ))}
        </div>
      )}

      {analysis && (
        <div className="mt-4 rounded border bg-white p-3">
          <h3 className="mb-2 font-semibold">Сгенерированное описание (RU)</h3>
          <p className="text-sm">{analysis.text_description}</p>
        </div>
      )}
    </main>
  );
}
