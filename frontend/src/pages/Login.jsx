import { useState } from "react";
import api from "../api/client";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
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
    }
  };

  return (
    <div className="card" style={{ maxWidth: 420 }}>
      <h2>Iniciar sesión</h2>
      <form onSubmit={submit}>
        <div className="field">
          <label>Correo</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>

        <div className="field">
          <label>Contraseña</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>

        <button type="submit">Entrar</button>
        {error && <p className="error">Error: {String(error)}</p>}
      </form>

      <p className="muted" style={{ marginTop: 12 }}>
        Si no tienes usuario, crea uno en la base de datos o usa las pruebas del backend.
      </p>
    </div>
  );
}
