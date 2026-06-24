import LevelTag from "./LevelTag.jsx";
import { hasMedia } from "../lib/media.js";

// Modo "all": muestra una línea por nivel (iterando `levels`).
// Modo "solo": una sola línea con el nivel del alumno (`level` objeto + `text`/`media`).
// onShow: si se pasa, renderiza el botón "Mostrar ejercicio".
export default function ExerciseRow({ exercise, mode, levels, level, text, media, onShow }) {
  const variants = exercise.variants || {};
  const anyMedia =
    mode === "solo"
      ? hasMedia(media)
      : (levels || []).some((l) => hasMedia(variants[l.id]?.media));

  return (
    <div className="exrow">
      <div className="row between">
        <div className="exname">{exercise.name}</div>
        {onShow && (
          <button className="btn ghost sm show-ex" onClick={onShow}>
            {anyMedia ? "▶ " : ""}Mostrar ejercicio
          </button>
        )}
      </div>

      {mode === "solo" ? (
        <div className="exvariant">
          <LevelTag level={level} size="md" />
          <span className="txt solo">{text || "—"}</span>
        </div>
      ) : (
        (levels || []).map((l) => (
          <div className="exvariant" key={l.id}>
            <LevelTag level={l} size="sm" />
            <span className="txt">{variants[l.id]?.text || "—"}</span>
          </div>
        ))
      )}
    </div>
  );
}
