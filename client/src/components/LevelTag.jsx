// Cuadro con letra A/B/C y color del nivel. Mapeo fijo: A=rojo, B=ámbar, C=verde.
export default function LevelTag({ level, size = "sm" }) {
  const lv = (level || "A").toUpperCase();
  return <span className={`lvl ${size} ${lv}`} aria-label={`Nivel ${lv}`}>{lv}</span>;
}
