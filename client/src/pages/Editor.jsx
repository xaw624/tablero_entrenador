import { useState } from "react";
import { api, ApiError } from "../api.js";
import { useStore } from "../state/store.jsx";
import { useToast } from "../components/Toast.jsx";
import ConfirmDialog from "../components/ConfirmDialog.jsx";
import MediaPicker from "../components/MediaPicker.jsx";
import CsvBar from "../components/CsvBar.jsx";
import { readableOn } from "../lib/levels.js";

const UNITS = ["reps", "seg", "cm", "kg", "m", "mm:ss"];
const WEEKDAYS = [
  ["", "(sin asignar)"], ["1", "Lunes"], ["2", "Martes"], ["3", "Miércoles"],
  ["4", "Jueves"], ["5", "Viernes"], ["6", "Sábado"], ["0", "Domingo"],
];

export default function Editor() {
  const [tab, setTab] = useState("rutinas");
  return (
    <div className="page">
      <div className="chips">
        <button className={`chip ${tab === "rutinas" ? "active" : ""}`} onClick={() => setTab("rutinas")}>Rutinas</button>
        <button className={`chip ${tab === "niveles" ? "active" : ""}`} onClick={() => setTab("niveles")}>Niveles</button>
        <button className={`chip ${tab === "pruebas" ? "active" : ""}`} onClick={() => setTab("pruebas")}>Pruebas</button>
      </div>
      {tab === "rutinas" && <RoutinesEditor />}
      {tab === "niveles" && <LevelsEditor />}
      {tab === "pruebas" && <TestsEditor />}
    </div>
  );
}

function RoutinesEditor() {
  const { routines, patterns, levels, refreshRoutines } = useStore();
  const toast = useToast();
  const days = Object.values(routines).sort((a, b) => a.sort - b.sort);
  const [day, setDay] = useState(() => days[0]?.day_key);
  const [confirm, setConfirm] = useState(null);
  const dayData = routines[day] || days[0];

  const wrap = (fn) => async (...args) => {
    try { await fn(...args); await refreshRoutines(); }
    catch (e) { toast(e instanceof ApiError ? e.detail : "Error al guardar"); }
  };

  const saveDay = wrap((dk, patch) => api.patch(`/api/routines/${dk}`, patch));
  const addDay = wrap(async () => {
    const d = await api.post("/api/routines/days", { name: "Nuevo día", focus: "" });
    setDay(d.day_key);
  });
  const delDay = wrap(async (dk) => {
    await api.del(`/api/routines/days/${dk}`);
    setDay(days.find((d) => d.day_key !== dk)?.day_key);
  });
  const reorderDays = wrap((keys) => api.put("/api/routines/days/reorder", { day_keys: keys }));
  const saveBlockTitle = wrap((id, v) => api.patch(`/api/routines/blocks/${id}`, { title: v }));
  const delBlock = wrap((id) => api.del(`/api/routines/blocks/${id}`));
  const addBlock = wrap(() => api.post(`/api/routines/${dayData.day_key}/blocks`, { title: "Nuevo bloque" }));
  const addExercise = wrap((blockId) =>
    api.post(`/api/routines/blocks/${blockId}/exercises`, { name: "Nuevo ejercicio", pattern_id: patterns[0].id }));
  const saveExercise = wrap((id, patch) => api.patch(`/api/routines/exercises/${id}`, patch));
  const delExercise = wrap((id) => api.del(`/api/routines/exercises/${id}`));
  const saveVariant = wrap((exId, levelId, patch) =>
    api.put(`/api/routines/exercises/${exId}/variants/${levelId}`, patch));

  const moveDay = (dk, dir) => {
    const keys = days.map((d) => d.day_key);
    const i = keys.indexOf(dk);
    const j = i + dir;
    if (j < 0 || j >= keys.length) return;
    [keys[i], keys[j]] = [keys[j], keys[i]];
    reorderDays(keys);
  };

  if (!dayData) {
    return (
      <>
        <div className="empty">No hay días. Crea uno para empezar.</div>
        <button className="btn" onClick={addDay}>+ Añadir día</button>
      </>
    );
  }

  return (
    <>
      <CsvBar label="Rutinas" exportPath="/api/export/routines.csv"
        importPath="/api/import/routines.csv" onImported={refreshRoutines} toast={toast} />

      <div className="chips">
        {days.map((d) => (
          <button key={d.day_key} className={`chip ${d.day_key === dayData.day_key ? "active" : ""}`}
            onClick={() => setDay(d.day_key)}>
            {d.name}
          </button>
        ))}
        <button className="chip" onClick={addDay}>+ día</button>
      </div>

      {/* Ajustes del día */}
      <div className="card">
        <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
          <div className="field grow" style={{ marginBottom: 0 }}>
            <label>Nombre del día</label>
            <input defaultValue={dayData.name} key={`dn-${dayData.day_key}`}
              onBlur={(e) => e.target.value.trim() && e.target.value !== dayData.name && saveDay(dayData.day_key, { name: e.target.value.trim() })} />
          </div>
          <div className="field" style={{ marginBottom: 0 }}>
            <label>Día de calendario</label>
            <select value={dayData.weekday == null ? "" : String(dayData.weekday)} key={`wd-${dayData.day_key}`}
              onChange={(e) => e.target.value !== "" && saveDay(dayData.day_key, { weekday: Number(e.target.value) })}>
              {WEEKDAYS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
        </div>
        <div className="field" style={{ marginTop: 8, marginBottom: 8 }}>
          <label>Focus del día</label>
          <input defaultValue={dayData.focus} key={`focus-${dayData.day_key}`}
            onBlur={(e) => e.target.value !== dayData.focus && saveDay(dayData.day_key, { focus: e.target.value })} />
        </div>
        <div className="row" style={{ gap: 6 }}>
          <button className="btn ghost sm" onClick={() => moveDay(dayData.day_key, -1)}>↑</button>
          <button className="btn ghost sm" onClick={() => moveDay(dayData.day_key, 1)}>↓</button>
          <span className="grow" />
          <button className="btn ghost sm" onClick={() => setConfirm({ type: "day", id: dayData.day_key, name: dayData.name })}>Eliminar día</button>
        </div>
      </div>

      <div className="grid-cards-lg">
      {dayData.blocks.map((block) => (
        <div className="card" key={block.id}>
          <div className="row between">
            <input className="input grow" defaultValue={block.title} key={`bt-${block.id}`}
              onBlur={(e) => e.target.value.trim() && e.target.value !== block.title && saveBlockTitle(block.id, e.target.value.trim())} />
            <button className="btn ghost sm" onClick={() => setConfirm({ type: "block", id: block.id, name: block.title })} style={{ marginLeft: 8 }}>×</button>
          </div>

          {block.items.map((ex) => (
            <div className="card2 card" key={ex.id}>
              <div className="row between">
                <input className="input grow" defaultValue={ex.name} key={`en-${ex.id}`}
                  onBlur={(e) => e.target.value.trim() && e.target.value !== ex.name && saveExercise(ex.id, { name: e.target.value.trim() })} />
                <button className="btn ghost sm" onClick={() => setConfirm({ type: "ex", id: ex.id, name: ex.name })} style={{ marginLeft: 8 }}>×</button>
              </div>
              <div className="field" style={{ marginTop: 8 }}>
                <label>Patrón</label>
                <select defaultValue={ex.pattern_id} key={`ep-${ex.id}`}
                  onChange={(e) => saveExercise(ex.id, { pattern_id: e.target.value })}>
                  {patterns.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
                </select>
              </div>
              {levels.map((lv) => {
                const v = (ex.variants || {})[lv.id] || {};
                return (
                  <div className="field variant-edit" key={lv.id} style={{ marginBottom: 6 }}>
                    <label style={{ color: lv.color }}>Variante · {lv.label}</label>
                    <input defaultValue={v.text || ""} key={`ev-${ex.id}-${lv.id}`}
                      onBlur={(e) => e.target.value !== (v.text || "") && saveVariant(ex.id, lv.id, { text: e.target.value })} />
                    <MediaPicker level={lv.id} value={v.media || ""}
                      onCommit={(val) => saveVariant(ex.id, lv.id, { media: val })}
                      onError={(m) => toast(m)} />
                  </div>
                );
              })}
            </div>
          ))}
          <button className="btn ghost sm" onClick={() => addExercise(block.id)}>+ Ejercicio</button>
        </div>
      ))}
      </div>

      <button className="btn" onClick={addBlock}>+ Añadir bloque</button>

      <ConfirmDialog
        open={!!confirm}
        title={confirm?.type === "block" ? "Borrar bloque" : confirm?.type === "day" ? "Eliminar día" : "Borrar ejercicio"}
        message={confirm
          ? confirm.type === "day"
            ? `¿Eliminar el día "${confirm.name}" con todos sus bloques y ejercicios?`
            : `¿Borrar "${confirm.name}"?${confirm.type === "block" ? " Se borran sus ejercicios." : ""}`
          : ""}
        confirmLabel={confirm?.type === "day" ? "Eliminar" : "Borrar"}
        onConfirm={() => {
          const c = confirm; setConfirm(null);
          if (c.type === "block") delBlock(c.id);
          else if (c.type === "day") delDay(c.id);
          else delExercise(c.id);
        }}
        onCancel={() => setConfirm(null)}
      />
    </>
  );
}

function LevelsEditor() {
  const { levels, refreshLevels, refreshRoutines, refreshAthletes } = useStore();
  const toast = useToast();
  const [confirm, setConfirm] = useState(null);

  const wrap = (fn, heavy = false) => async (...args) => {
    try {
      await fn(...args);
      await refreshLevels();
      if (heavy) { await refreshRoutines(); await refreshAthletes(); }
    } catch (e) { toast(e instanceof ApiError ? e.detail : "Error al guardar"); }
  };

  const saveLevel = wrap((id, patch) => api.patch(`/api/levels/${id}`, patch));
  const addLevel = wrap(() => api.post("/api/levels", { label: "Nuevo nivel", color: "#7b5cff" }), true);
  const delLevel = wrap((id) => api.del(`/api/levels/${id}`), true);
  const reorderLevels = wrap((ids) => api.put("/api/levels/reorder", { level_ids: ids }), true);

  const move = (id, dir) => {
    const ids = levels.map((l) => l.id);
    const i = ids.indexOf(id);
    const j = i + dir;
    if (j < 0 || j >= ids.length) return;
    [ids[i], ids[j]] = [ids[j], ids[i]];
    reorderLevels(ids);
  };

  return (
    <>
      <div className="muted" style={{ marginBottom: 12 }}>
        Los niveles son una lista global. Cada ejercicio define una variante por nivel y cada alumno
        elige su nivel por patrón. Borrar un nivel reasigna a los alumnos al primero.
      </div>

      <div className="grid-cards">
      {levels.map((lv) => (
        <div className="card" key={lv.id}>
          <div className="row" style={{ gap: 10 }}>
            <input type="color" value={lv.color} title="Color" style={{ width: 44, height: 44, padding: 2 }}
              onChange={(e) => saveLevel(lv.id, { color: e.target.value })} />
            <input className="grow" defaultValue={lv.label} key={`ll-${lv.id}`}
              onBlur={(e) => e.target.value.trim() && e.target.value !== lv.label && saveLevel(lv.id, { label: e.target.value.trim() })} />
          </div>
          <div className="row" style={{ gap: 6, marginTop: 8 }}>
            <span className="ltag sm" style={{ background: lv.color, color: readableOn(lv.color) }}>{lv.label}</span>
            <span className="grow" />
            <button className="btn ghost sm" onClick={() => move(lv.id, -1)}>↑</button>
            <button className="btn ghost sm" onClick={() => move(lv.id, 1)}>↓</button>
            <button className="btn ghost sm" onClick={() => setConfirm(lv)}>×</button>
          </div>
        </div>
      ))}
      </div>

      <button className="btn" onClick={addLevel}>+ Añadir nivel</button>

      <ConfirmDialog
        open={!!confirm}
        title="Borrar nivel"
        message={confirm ? `¿Borrar el nivel "${confirm.label}"? Los alumnos en este nivel pasarán al primero, y se borran sus variantes.` : ""}
        confirmLabel="Borrar"
        onConfirm={() => { const c = confirm; setConfirm(null); delLevel(c.id); }}
        onCancel={() => setConfirm(null)}
      />
    </>
  );
}

function TestsEditor() {
  const { tests, patterns, refreshTests } = useStore();
  const toast = useToast();
  const [confirm, setConfirm] = useState(null);
  const activeTests = tests.filter((t) => !t.archived);

  const wrap = (fn) => async (...args) => {
    try { await fn(...args); await refreshTests(); }
    catch (e) { toast(e instanceof ApiError ? e.detail : "Error al guardar"); }
  };

  const saveTest = wrap((id, patch) => api.patch(`/api/tests/${id}`, patch));
  const delTest = wrap((id) => api.del(`/api/tests/${id}`));
  const addTest = wrap(() => api.post("/api/tests", { name: "Nueva prueba", pattern_id: patterns[0].id, unit: "reps", better: "high" }));

  return (
    <>
      <CsvBar label="Pruebas" exportPath="/api/export/tests.csv"
        importPath="/api/import/tests.csv" onImported={refreshTests} toast={toast} />

      <div className="grid-cards">
      {activeTests.map((t) => (
        <div className="card" key={t.id}>
          <div className="row between">
            <input className="input grow" defaultValue={t.name} key={`tn-${t.id}`}
              onBlur={(e) => e.target.value.trim() && e.target.value !== t.name && saveTest(t.id, { name: e.target.value.trim() })} />
            <button className="btn ghost sm" onClick={() => setConfirm(t)} style={{ marginLeft: 8 }}>×</button>
          </div>
          <div className="row" style={{ gap: 8, marginTop: 8 }}>
            <div className="field grow">
              <label>Patrón</label>
              <select defaultValue={t.pattern_id} onChange={(e) => saveTest(t.id, { pattern_id: e.target.value })}>
                {patterns.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
              </select>
            </div>
            <div className="field grow">
              <label>Unidad</label>
              <select defaultValue={t.unit} onChange={(e) => saveTest(t.id, { unit: e.target.value })}>
                {UNITS.map((u) => <option key={u} value={u}>{u}</option>)}
              </select>
            </div>
          </div>
          <div className="field">
            <label>Dirección</label>
            <select defaultValue={t.better} onChange={(e) => saveTest(t.id, { better: e.target.value })}>
              <option value="high">más es mejor</option>
              <option value="low">menos es mejor</option>
            </select>
          </div>
        </div>
      ))}
      </div>

      <button className="btn" onClick={addTest}>+ Añadir prueba</button>

      <ConfirmDialog
        open={!!confirm}
        title="Borrar prueba"
        message={confirm ? `¿Borrar "${confirm.name}"? Si tiene mediciones se archiva.` : ""}
        confirmLabel="Borrar"
        onConfirm={() => { const c = confirm; setConfirm(null); delTest(c.id); }}
        onCancel={() => setConfirm(null)}
      />
    </>
  );
}
