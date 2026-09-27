import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";

const fechaLarga = (iso) => new Date(iso + "Z").toLocaleString("es-ES");

export default function BuilderQueuePage() {
  const navigate = useNavigate();
  const [estado, setEstado] = useState("pendiente");
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);

  const cargar = () => {
    setItems(null);
    api
      .get("/api/builder/queue", { params: { estado } })
      .then((res) => setItems(res.data))
      .catch((err) => setError(err.response?.data?.detail || err.message));
  };

  useEffect(cargar, [estado]);

  return (
    <div>
      <h1>Cola de revisión</h1>
      {error && <p className="error">Error: {String(error)}</p>}

      <div className="card row">
        <label className="field" style={{ marginBottom: 0 }}>
          Estado
          <select value={estado} onChange={(e) => setEstado(e.target.value)}>
            <option value="pendiente">Pendientes</option>
            <option value="aprobado">Aprobados</option>
            <option value="rechazado">Rechazados</option>
          </select>
        </label>
      </div>

      <section className="card">
        {!items && !error && <p className="muted">Cargando...</p>}
        {items && items.length === 0 && <p className="muted">No hay documentos en este estado.</p>}
        {items && items.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Usuario</th>
                <th>Tipo</th>
                <th>Archivo</th>
                <th>Subido</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr key={it.id}>
                  <td>
                    {it.usuario.full_name || it.usuario.email}
                    <br />
                    <small className="muted">{it.usuario.email}</small>
                  </td>
                  <td>{it.tipo === "ingreso" ? "Ingreso" : "Gasto"}</td>
                  <td>{it.nombre_archivo}</td>
                  <td>{fechaLarga(it.creado_en)}</td>
                  <td>
                    <button type="button" className="small" onClick={() => navigate(`/builder/${it.id}`)}>
                      {it.estado === "pendiente" ? "Revisar" : "Ver"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
