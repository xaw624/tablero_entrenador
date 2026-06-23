// Réplica en cliente de la lógica de §6.10 para cálculo de deltas al vuelo.

export function toNum(unit, raw) {
  if (raw == null) return null;
  const s = String(raw).trim();
  if (s === "") return null;
  if (unit === "mm:ss") {
    if (s.includes(":")) {
      const [m, sec] = s.split(":");
      const mi = parseInt(m, 10);
      const se = parseFloat(sec.replace(",", "."));
      if (Number.isNaN(mi) || Number.isNaN(se)) return null;
      return mi * 60 + se;
    }
    const v = parseFloat(s.replace(",", "."));
    return Number.isNaN(v) ? null : v;
  }
  const v = parseFloat(s.replace(",", "."));
  return Number.isNaN(v) ? null : v;
}

export function computeDelta(better, unit, curRaw, prevRaw) {
  const cur = toNum(unit, curRaw);
  const prev = toNum(unit, prevRaw);
  if (cur == null || prev == null) return null;
  const d = cur - prev;
  if (d === 0) return { value: 0, improved: null };
  const improved = better === "high" ? d > 0 : d < 0;
  return { value: d, improved };
}

export function formatValue(unit, raw) {
  const s = String(raw ?? "").trim();
  if (!s) return s;
  if (unit === "reps" || unit === "mm:ss") return s;
  return `${s} ${unit}`;
}

export function formatDelta(d, unit) {
  if (!d) return "";
  if (d.value === 0) return "=";
  const sign = d.value > 0 ? "+" : "";
  if (unit === "mm:ss") {
    const abs = Math.abs(d.value);
    const m = Math.floor(abs / 60);
    const s = Math.round(abs % 60);
    return `${d.value > 0 ? "+" : "−"}${m}:${String(s).padStart(2, "0")}`;
  }
  return `${sign}${Math.round(d.value * 100) / 100}`;
}

// Date.getDay() (0=dom..6=sáb) → day_key. Sáb/dom caen en 'lunes'.
const WEEK = ["lunes", "lunes", "martes", "miercoles", "jueves", "viernes", "lunes"];
export function todayDayKey() {
  return WEEK[new Date().getDay()];
}
export function isWeekend() {
  const g = new Date().getDay();
  return g === 0 || g === 6;
}

export function todayMs() {
  // Mediodía local de hoy (epoch ms), como hace el backend para 'date'.
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 12, 0, 0).getTime();
}

export function dateInputValue(ms) {
  const d = new Date(ms);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function dateInputToMs(value) {
  const [y, m, d] = value.split("-").map(Number);
  return new Date(y, m - 1, d, 12, 0, 0).getTime();
}

export function fmtShortDate(ms) {
  const d = new Date(ms);
  const meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  return `${d.getDate()} ${meses[d.getMonth()]} ${d.getFullYear()}`;
}
