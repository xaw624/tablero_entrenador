import LevelTag from "./LevelTag.jsx";
import { hasMedia } from "../lib/media.js";

// Modo "all": muestra las 3 variantes A/B/C apiladas.
// Modo "solo": muestra una sola línea con el nivel del alumno.
// onShow: si se pasa, renderiza el botón "Mostrar ejercicio".
export default function ExerciseRow({ exercise, mode, level, text, media, onShow }) {
  const anyMedia =
    mode === "solo"
      ? hasMedia(media)
      : hasMedia(exercise.media_a) || hasMedia(exercise.media_b) || hasMedia(exercise.media_c);

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
        ["A", "B", "C"].map((lv) => (
          <div className="exvariant" key={lv}>
            <LevelTag level={lv} size="sm" />
            <span className="txt">{exercise[`variant_${lv.toLowerCase()}`] || "—"}</span>
          </div>
        ))
      )}
    </div>
  );
}
