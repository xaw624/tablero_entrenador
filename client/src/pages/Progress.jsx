import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useStore } from "../state/store.jsx";
import Chart from "../components/Chart.jsx";
import { computeDelta, fmtShortDate, formatDelta, formatValue } from "../lib/format.js";

export default function Progress() {
  const { athletes, tests, sessions } = useStore();
  const activeAthletes = athletes.filter((a) => !a.archived);
  const activeTests = tests.filter((t) => !t.archived);

  const [athleteId, setAthleteId] = useState(() => activeAthletes[0]?.id || "");
  const [testId, setTestId] = useState(() => activeTests[0]?.id || "");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!athleteId || !testId) return;
    setLoading(true);
    api.get(`/api/progress?athlete_id=${athleteId}&test_id=${testId}`)
      .then(setData)
      .finally(() => setLoading(false));
  }, [athleteId, testId]);

  if (sessions.length === 0) {
    return (
      <div className="page">
        <div className="empty">
          Aún no hay pruebas guardadas.<br />
          <Link to="/prueba">Registrar una prueba →</Link>
        </div>
      </div>
    );
  }

  const points = data?.points || [];
  const test = data?.test;
  let trend = null;
  if (test && points.length >= 2) {
    const first = points[0].num, last = points[points.length - 1].num;
    if (first !== last) {
      const improved = test.better === "high" ? last > first : last < first;
      trend = improved ? "▲ mejora" : "▼ baja";
    } else trend = "= igual";
  }

  return (
    <div className="page">
      <div className="row" style={{ gap: 8 }}>
        <div className="field grow">
          <label>Alumno</label>
          <select value={athleteId} onChange={(e) => setAthleteId(Number(e.target.value))}>
            {activeAthletes.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </div>
        <div className="field grow">
          <label>Prueba</label>
          <select value={testId} onChange={(e) => setTestId(e.target.value)}>
            {activeTests.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </div>
      </div>

      {loading && <div className="spinner">Cargando…</div>}

      {!loading && test && (
        <div className="grid-2">
          <div className="card">
            <div className="row between">
              <div className="block-title" style={{ marginTop: 0 }}>{test.name}</div>
              {trend && <span className={`delta ${trend.startsWith("▲") ? "up" : trend.startsWith("▼") ? "down" : "flat"}`}>{trend}</span>}
            </div>
            {test.better === "low" && <div className="muted">menos es mejor (tiempo)</div>}
            <div style={{ marginTop: 10 }}>
              <Chart points={points} test={test} />
            </div>
          </div>

          <div className="card">
            <div className="block-title" style={{ marginTop: 0 }}>Historial</div>
            {points.length === 0 && <div className="empty">Sin registros para esta combinación.</div>}
            {[...points].reverse().map((p, i, arr) => {
              const prev = arr[i + 1];
              const d = prev ? computeDelta(test.better, test.unit, p.raw, prev.raw) : null;
              return (
                <div className="exrow row between" key={p.date}>
                  <span className="muted">{fmtShortDate(p.date)}</span>
                  <span className="exname">{formatValue(test.unit, p.raw)}</span>
                  <span className={`delta ${d?.improved === true ? "up" : d?.improved === false ? "down" : "flat"}`}>
                    {d ? formatDelta(d, test.unit) : "—"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
