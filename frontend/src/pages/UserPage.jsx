import { useEffect, useState } from "react";
import api from "../api/client";
import { nifAviso } from "../utils/nif";

export default function UserPage() {
  const [form, setForm] = useState(null);
  const [email, setEmail] = useState("");
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .get("/api/users/me")
      .then((res) => {
        setEmail(res.data.email);
        setForm({
          full_name: res.data.full_name || "",
          nif: res.data.nif || "",
          cuota_autonomos_mensual: res.data.cuota_autonomos_mensual,
        });
      })
      .catch((err) => setError(err.response?.data?.detail || err.message));
  }, []);

  const set = (field) => (e) => {
    setSaved(false);
    setForm({ ...form, [field]: e.target.value });
  };

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setSaved(false);
    setSaving(true);
    try {
      await api.put("/api/users/me", {
        ...form,
        cuota_autonomos_mensual: parseFloat(form.cuota_autonomos_mensual) || 0,
      });
      setSaved(true);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(Array.isArray(detail) ? "Revisa los datos introducidos" : detail || err.message);
    } finally {
      setSaving(false);
    }
  };

  const aviso = form ? nifAviso(form.nif) : null;

  return (
    <div>
      <h1>Usuario</h1>
      {error && <p className="error">Error: {String(error)}</p>}
      {!form && !error && <p className="muted">Cargando...</p>}

      {form && (
        <form onSubmit={submit} className="card" style={{ maxWidth: 480 }}>
          <div className="field">
            <label>Correo</label>
            <input value={email} disabled />
          </div>

          <div className="field">
            <label>Nombre completo</label>
            <input value={form.full_name} onChange={set("full_name")} />
          </div>

          <div className="field">
            <label>NIF/CIF</label>
            <input value={form.nif} onChange={set("nif")} />
            {aviso && <small className="warning">{aviso}</small>}
          </div>

          <div className="field">
            <label>Cuota de autónomos media mensual (€)</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={form.cuota_autonomos_mensual}
              onChange={set("cuota_autonomos_mensual")}
            />
            <small className="muted">
              Se descuenta como gasto deducible: ×12 en Renta y ×3 en cada modelo 130 trimestral.
            </small>
          </div>

          <button type="submit" disabled={saving}>
            {saving ? "Guardando..." : "Guardar"}
          </button>
          {saved && <p style={{ color: "#15803d" }}>Datos guardados.</p>}
        </form>
      )}
    </div>
  );
}
