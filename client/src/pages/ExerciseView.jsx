import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useStore } from "../state/store.jsx";
import MediaView from "../components/MediaView.jsx";
import LevelTag from "../components/LevelTag.jsx";
import { levelsById } from "../lib/levels.js";

export default function ExerciseView() {
  const { dayKey, exerciseId } = useParams();
  const [params] = useSearchParams();
  const view = params.get("view") || "all"; // 'all' o id de alumno
  const navigate = useNavigate();
  const { routines, athletes, levels } = useStore();

  const lvById = useMemo(() => levelsById(levels), [levels]);
  const day = routines[dayKey];
  // Lista aplanada de ejercicios del día, en orden de bloques.
  const flat = useMemo(() => {
    if (!day) return [];
    return day.blocks.flatMap((b) => b.items.map((it) => ({ ...it, blockTitle: b.title })));
  }, [day]);

  const index = flat.findIndex((e) => String(e.id) === String(exerciseId));
  const ex = index >= 0 ? flat[index] : null;

  const athlete = view === "all" ? null : athletes.find((a) => String(a.id) === String(view));
  const fallbackLevel = levels[0]?.id;
  const defaultLevel = (athlete && ex ? athlete.levels[ex.pattern_id] : null) || fallbackLevel;
  const [level, setLevel] = useState(defaultLevel);

  // Al cambiar de ejercicio, reajusta el nivel por defecto.
  useEffect(() => {
    setLevel(defaultLevel);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exerciseId, view]);

  if (!day || !ex) {
    return (
      <div className="exview">
        <button className="btn ghost" onClick={() => navigate(-1)}>← Volver</button>
        <div className="empty">Ejercicio no encontrado.</div>
      </div>
    );
  }

  const variant = (ex.variants || {})[level] || {};
  const text = variant.text;
  const media = variant.media;

  const go = (i) => {
    const target = flat[i];
    navigate(`/ejercicio/${dayKey}/${target.id}?view=${encodeURIComponent(view)}`);
  };

  return (
    <div className="exview">
      <div className="exview-top">
        <button className="btn ghost sm" onClick={() => navigate(-1)}>← Volver</button>
        <span className="muted">{day.name}{athlete ? ` · ${athlete.name}` : ""}</span>
      </div>

      <div className="exview-body">
        <div className="exview-media">
          <MediaView src={media} />
        </div>

        <div className="exview-info">
          <div className="exview-head">
            <div className="eyebrow">{ex.blockTitle}</div>
            <h1 className="exview-name">{ex.name}</h1>
          </div>

          {/* Selector de variante */}
          <div className="exview-levels">
            {levels.map((lv) => (
              <button key={lv.id} className={`lvltab ${level === lv.id ? "active" : ""}`} onClick={() => setLevel(lv.id)}>
                <LevelTag level={lv} size="sm" /> {lv.id === defaultLevel && athlete ? "· su nivel" : ""}
              </button>
            ))}
          </div>

          <div className="card exview-text">
            <div className="row" style={{ gap: 10, alignItems: "flex-start" }}>
              <LevelTag level={lvById[level]} size="md" />
              <span className="txt solo">{text || "—"}</span>
            </div>
          </div>

          <div className="exview-nav">
            <button className="btn ghost" disabled={index <= 0} onClick={() => go(index - 1)}>← Anterior</button>
            <span className="muted">{index + 1} / {flat.length}</span>
            <button className="btn ghost" disabled={index >= flat.length - 1} onClick={() => go(index + 1)}>Siguiente →</button>
          </div>
        </div>
      </div>
    </div>
  );
}
