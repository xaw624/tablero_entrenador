import { useState } from "react";
import { api, ApiError } from "../api.js";
import { useStore } from "../state/store.jsx";
import { useToast } from "../components/Toast.jsx";
import ConfirmDialog from "../components/ConfirmDialog.jsx";

export default function Athletes() {
  const { athletes, patterns, refreshAthletes } = useStore();
  const toast = useToast();
  const [confirm, setConfirm] = useState(null); // athlete a archivar
  const activeAthletes = athletes.filter((a) => !a.archived);

  async function rename(id, name) {
    try {
      await api.patch(`/api/athletes/${id}`, { name });
      await refreshAthletes();
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "No se pudo renombrar");
    }
  }

  async function setLevel(id, pattern_id, level) {
    try {
      await api.put(`/api/athletes/${id}/levels`, { [pattern_id]: level });
      await refreshAthletes();
    } catch (e) {
      toast(e instanceof ApiError ? e.detail : "No se pudo cambiar el nivel");
    }
  }

  async function archive(a) {
    setConfirm(null);
    await api.del(`/api/athletes/${a.id}`);
    await refreshAthletes();
    toast("Alumno archivado");
  }

  async function add() {
    if (activeAthletes.length >= 12) {
      toast("Límite sugerido de 12 alumnos");
      return;
    }
    await api.post("/api/athletes", { name: `Alumno ${activeAthletes.length + 1}` });
    await refreshAthletes();
  }

  return (
    <div className="page">
      <div className="muted" style={{ marginBottom: 12 }}>
        Los niveles son <strong>por patrón</strong> y pueden mezclarse (p. ej. C en pierna, A en tracción).
      </div>

      <div className="grid-cards">
      {activeAthletes.map((a) => (
        <div className="card" key={a.id}>
          <div className="row between">
            <input className="input grow" defaultValue={a.name}
              onBlur={(e) => e.target.value.trim() && e.target.value !== a.name && rename(a.id, e.target.value.trim())} />
            <button className="btn ghost sm" title="Archivar" onClick={() => setConfirm(a)} style={{ marginLeft: 8 }}>×</button>
          </div>

          <div className="lvlgrid">
            {patterns.map((p) => {
              const current = a.levels[p.id] || "A";
              return (
                <div className="prow" key={p.id}>
                  <span className="plabel">{p.label}</span>
                  <div className="lvlbtns">
                    {["A", "B", "C"].map((lv) => (
                      <button key={lv}
                        className={`lvlbtn ${lv} ${current === lv ? "active" : ""}`}
                        onClick={() => current !== lv && setLevel(a.id, p.id, lv)}>
                        {lv}
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
      </div>

      <button className="btn" onClick={add}>+ Añadir alumno</button>

      <ConfirmDialog
        open={!!confirm}
        title="Archivar alumno"
        message={confirm ? `¿Archivar a "${confirm.name}"? Su historial se conserva.` : ""}
        confirmLabel="Archivar"
        onConfirm={() => archive(confirm)}
        onCancel={() => setConfirm(null)}
      />
    </div>
  );
}
