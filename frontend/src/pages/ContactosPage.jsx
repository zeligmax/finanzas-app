import { useEffect, useState } from "react";
import api from "../api/client";

const vacio = { tipo: "cliente", nombre: "", nif: "", direccion: "" };

function ContactoForm({ tipo, initial, onSaved, onCancel }) {
  const [form, setForm] = useState(initial ? { ...vacio, ...initial } : { ...vacio, tipo });
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const set = (campo) => (e) => setForm({ ...form, [campo]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const payload = { ...form, nif: form.nif || null, direccion: form.direccion || null };
      if (initial) {
        await api.put(`/api/contactos/${initial.id}`, payload);
      } else {
        await api.post("/api/contactos/", payload);
        setForm({ ...vacio, tipo });
      }
      onSaved();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="card" style={{ maxWidth: 480 }}>
      {initial && <h2>Editando {tipo === "cliente" ? "cliente" : "proveedor"}</h2>}
      <div className="field">
        <label>Nombre</label>
        <input value={form.nombre} onChange={set("nombre")} required />
      </div>
      <div className="field">
        <label>NIF/CIF</label>
        <input value={form.nif} onChange={set("nif")} />
      </div>
      <div className="field">
        <label>Dirección</label>
        <input value={form.direccion} onChange={set("direccion")} placeholder="Calle, número, código postal, ciudad" />
      </div>
      <div className="form-actions">
        <button type="submit" disabled={saving}>
          {saving ? "Guardando..." : initial ? "Guardar cambios" : "Añadir"}
        </button>
        {initial && (
          <button type="button" className="secondary" onClick={onCancel}>
            Cancelar
          </button>
        )}
      </div>
      {error && <p className="error">Error: {String(error)}</p>}
    </form>
  );
}

export default function ContactosPage() {
  const [tipo, setTipo] = useState("cliente");
  const [items, setItems] = useState(null);
  const [editando, setEditando] = useState(null);
  const [error, setError] = useState(null);

  const cargar = () => {
    api
      .get("/api/contactos/", { params: { tipo } })
      .then((res) => setItems(res.data))
      .catch((err) => setError(err.response?.data?.detail || err.message));
  };

  useEffect(() => {
    setItems(null);
    setEditando(null);
    cargar();
  }, [tipo]);

  const guardado = () => {
    setEditando(null);
    cargar();
  };

  const borrar = async (contacto) => {
    if (!window.confirm(`¿Borrar "${contacto.nombre}"? Las facturas/gastos ya creados no cambian.`)) return;
    try {
      await api.delete(`/api/contactos/${contacto.id}`);
      if (editando?.id === contacto.id) setEditando(null);
      cargar();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  return (
    <div>
      <h1>Contactos</h1>
      <p className="muted">
        Guarda aquí tus clientes y proveedores habituales. Al crear una factura o un gasto podrás elegirlos y solo
        tendrás que cambiar la base imponible.
      </p>
      {error && <p className="error">Error: {String(error)}</p>}

      <div className="tabs">
        <div className={`tab ${tipo === "cliente" ? "active" : ""}`} onClick={() => setTipo("cliente")}>
          Clientes
        </div>
        <div className={`tab ${tipo === "proveedor" ? "active" : ""}`} onClick={() => setTipo("proveedor")}>
          Proveedores
        </div>
      </div>

      <ContactoForm
        key={editando ? editando.id : `nuevo-${tipo}`}
        tipo={tipo}
        initial={editando}
        onSaved={guardado}
        onCancel={() => setEditando(null)}
      />

      <section className="card">
        <h2>{tipo === "cliente" ? "Clientes guardados" : "Proveedores guardados"}</h2>
        {!items && !error && <p className="muted">Cargando...</p>}
        {items && items.length === 0 && <p className="muted">Todavía no has guardado ninguno.</p>}
        {items && items.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>NIF/CIF</th>
                <th>Dirección</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id} className={editando?.id === c.id ? "editing" : undefined}>
                  <td>{c.nombre}</td>
                  <td>{c.nif || "—"}</td>
                  <td>{c.direccion || "—"}</td>
                  <td>
                    <div className="actions">
                      <button type="button" className="secondary small" onClick={() => setEditando(c)}>
                        Editar
                      </button>
                      <button type="button" className="danger small" onClick={() => borrar(c)}>
                        Borrar
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
