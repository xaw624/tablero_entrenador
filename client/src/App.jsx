import { useCallback, useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, ApiError, setUnauthorizedHandler } from "./api.js";
import { useStore } from "./state/store.jsx";
import TabBar from "./components/TabBar.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
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
      <ErrorBoundary>{children}</ErrorBoundary>
    </div>
  );
}

function LoadError({ detail, onRetry, onLogout }) {
  return (
    <div className="login-wrap">
      <div className="card login-card center">
        <div className="block-title" style={{ marginTop: 0 }}>No se pudieron cargar los datos</div>
        <p className="muted">{detail}</p>
        <p className="muted" style={{ fontSize: 12 }}>
          Si acabas de actualizar el servidor, asegúrate de haber reiniciado el servicio
          (<code>systemctl restart tablero-entrenador</code>).
        </p>
        <button className="btn" onClick={onRetry}>Reintentar</button>
        <button className="btn ghost" style={{ marginLeft: 8 }} onClick={onLogout}>Salir</button>
      </div>
    </div>
  );
}

export default function App() {
  const { me, setMe, ready, loadAll, reset } = useStore();
  const [booting, setBooting] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    setUnauthorizedHandler(() => {
      reset();
      navigate("/login");
    });
  }, [navigate, reset]);

  const boot = useCallback(async () => {
    setLoadError(null);
    try {
      const u = await api.get("/api/auth/me");
      setMe(u);
    } catch {
      // 401 → onUnauthorized redirige a login; error de red → también queda en login.
      setBooting(false);
      return;
    }
    try {
      await loadAll();
    } catch (e) {
      // No dejamos la app colgada en el spinner: mostramos error con reintento.
      setLoadError(e instanceof ApiError ? e.detail : "No se pudo conectar con el servidor.");
    } finally {
      setBooting(false);
    }
  }, [loadAll, setMe, reset]);

  useEffect(() => {
    boot();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const retry = useCallback(async () => {
    setLoadError(null);
    try {
      await loadAll();
    } catch (e) {
      setLoadError(e instanceof ApiError ? e.detail : "No se pudo conectar con el servidor.");
    }
  }, [loadAll]);

  const logout = useCallback(async () => {
    try { await api.post("/api/auth/logout"); } catch { /* ignore */ }
    reset();
    navigate("/login");
  }, [reset, navigate]);

  if (booting) return <div className="spinner">Cargando…</div>;

  // Ruta de login
  if (location.pathname === "/login") {
    if (me) return <Navigate to="/" replace />;
    return <Login />;
  }

  if (!me) return <Navigate to="/login" replace />;
  if (!ready) {
    if (loadError) return <LoadError detail={loadError} onRetry={retry} onLogout={logout} />;
    return <div className="spinner">Cargando datos…</div>;
  }

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
