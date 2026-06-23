import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api.js";
import { useStore } from "../state/store.jsx";

export default function Login() {
  const { setMe, loadAll } = useStore();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const u = await api.post("/api/auth/login", { email, password });
      setMe(u);
      await loadAll();
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Error al entrar");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={submit}>
        <div className="brand center" style={{ marginBottom: 6 }}>Tablero<span className="dot">.</span></div>
        <div className="muted center" style={{ marginBottom: 16 }}>del Entrenador</div>
        <div className="field">
          <label htmlFor="email">Correo</label>
          <input id="email" type="email" autoComplete="username" value={email}
            onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="field">
          <label htmlFor="password">Contraseña</label>
          <input id="password" type="password" autoComplete="current-password" value={password}
            onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <button className="btn" style={{ width: "100%" }} disabled={busy}>
          {busy ? "Entrando…" : "Entrar"}
        </button>
        {error && <div className="error center">{error}</div>}
      </form>
    </div>
  );
}
