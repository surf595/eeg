'use client';

import Plot from 'react-plotly.js';

type Props = {
  times: number[];
  stacked: Array<{ channel: string; values: number[] }>;
};

export function RawViewer({ times, stacked }: Props) {
  return (
    <Plot
      data={stacked.map((s) => ({ x: times, y: s.values, type: 'scatter', mode: 'lines', name: s.channel }))}
      layout={{ title: 'Raw EEG (stacked)', height: 320, dragmode: 'pan' }}
      className="w-full"
      config={{ responsive: true }}
    />
  );
}
