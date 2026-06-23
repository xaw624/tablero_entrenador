import { NavLink } from "react-router-dom";

const I = {
  hoy: "M4 7h16M4 12h16M4 17h10", // líneas (board del día)
  prueba: "M12 8v4l3 2M12 21a8 8 0 100-16 8 8 0 000 16zM9 2h6", // cronómetro
  progreso: "M4 19V5M4 19h16M8 15l3-4 3 2 4-6", // gráfica
  alumnos: "M16 19a4 4 0 00-8 0M12 11a3 3 0 100-6 3 3 0 000 6M20 19a3 3 0 00-4-3M4 19a3 3 0 014-3", // personas
  editar: "M4 20h4L18 10l-4-4L4 16v4zM13 7l4 4", // lápiz
};

const TABS = [
  { to: "/", label: "Hoy", end: true, icon: I.hoy },
  { to: "/prueba", label: "Prueba", icon: I.prueba },
  { to: "/progreso", label: "Progreso", icon: I.progreso },
  { to: "/alumnos", label: "Alumnos", icon: I.alumnos },
  { to: "/editar", label: "Editar", icon: I.editar },
];

export default function TabBar() {
  return (
    <nav className="tabbar" aria-label="Navegación principal">
      {TABS.map((t) => (
        <NavLink key={t.to} to={t.to} end={t.end} className={({ isActive }) => (isActive ? "active" : "")}>
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor"
            strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d={t.icon} />
          </svg>
          <span>{t.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
