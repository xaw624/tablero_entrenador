import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useStore } from "../state/store.jsx";
import ExerciseRow from "../components/ExerciseRow.jsx";
import { levelsById } from "../lib/levels.js";

export default function Today() {
  const { routines, athletes, levels } = useStore();
  const navigate = useNavigate();

  // Lista de días ordenada por sort; "Hoy" = día cuyo weekday coincide con el del calendario.
  const days = useMemo(
    () => Object.values(routines).sort((a, b) => a.sort - b.sort),
    [routines]
  );
  const todayKey = useMemo(() => {
    const wd = new Date().getDay();
    const match = days.find((d) => d.weekday === wd);
    return match ? match.day_key : days[0]?.day_key;
  }, [days]);

  const [day, setDay] = useState(() => todayKey);
  const [view, setView] = useState("all"); // 'all' o athlete id (string)

  const lvById = useMemo(() => levelsById(levels), [levels]);
  const activeAthletes = athletes.filter((a) => !a.archived);
  const dayData = routines[day] || routines[todayKey];
  const isToday = dayData && dayData.day_key === todayKey;

  const athlete = useMemo(
    () => (view === "all" ? null : activeAthletes.find((a) => String(a.id) === String(view))),
    [view, activeAthletes]
  );

  const showExercise = (exId) =>
    navigate(`/ejercicio/${dayData.day_key}/${exId}?view=${encodeURIComponent(view)}`);

  if (!dayData) return <div className="page"><div className="empty">No hay rutina para este día.</div></div>;

  return (
    <div className="page">
      <div className="chips">
        {days.map((d) => (
          <button key={d.day_key} className={`chip ${d.day_key === dayData.day_key ? "active" : ""}`}
            onClick={() => setDay(d.day_key)}>
            {d.name}
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
      </div>

      <div className="field">
        <label>Ver para</label>
        <select value={view} onChange={(e) => setView(e.target.value)}>
          <option value="all">Todos los niveles</option>
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
              const levelId = athlete.levels[ex.pattern_id];
              const v = (ex.variants || {})[levelId] || {};
              return (
                <ExerciseRow key={ex.id} exercise={ex} mode="solo" level={lvById[levelId]}
                  text={v.text} media={v.media} onShow={() => showExercise(ex.id)} />
              );
            }
            return <ExerciseRow key={ex.id} exercise={ex} mode="all" levels={levels}
              onShow={() => showExercise(ex.id)} />;
          })}
        </div>
      ))}
      </div>
    </div>
  );
}
