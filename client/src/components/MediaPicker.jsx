import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api.js";
import { mediaKind } from "../lib/media.js";

// Editor de medio de una variante: subir imagen/gif o pegar URL de video.
// onCommit(value) persiste (se llama al subir y al salir del input de URL).
export default function MediaPicker({ value, onCommit, level, onError }) {
  const fileRef = useRef(null);
  const [draft, setDraft] = useState(value || "");
  const [busy, setBusy] = useState(false);

  useEffect(() => { setDraft(value || ""); }, [value]);

  const kind = mediaKind(draft);

  async function onFile(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await api.postForm("/api/uploads", fd);
      setDraft(res.url);
      onCommit(res.url);
    } catch (err) {
      onError?.(err instanceof ApiError ? err.detail : "No se pudo subir");
    } finally {
      setBusy(false);
    }
  }

  function commitUrl() {
    if (draft !== (value || "")) onCommit(draft.trim());
  }

  function clear() {
    setDraft("");
    onCommit("");
  }

  return (
    <div className="mediapicker">
      <label className="muted">Medio (imagen/gif o URL de video)</label>
      <div className="row" style={{ gap: 6 }}>
        <input
          className="grow"
          placeholder="URL de video o sube imagen/gif →"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commitUrl}
        />
        <button type="button" className="btn ghost sm" disabled={busy} onClick={() => fileRef.current?.click()}>
          {busy ? "…" : "Subir"}
        </button>
        {draft && (
          <button type="button" className="btn ghost sm" title="Quitar" onClick={clear}>×</button>
        )}
        <input ref={fileRef} type="file" accept="image/*" hidden onChange={onFile} />
      </div>
      {draft && (
        <div className="media-hint muted">
          {kind === "image" && draft.startsWith("/media/")
            ? "imagen subida"
            : kind === "image"
            ? "imagen (URL)"
            : kind === "youtube" || kind === "vimeo" || kind === "video"
            ? "video"
            : "enlace"}
          {kind === "image" && <img className="media-thumb" src={draft} alt="" />}
        </div>
      )}
    </div>
  );
}
