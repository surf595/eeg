import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="mx-auto max-w-5xl p-6">
      <h1 className="mb-2 text-2xl font-semibold">EEG MVP Phase 1</h1>
      <p className="mb-4 text-sm text-slate-600">Каталог и single-file viewer работают с локальной библиотекой ./eeg.</p>
      <Link href="/catalog" className="rounded bg-slate-900 px-4 py-2 text-white">Open file catalog</Link>
    </main>
  );
}
