import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";

export default function ClientesPage({ esGestor, clienteActivo, onElegirCliente }) {
  const navigate = useNavigate();
  const [clientes, setClientes] = useState(null);
  const [codigo, setCodigo] = useState("");
  const [error, setError] = useState(null);
  const [aviso, setAviso] = useState(null);

  const cargar = () =>
    api
      .get("/api/gestor/clients")
      .then((res) => setClientes(res.data))
      .catch((err) => setError(err.response?.data?.detail || err.message));

  useEffect(() => {
    if (esGestor) cargar();
  }, [esGestor]);

  if (!esGestor) {
    return (
      <div className="card">
        <h2>Clientes</h2>
        <p className="muted">Esta sección es solo para cuentas de gestor.</p>
      </div>
    );
  }

  const canjear = async (e) => {
    e.preventDefault();
    setError(null);
    setAviso(null);
    try {
      const res = await api.post("/api/gestor/redeem", { codigo });
      setCodigo("");
      setAviso(`Ahora tienes acceso de lectura a ${res.data.nombre || res.data.email}.`);
      cargar();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const ver = (cliente) => {
    onElegirCliente({ id: cliente.cliente_id, nombre: cliente.nombre, email: cliente.email });
    navigate("/documents");
  };

  const desvincular = async (cliente) => {
    if (!window.confirm(`¿Dejar de ver los datos de ${cliente.nombre || cliente.email}?`)) return;
    try {
      await api.delete(`/api/access/${cliente.acceso_id}`);
      if (clienteActivo?.id === cliente.cliente_id) onElegirCliente(null);
      cargar();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  return (
    <div>
      <h1>Clientes</h1>
      {error && <p className="error">Error: {String(error)}</p>}
      {aviso && <p style={{ color: "#15803d" }}>{aviso}</p>}

      <section className="card">
        <p className="muted">
          Pide a tu cliente que genere un código en su sección "Gestor" y escríbelo aquí. Tendrás acceso de solo
          lectura a sus facturas, gastos, impuestos y Renta hasta que él lo revoque.
        </p>
        <form onSubmit={canjear} className="row" style={{ alignItems: "flex-end" }}>
          <div className="field" style={{ marginBottom: 0, flex: 1, minWidth: 220 }}>
            <label>Código de invitación</label>
            <input value={codigo} onChange={(e) => setCodigo(e.target.value)} placeholder="ABCDE-FGHJK" required />
          </div>
          <button type="submit">Vincular cliente</button>
        </form>
      </section>

      <section className="card">
        <h2>Mis clientes</h2>
        {!clientes && !error && <p className="muted">Cargando...</p>}
        {clientes && clientes.length === 0 && <p className="muted">Todavía no tienes clientes vinculados.</p>}
        {clientes && clientes.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Cliente</th>
                <th>Correo</th>
                <th>NIF/CIF</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {clientes.map((c) => (
                <tr key={c.acceso_id} className={clienteActivo?.id === c.cliente_id ? "editing" : undefined}>
                  <td>{c.nombre || "—"}</td>
                  <td>{c.email}</td>
                  <td>{c.nif || "—"}</td>
                  <td>
                    <div className="actions">
                      <button type="button" className="small" onClick={() => ver(c)}>
                        Ver datos
                      </button>
                      <button type="button" className="secondary small" onClick={() => desvincular(c)}>
                        Desvincular
                      </button>
                    </div>
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
