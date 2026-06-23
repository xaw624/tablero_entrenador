import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useStore } from "../state/store.jsx";
import ExerciseRow from "../components/ExerciseRow.jsx";
import { isWeekend, todayDayKey } from "../lib/format.js";

const DAY_ORDER = ["lunes", "martes", "miercoles", "jueves", "viernes"];

export default function Today() {
  const { routines, athletes } = useStore();
  const navigate = useNavigate();
  const [day, setDay] = useState(() => todayDayKey());
  const [view, setView] = useState("all"); // 'all' o athlete id (string)

  const showExercise = (exId) =>
    navigate(`/ejercicio/${day}/${exId}?view=${encodeURIComponent(view)}`);

  const activeAthletes = athletes.filter((a) => !a.archived);
  const dayData = routines[day];
  const isToday = day === todayDayKey();

  const athlete = useMemo(
    () => (view === "all" ? null : activeAthletes.find((a) => String(a.id) === String(view))),
    [view, activeAthletes]
  );

  if (!dayData) return <div className="page"><div className="empty">No hay rutina para este día.</div></div>;

  return (
    <div className="page">
      <div className="chips">
        {DAY_ORDER.map((d) => (
          <button key={d} className={`chip ${d === day ? "active" : ""}`} onClick={() => setDay(d)}>
            {routines[d]?.name || d}
          </button>
        ))}
      </div>

      <div className="board">
        <div className="eyebrow">Sesión del día</div>
        <div className="dayname">
          {dayData.name}
          {isToday && <span className="today-tag">Hoy</span>}
        </div>
        <div className="focus">{dayData.focus}</div>
        {isWeekend() && isToday && (
          <div className="muted" style={{ marginTop: 6 }}>Fin de semana — mostrando lunes por defecto.</div>
        )}
      </div>

      <div className="field">
        <label>Ver para</label>
        <select value={view} onChange={(e) => setView(e.target.value)}>
          <option value="all">Todos (A/B/C)</option>
          {activeAthletes.map((a) => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
      </div>

      <div className="grid-cards">
      {dayData.blocks.map((block) => (
        <div className="card" key={block.id}>
          <div className="block-title" style={{ marginTop: 0 }}>{block.title}</div>
          {block.items.map((ex) => {
            if (athlete) {
              const level = athlete.levels[ex.pattern_id] || "A";
              const text = ex[`variant_${level.toLowerCase()}`];
              const media = ex[`media_${level.toLowerCase()}`];
              return (
                <ExerciseRow key={ex.id} exercise={ex} mode="solo" level={level} text={text}
                  media={media} onShow={() => showExercise(ex.id)} />
              );
            }
            return <ExerciseRow key={ex.id} exercise={ex} mode="all" onShow={() => showExercise(ex.id)} />;
          })}
        </div>
      ))}
      </div>
    </div>
  );
}
