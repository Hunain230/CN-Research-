export default function Sparkline({ values, label, flat = false }: { values: number[]; label: string; flat?: boolean }) {
  return <svg className={`lane-sparkline ${flat ? 'flat' : ''}`} viewBox="0 0 112 28" role="img" aria-label={label}>
    {values.length > 1 ? <SparkPath values={values} /> : <text x="0" y="18">Waiting for records</text>}
  </svg>;
}

function SparkPath({ values }: { values: number[] }) {
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const span = max - min || 1;
  const points = values.map((value, index) => `${(index / Math.max(1, values.length - 1)) * 110},${24 - ((value - min) / span) * 20}`).join(' ');
  return <polyline points={points} />;
}

