import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";

export default function BuilderLoginScreen({ onLogin }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const data = new URLSearchParams();
      data.append("username", email);
      data.append("password", password);
      const res = await api.post("/api/auth/login", data);
      const token = res.data.access_token;

      const perfil = await api.get("/api/users/me", { headers: { Authorization: `Bearer ${token}` } });
      if (perfil.data.role !== "builder") {
        setError("Esta cuenta no tiene acceso Builder.");
        return;
      }
      onLogin(token);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Finanzas Autónomo · Builder</h1>
        <button className="secondary" onClick={() => navigate("/")}>
          Login normal
        </button>
      </header>
      <main>
        <div className="card" style={{ maxWidth: 420 }}>
          <h2>Acceso Builder</h2>
          <p className="muted">Solo para cuentas de personal interno.</p>
          <form onSubmit={submit}>
            <div className="field">
              <label>Correo</label>
              <input value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div className="field">
              <label>Contraseña</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
            <button type="submit" disabled={saving}>
              {saving ? "Entrando..." : "Entrar"}
            </button>
            {error && <p className="error">Error: {String(error)}</p>}
          </form>
        </div>
      </main>
    </div>
  );
}
