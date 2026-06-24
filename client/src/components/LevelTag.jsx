import { readableOn } from "../lib/levels.js";

// Píldora con el nombre del nivel y su color. `level` es el objeto {id,label,color}.
export default function LevelTag({ level, size = "sm" }) {
  if (!level) return null;
  const color = level.color || "#888888";
  return (
    <span className={`ltag ${size}`} style={{ background: color, color: readableOn(color) }}>
      {level.label}
    </span>
  );
}
