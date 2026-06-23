import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../api.js";
import { useStore } from "../state/store.jsx";
import { useToast } from "../components/Toast.jsx";
import LevelTag from "../components/LevelTag.jsx";
import {
  computeDelta, dateInputToMs, dateInputValue, fmtShortDate, formatDelta, todayMs,
} from "../lib/format.js";

export default function TestDay() {
  const { athletes, tests, refreshSessions } = useStore();
  const toast = useToast();
  const activeAthletes = athletes.filter((a) => !a.archived);
  const activeTests = tests.filter((t) => !t.archived);

  const [dateMs, setDateMs] = useState(() => todayMs());
  const [activeTestId, setActiveTestId] = useState(() => activeTests[0]?.id || "");
  const [values, setValues] = useState({}); // `${athleteId}:${testId}` -> raw
  const [latest, setLatest] = useState(null);
  const [busy, setBusy] = useState(false);
  const [savedId, setSavedId] = useState(null);

  useEffect(() => {
    api.get("/api/sessions/latest").then(setLatest).catch(() => setLatest(null));
  }, []);

  const prevMap = useMemo(() => {
    const m = {};
    (latest?.measurements || []).forEach((mm) => { m[`${mm.athlete_id}:${mm.test_id}`] = mm.raw_value; });
    return m;
  }, [latest]);

  const activeTest = activeTests.find((t) => t.id === activeTestId);

  function setVal(athleteId, raw) {
    setValues((v) => ({ ...v, [`${athleteId}:${activeTestId}`]: raw }));
  }

  async function save() {
    const measurements = Object.entries(values)
      .map(([key, raw]) => {
        const [athlete_id, test_id] = key.split(":");
        return { athlete_id: Number(athlete_id), test_id, raw_value: raw };
      })
      .filter((m) => m.raw_value.trim() !== "");
    if (measurements.length === 0) {
      toast("Anota al menos un resultado");
      return;
    }
    setBusy(true);
    try {
      const created = await api.post("/api/sessions", { date: dateMs, note: "", measurements });
      setSavedId(created.id);
      await refreshSessions();
      toast("Prueba guardada ✓");
      setValues({});
      api.get("/api/sessions/latest").then(setLatest).catch(() => {});
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "No se pudo guardar");
    } finally {
      setBusy(false);
    }
  }

  async function share() {
    if (!savedId) {
      toast("Guarda la prueba primero");
      return;
    }
    try {
      const text = await api.getText(`/api/export/session/${savedId}.txt`);
      if (navigator.share) {
        await navigator.share({ text });
      } else {
        await navigator.clipboard.writeText(text);
        toast("Resumen copiado ✓");
      }
    } catch {
      toast("No se pudo compartir");
    }
  }

  if (activeTests.length === 0) {
    return <div className="page"><div className="empty">No hay pruebas definidas. Créalas en Editar.</div></div>;
  }

  return (
    <div className="page">
      <div className="field">
        <label>Fecha de la prueba</label>
        <input type="date" value={dateInputValue(dateMs)}
          onChange={(e) => setDateMs(dateInputToMs(e.target.value))} />
      </div>
      <div className="muted" style={{ marginBottom: 12 }}>
        {latest ? `Comparando con ${fmtShortDate(latest.date)}` : "Primera sesión (sin comparación previa)"}
      </div>

      <div className="chips">
        {activeTests.map((t) => (
          <button key={t.id} className={`chip ${t.id === activeTestId ? "active" : ""}`}
            onClick={() => setActiveTestId(t.id)}>
            {t.name}
          </button>
        ))}
      </div>

      {activeTest && (
        <div className="card2 card">
          <div className="block-title" style={{ marginTop: 0 }}>{activeTest.name}</div>
          <div className="muted">
            Unidad: {activeTest.unit} · {activeTest.better === "high" ? "más es mejor" : "menos es mejor"}
          </div>
        </div>
      )}

      <div className="card capture-list">
        {activeAthletes.map((a) => {
          const key = `${a.id}:${activeTestId}`;
          const raw = values[key] ?? "";
          const prev = prevMap[key];
          const level = a.levels[activeTest?.pattern_id] || "A";
          const d = prev != null ? computeDelta(activeTest.better, activeTest.unit, raw, prev) : null;
          return (
            <div className="exrow" key={a.id}>
              <div className="row between">
                <div className="row">
                  <LevelTag level={level} size="sm" />
                  <span className="exname">{a.name}</span>
                </div>
                <input className="input narrow"
                  inputMode={activeTest.unit === "mm:ss" ? "text" : "decimal"}
                  placeholder={activeTest.unit === "mm:ss" ? "mm:ss" : activeTest.unit}
                  value={raw} onChange={(e) => setVal(a.id, e.target.value)} />
              </div>
              <div className="row" style={{ marginTop: 4, gap: 12 }}>
                {prev != null && <span className="muted">antes {prev}</span>}
                {d && (
                  <span className={`delta ${d.improved === true ? "up" : d.improved === false ? "down" : "flat"}`}>
                    {formatDelta(d, activeTest.unit)}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="row between">
        <button className="btn ghost" onClick={share} disabled={!savedId}>Compartir resumen</button>
        <button className="btn" onClick={save} disabled={busy}>{busy ? "Guardando…" : "Guardar prueba"}</button>
      </div>
    </div>
  );
}
