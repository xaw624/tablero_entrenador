import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api.js";

// Modal para buscar en el catálogo de ejercicios (fuente wger). Reutilizado por el Editor
// ("+ Desde catálogo") y por el MediaPicker ("Catálogo"). onPick(item) recibe el ejercicio
// elegido; onClose cierra sin elegir. `pattern` prefiltra por patrón (opcional).
export default function CatalogPicker({ open, pattern, onPick, onClose, patterns = [] }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  // Al abrir: limpia estado, enfoca el buscador y carga una primera tanda (según prefiltro).
  useEffect(() => {
    if (!open) return;
    setQ("");
    setError("");
    const t = setTimeout(() => inputRef.current?.focus(), 50);
    return () => clearTimeout(t);
  }, [open]);

  // Búsqueda con debounce; depende de q, pattern y open.
  useEffect(() => {
    if (!open) return;
    let alive = true;
    setBusy(true);
    const t = setTimeout(async () => {
      try {
        const params = new URLSearchParams();
        if (q.trim()) params.set("q", q.trim());
        if (pattern) params.set("pattern", pattern);
        const res = await api.get(`/api/catalog?${params.toString()}`);
        if (alive) { setResults(res); setError(""); }
      } catch (e) {
        if (alive) setError(e instanceof ApiError ? e.detail : "No se pudo buscar");
      } finally {
        if (alive) setBusy(false);
      }
    }, 250);
    return () => { alive = false; clearTimeout(t); };
  }, [q, pattern, open]);

  if (!open) return null;

  const patternLabel = (id) => patterns.find((p) => p.id === id)?.label || id;

  return (
    <div className="backdrop" onClick={onClose}>
      <div className="dialog wide" onClick={(e) => e.stopPropagation()}>
        <div className="row between" style={{ marginBottom: 10 }}>
          <div className="block-title" style={{ marginTop: 0 }}>Catálogo de ejercicios</div>
          <button className="btn ghost sm" onClick={onClose}>×</button>
        </div>

        <input
          ref={inputRef}
          className="input"
          placeholder={pattern ? "Buscar en este patrón…" : "Buscar ejercicio…"}
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />

        {error && <div className="muted" style={{ color: "var(--brick)", marginTop: 10 }}>{error}</div>}

        <div className="catalog-results">
          {busy && results.length === 0 ? (
            <div className="spinner">Buscando…</div>
          ) : results.length === 0 ? (
            <div className="empty" style={{ padding: 24 }}>Sin resultados.</div>
          ) : (
            results.map((item) => (
              <button key={item.id} type="button" className="catalog-item" onClick={() => onPick(item)}>
                {item.media ? (
                  <img className="catalog-thumb" src={item.media} alt="" loading="lazy" />
                ) : (
                  <div className="catalog-thumb catalog-thumb-empty">—</div>
                )}
                <div className="catalog-meta">
                  <div className="catalog-name">{item.name}</div>
                  <div className="muted catalog-sub">
                    {item.pattern_id ? patternLabel(item.pattern_id) : "sin patrón"}
                    {item.muscles ? ` · ${item.muscles}` : ""}
                  </div>
                </div>
              </button>
            ))
          )}
        </div>

        <div className="muted catalog-attr">Fuente: wger · Creative Commons</div>
      </div>
    </div>
  );
}
