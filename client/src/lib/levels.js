// Helpers para el catálogo dinámico de niveles.

export function levelsById(levels) {
  return Object.fromEntries((levels || []).map((l) => [l.id, l]));
}

// Color de texto legible (negro/blanco) según la luminancia del fondo.
export function readableOn(hex) {
  if (!hex || hex[0] !== "#" || hex.length < 7) return "#ffffff";
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return lum > 0.6 ? "#0c0f12" : "#ffffff";
}
