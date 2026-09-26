import { useEffect, useState } from "react";
import api from "../api/client";

const fechaLarga = (iso) => new Date(iso + "Z").toLocaleDateString("es-ES");

export default function AccesoPage() {
  const [accesos, setAccesos] = useState(null);
  const [etiqueta, setEtiqueta] = useState("");
  const [error, setError] = useState(null);
  const [copiado, setCopiado] = useState(null);

  const cargar = () =>
    api
      .get("/api/access/")
      .then((res) => setAccesos(res.data))
      .catch((err) => setError(err.response?.data?.detail || err.message));

  useEffect(() => {
    cargar();
  }, []);

  const crear = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/api/access/invitations", { etiqueta });
      setEtiqueta("");
      cargar();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const revocar = async (acceso) => {
    const texto =
      acceso.estado === "pendiente"
        ? "¿Cancelar esta invitación? El código dejará de funcionar."
        : `¿Revocar el acceso de ${acceso.gestor?.email}? Dejará de ver tus datos.`;
    if (!window.confirm(texto)) return;
    try {
      await api.delete(`/api/access/${acceso.id}`);
      cargar();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const copiar = async (codigo) => {
    try {
      await navigator.clipboard.writeText(codigo);
      setCopiado(codigo);
    } catch {
      setCopiado(null);
    }
  };

  return (
    <div>
      <h1>Acceso de tu gestor</h1>
      {error && <p className="error">Error: {String(error)}</p>}

      <section className="card">
        <p>
          Tu gestor podrá ver, <strong>solo en lectura</strong>, tus facturas, gastos, impuestos y Renta. No podrá
          modificar nada y puedes quitarle el acceso cuando quieras.
        </p>
        <p className="muted">
          Genera un código y compártelo con tu gestor por un canal de confianza. Solo sirve una vez y caduca a los 7
          días. Tu gestor debe tener una cuenta de tipo gestor y canjearlo en su sección Clientes.
        </p>
        <form onSubmit={crear} className="row" style={{ alignItems: "flex-end" }}>
          <div className="field" style={{ marginBottom: 0, flex: 1, minWidth: 220 }}>
            <label>Nombre para reconocerlo (opcional)</label>
            <input value={etiqueta} onChange={(e) => setEtiqueta(e.target.value)} placeholder="Mi gestoría" />
          </div>
          <button type="submit">Generar código</button>
        </form>
      </section>

      <section className="card">
        <h2>Invitaciones y accesos</h2>
        {!accesos && !error && <p className="muted">Cargando...</p>}
        {accesos && accesos.length === 0 && <p className="muted">Todavía no has dado acceso a ningún gestor.</p>}
        {accesos && accesos.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Estado</th>
                <th>Detalle</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {accesos.map((a) => (
                <tr key={a.id}>
                  <td>{a.etiqueta || "—"}</td>
                  <td>{a.estado === "pendiente" ? "Pendiente" : "Con acceso"}</td>
                  <td>
                    {a.estado === "pendiente" ? (
                      <>
                        <span className="code">{a.codigo}</span>{" "}
                        <button type="button" className="secondary small" onClick={() => copiar(a.codigo)}>
                          {copiado === a.codigo ? "Copiado" : "Copiar"}
                        </button>
                        <br />
                        <small className="muted">Caduca el {fechaLarga(a.expires_at)}</small>
                      </>
                    ) : (
                      <>
                        {a.gestor?.nombre || a.gestor?.email}
                        <br />
                        <small className="muted">{a.gestor?.email}</small>
                      </>
                    )}
                  </td>
                  <td>
                    <button type="button" className="danger small" onClick={() => revocar(a)}>
                      {a.estado === "pendiente" ? "Cancelar" : "Revocar"}
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
