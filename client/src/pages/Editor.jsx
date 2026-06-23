import { useState } from "react";
import { api, ApiError } from "../api.js";
import { useStore } from "../state/store.jsx";
import { useToast } from "../components/Toast.jsx";
import ConfirmDialog from "../components/ConfirmDialog.jsx";
import MediaPicker from "../components/MediaPicker.jsx";
import CsvBar from "../components/CsvBar.jsx";

const UNITS = ["reps", "seg", "cm", "kg", "m", "mm:ss"];
const DAY_ORDER = ["lunes", "martes", "miercoles", "jueves", "viernes"];

export default function Editor() {
  const [tab, setTab] = useState("rutinas");
  return (
    <div className="page">
      <div className="chips">
        <button className={`chip ${tab === "rutinas" ? "active" : ""}`} onClick={() => setTab("rutinas")}>Rutinas</button>
        <button className={`chip ${tab === "pruebas" ? "active" : ""}`} onClick={() => setTab("pruebas")}>Pruebas</button>
      </div>
      {tab === "rutinas" ? <RoutinesEditor /> : <TestsEditor />}
    </div>
  );
}

function RoutinesEditor() {
  const { routines, patterns, refreshRoutines } = useStore();
  const toast = useToast();
  const [day, setDay] = useState("lunes");
  const [confirm, setConfirm] = useState(null);
  const dayData = routines[day];

  const wrap = (fn) => async (...args) => {
    try { await fn(...args); await refreshRoutines(); }
    catch (e) { toast(e instanceof ApiError ? e.detail : "Error al guardar"); }
  };

  const saveFocus = wrap((v) => api.patch(`/api/routines/${day}`, { focus: v }));
  const saveBlockTitle = wrap((id, v) => api.patch(`/api/routines/blocks/${id}`, { title: v }));
  const delBlock = wrap((id) => api.del(`/api/routines/blocks/${id}`));
  const addBlock = wrap(() => api.post(`/api/routines/${day}/blocks`, { title: "Nuevo bloque" }));
  const addExercise = wrap((blockId) =>
    api.post(`/api/routines/blocks/${blockId}/exercises`, { name: "Nuevo ejercicio", pattern_id: patterns[0].id }));
  const saveExercise = wrap((id, patch) => api.patch(`/api/routines/exercises/${id}`, patch));
  const delExercise = wrap((id) => api.del(`/api/routines/exercises/${id}`));

  if (!dayData) return <div className="empty">Cargando…</div>;

  return (
    <>
      <CsvBar
        label="Rutinas"
        exportPath="/api/export/routines.csv"
        importPath="/api/import/routines.csv"
        onImported={refreshRoutines}
        toast={toast}
      />

      <div className="chips">
        {DAY_ORDER.map((d) => (
          <button key={d} className={`chip ${d === day ? "active" : ""}`} onClick={() => setDay(d)}>
            {routines[d]?.name || d}
          </button>
        ))}
      </div>

      <div className="field">
        <label>Focus del día</label>
        <input defaultValue={dayData.focus} key={`focus-${day}`}
          onBlur={(e) => e.target.value !== dayData.focus && saveFocus(e.target.value)} />
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
              {["a", "b", "c"].map((lv) => (
                <div className="field variant-edit" key={lv} style={{ marginBottom: 6 }}>
                  <label style={{ color: `var(--lvl${lv.toUpperCase()})` }}>Variante {lv.toUpperCase()}</label>
                  <input defaultValue={ex[`variant_${lv}`]} key={`ev-${ex.id}-${lv}`}
                    onBlur={(e) => e.target.value !== ex[`variant_${lv}`] && saveExercise(ex.id, { [`variant_${lv}`]: e.target.value })} />
                  <MediaPicker
                    level={lv.toUpperCase()}
                    value={ex[`media_${lv}`]}
                    onCommit={(val) => saveExercise(ex.id, { [`media_${lv}`]: val })}
                    onError={(m) => toast(m)}
                  />
                </div>
              ))}
            </div>
          ))}
          <button className="btn ghost sm" onClick={() => addExercise(block.id)}>+ Ejercicio</button>
        </div>
      ))}
      </div>

      <button className="btn" onClick={addBlock}>+ Añadir bloque</button>

      <ConfirmDialog
        open={!!confirm}
        title={confirm?.type === "block" ? "Borrar bloque" : "Borrar ejercicio"}
        message={confirm ? `¿Borrar "${confirm.name}"?${confirm.type === "block" ? " Se borran sus ejercicios." : ""}` : ""}
        confirmLabel="Borrar"
        onConfirm={() => { const c = confirm; setConfirm(null); c.type === "block" ? delBlock(c.id) : delExercise(c.id); }}
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
      <CsvBar
        label="Pruebas"
        exportPath="/api/export/tests.csv"
        importPath="/api/import/tests.csv"
        onImported={refreshTests}
        toast={toast}
      />

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
