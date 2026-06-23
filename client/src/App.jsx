import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, ApiError, setUnauthorizedHandler } from "./api.js";
import { useStore } from "./state/store.jsx";
import TabBar from "./components/TabBar.jsx";
import Login from "./pages/Login.jsx";
import Today from "./pages/Today.jsx";
import TestDay from "./pages/TestDay.jsx";
import Progress from "./pages/Progress.jsx";
import Athletes from "./pages/Athletes.jsx";
import Editor from "./pages/Editor.jsx";
import ExerciseView from "./pages/ExerciseView.jsx";

function Shell({ children }) {
  const { me, reset } = useStore();
  const navigate = useNavigate();
  async function logout() {
    try { await api.post("/api/auth/logout"); } catch { /* ignore */ }
    reset();
    navigate("/login");
  }
  return (
    <div className="app">
      <header className="header">
        <div className="brand">Tablero<span className="dot">.</span></div>
        <div className="row" style={{ gap: 10 }}>
          <span className="who">{me?.email}</span>
          <button className="btn ghost sm" onClick={logout}>Salir</button>
        </div>
      </header>
      <TabBar />
      {children}
    </div>
  );
}

export default function App() {
  const { me, setMe, ready, loadAll, reset } = useStore();
  const [booting, setBooting] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    setUnauthorizedHandler(() => {
      reset();
      navigate("/login");
    });
  }, [navigate, reset]);

  useEffect(() => {
    (async () => {
      try {
        const u = await api.get("/api/auth/me");
        setMe(u);
        await loadAll();
      } catch (e) {
        if (!(e instanceof ApiError) || e.status !== 401) {
          // error de red u otro: igual mandamos a login
        }
      } finally {
        setBooting(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (booting) return <div className="spinner">Cargando…</div>;

  // Ruta de login
  if (location.pathname === "/login") {
    if (me) return <Navigate to="/" replace />;
    return <Login />;
  }

  if (!me) return <Navigate to="/login" replace />;
  if (!ready) return <div className="spinner">Cargando datos…</div>;

  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Today />} />
        <Route path="/prueba" element={<TestDay />} />
        <Route path="/progreso" element={<Progress />} />
        <Route path="/alumnos" element={<Athletes />} />
        <Route path="/editar" element={<Editor />} />
        <Route path="/ejercicio/:dayKey/:exerciseId" element={<ExerciseView />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Shell>
  );
}
