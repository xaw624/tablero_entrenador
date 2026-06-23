// Gráfica de línea SVG responsive. Grafica points[].num contra el orden de fechas.
export default function Chart({ points, test }) {
  const W = 320, H = 180, PAD = 28;
  if (!points || points.length === 0) {
    return <div className="empty">Sin datos para graficar.</div>;
  }

  const nums = points.map((p) => p.num);
  let min = Math.min(...nums);
  let max = Math.max(...nums);
  if (min === max) { min -= 1; max += 1; }
  const range = max - min;

  const n = points.length;
  const xOf = (i) => PAD + (n === 1 ? (W - 2 * PAD) / 2 : (i * (W - 2 * PAD)) / (n - 1));
  const yOf = (v) => H - PAD - ((v - min) / range) * (H - 2 * PAD);

  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${xOf(i)},${yOf(p.num)}`).join(" ");

  const fmtDate = (ms) => {
    const d = new Date(ms);
    return `${d.getDate()}/${d.getMonth() + 1}`;
  };

  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Gráfica de progreso">
      {/* ejes */}
      <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="var(--line)" />
      <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="var(--line)" />
      {/* línea */}
      <path d={path} fill="none" stroke="var(--brick)" strokeWidth="2" />
      {/* puntos */}
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={xOf(i)} cy={yOf(p.num)} r="3.5" fill="var(--brick)" />
          <text x={xOf(i)} y={H - PAD + 14} fontSize="9" fill="var(--ink-faint)" textAnchor="middle">
            {fmtDate(p.date)}
          </text>
        </g>
      ))}
      {/* etiquetas min/max en Y */}
      <text x={PAD - 4} y={PAD + 4} fontSize="9" fill="var(--ink-faint)" textAnchor="end">{max}</text>
      <text x={PAD - 4} y={H - PAD} fontSize="9" fill="var(--ink-faint)" textAnchor="end">{min}</text>
    </svg>
  );
}
