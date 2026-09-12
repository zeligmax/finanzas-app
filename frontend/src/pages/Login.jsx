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
    <div style={{ maxWidth: 480 }}>
      <h2>Iniciar sesión</h2>
      <form onSubmit={submit}>
        <div style={{ marginBottom: 8 }}>
          <label>Correo</label>
          <br />
          <input value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>

        <div style={{ marginBottom: 8 }}>
          <label>Contraseña</label>
          <br />
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>

        <button type="submit">Entrar</button>
        {error && (
          <p style={{ color: "crimson" }}>Error: {String(error)}</p>
        )}
      </form>

      <p style={{ marginTop: 12 }}>
        Si no tienes usuario, crea uno en la base de datos o usa las pruebas del backend.
      </p>
    </div>
  );
}
