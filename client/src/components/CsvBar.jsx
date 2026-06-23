import { useRef, useState } from "react";
import { api, ApiError } from "../api.js";
import ConfirmDialog from "./ConfirmDialog.jsx";

// Barra de Exportar/Importar CSV (reemplaza todo). Reutilizable para rutinas y pruebas.
export default function CsvBar({ label, exportPath, importPath, onImported, toast }) {
  const fileRef = useRef(null);
  const [pending, setPending] = useState(null); // File a confirmar
  const [busy, setBusy] = useState(false);

  function pickFile(e) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (f) setPending(f);
  }

  async function doImport() {
    const file = pending;
    setPending(null);
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await api.postForm(importPath, fd);
      await onImported?.();
      toast?.(`Importado ✓ (${Object.values(res).filter((v) => typeof v === "number").join(", ")})`);
    } catch (err) {
      toast?.(err instanceof ApiError ? err.detail : "No se pudo importar");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card csvbar">
      <div className="row between">
        <div>
          <div className="block-title" style={{ marginTop: 0 }}>{label}</div>
          <div className="muted">Exporta para editar en Excel; importar reemplaza todo.</div>
        </div>
      </div>
      <div className="row" style={{ gap: 8, marginTop: 8, flexWrap: "wrap" }}>
        {/* Descarga directa: GET con cookie de sesión (mismo origen). */}
        <a className="btn ghost sm" href={exportPath} download>⬇ Exportar CSV</a>
        <button className="btn ghost sm" disabled={busy} onClick={() => fileRef.current?.click()}>
          {busy ? "Importando…" : "⬆ Importar CSV"}
        </button>
        <input ref={fileRef} type="file" accept=".csv,text/csv" hidden onChange={pickFile} />
      </div>

      <ConfirmDialog
        open={!!pending}
        title="Importar CSV"
        message={`Esto reemplazará ${label.toLowerCase()} con el contenido de "${pending?.name}". ¿Continuar?`}
        confirmLabel="Reemplazar"
        onConfirm={doImport}
        onCancel={() => setPending(null)}
      />
    </div>
  );
}
