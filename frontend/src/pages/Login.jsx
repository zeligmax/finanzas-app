import { useState } from "react";
import api from "../api/client";

export default function Login({ onLogin }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const submitLogin = async (e) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const data = new URLSearchParams();
      data.append("username", email);
      data.append("password", password);

      const res = await api.post("/api/auth/login", data);
      const token = res.data.access_token;
      if (token) {
        onLogin(token);
      } else {
        setError("Respuesta inválida del servidor");
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setSaving(false);
    }
  };

  const submitRegister = async (e) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const res = await api.post("/api/auth/register", {
        email,
        password,
        full_name: fullName || null,
      });
      const token = res.data.access_token;
      if (token) {
        onLogin(token);
      } else {
        setError("Respuesta inválida del servidor");
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card" style={{ maxWidth: 420 }}>
      <div className="tabs">
        <div className={`tab ${mode === "login" ? "active" : ""}`} onClick={() => setMode("login")}>
          Iniciar sesión
        </div>
        <div className={`tab ${mode === "register" ? "active" : ""}`} onClick={() => setMode("register")}>
          Crear cuenta
        </div>
      </div>

      {mode === "login" ? (
        <form onSubmit={submitLogin}>
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
      ) : (
        <form onSubmit={submitRegister}>
          <div className="field">
            <label>Nombre</label>
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </div>

          <div className="field">
            <label>Correo</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>

          <div className="field">
            <label>Contraseña</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={6}
              required
            />
          </div>

          <button type="submit" disabled={saving}>
            {saving ? "Creando cuenta..." : "Crear cuenta"}
          </button>
          {error && <p className="error">Error: {String(error)}</p>}
        </form>
      )}

      <p className="muted" style={{ marginTop: 12 }}>
        Tus facturas y gastos solo los ves tú, asociados a tu correo.
      </p>
    </div>
  );
}
