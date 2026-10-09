import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api from "../api/client";

export default function VerificarPage() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [estado, setEstado] = useState("comprobando"); // "comprobando" | "ok" | "error"
  const [mensaje, setMensaje] = useState("");

  useEffect(() => {
    if (!token) {
      setEstado("error");
      setMensaje("Falta el código de confirmación en el enlace.");
      return;
    }
    api
      .get(`/api/auth/verify/${token}`)
      .then((res) => {
        setEstado("ok");
        setMensaje(res.data.mensaje);
      })
      .catch((err) => {
        setEstado("error");
        setMensaje(err.response?.data?.detail || err.message);
      });
  }, [token]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Finanzas Autónomo</h1>
      </header>
      <main>
        <div className="card" style={{ maxWidth: 420 }}>
          <h2>Confirmación de correo</h2>
          {estado === "comprobando" && <p className="muted">Comprobando...</p>}
          {estado === "ok" && (
            <>
              <p style={{ color: "#15803d" }}>{mensaje}</p>
              <Link to="/">Ir a iniciar sesión</Link>
            </>
          )}
          {estado === "error" && (
            <>
              <p className="error">{mensaje}</p>
              <p className="muted">
                Si el enlace ha caducado, inicia sesión y pide que te reenvíen el correo desde el aviso que te
                saldrá.
              </p>
              <Link to="/">Ir a iniciar sesión</Link>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
