import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import api from "../api/client";

const today = () => new Date().toISOString().slice(0, 10);

function Field({ label, children }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
    </div>
  );
}

function VistaArchivo({ docId, tipoArchivo }) {
  const [url, setUrl] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let objectUrl;
    api
      .get(`/api/builder/queue/${docId}/file`, { responseType: "blob" })
      .then((res) => {
        objectUrl = URL.createObjectURL(res.data);
        setUrl(objectUrl);
      })
      .catch((err) => setError(err.response?.data?.detail || err.message));
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [docId]);

  if (error) return <p className="error">No se puede mostrar el archivo: {error}</p>;
  if (!url) return <p className="muted">Cargando archivo...</p>;

  if (tipoArchivo === "application/pdf") {
    return <embed src={url} type="application/pdf" style={{ width: "100%", height: 700, border: "none" }} />;
  }
  return <img src={url} alt="Documento subido" style={{ width: "100%", height: "auto" }} />;
}

export default function BuilderReviewPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [doc, setDoc] = useState(null);
  const [form, setForm] = useState(null);
  const [error, setError] = useState(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    api
      .get(`/api/builder/queue/${id}`)
      .then((res) => {
        setDoc(res.data);
        const d = res.data.datos_extraidos || {};
        setForm({
          numero: d.numero || "",
          fecha: d.fecha || today(),
          emisor_nombre: d.emisor?.nombre || "",
          emisor_nif: d.emisor?.nif || "",
          receptor_nombre: d.receptor?.nombre || "",
          receptor_nif: d.receptor?.nif || "",
          base_imponible: d.base_imponible ?? "",
          tipo_iva: d.tipo_iva ?? 21,
          retencion_irpf_pct: d.retencion_irpf_pct ?? 0,
          categoria: "",
        });
      })
      .catch((err) => setError(err.response?.data?.detail || err.message));
  }, [id]);

  const set = (campo) => (e) => setForm({ ...form, [campo]: e.target.value });

  const aprobar = async (e) => {
    e.preventDefault();
    setError(null);
    setGuardando(true);
    try {
      const payload = {
        numero: form.numero,
        fecha: form.fecha,
        emisor: { nombre: form.emisor_nombre, nif: form.emisor_nif || null },
        receptor: { nombre: form.receptor_nombre, nif: form.receptor_nif || null },
        base_imponible: parseFloat(form.base_imponible) || 0,
        tipo_iva: parseFloat(form.tipo_iva) || 0,
        retencion_irpf_pct: parseFloat(form.retencion_irpf_pct) || 0,
        ...(doc.tipo === "gasto" ? { categoria: form.categoria } : {}),
      };
      await api.post(`/api/builder/queue/${id}/approve`, payload);
      navigate("/builder");
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setGuardando(false);
    }
  };

  const rechazar = async () => {
    const motivo = window.prompt("Motivo del rechazo (opcional):") || null;
    setError(null);
    setGuardando(true);
    try {
      await api.post(`/api/builder/queue/${id}/reject`, { motivo });
      navigate("/builder");
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setGuardando(false);
    }
  };

  if (error && !doc) return <p className="error">Error: {String(error)}</p>;
  if (!doc || !form) return <p className="muted">Cargando...</p>;

  const datos = doc.datos_extraidos || {};
  const yaRevisado = doc.estado !== "pendiente";

  return (
    <div>
      <p>
        <Link to="/builder">← Volver a la cola</Link>
      </p>
      <h1>Revisar documento</h1>

      <div className="card">
        <p>
          <strong>{doc.usuario.full_name || doc.usuario.email}</strong> ({doc.usuario.email}) · Subido como{" "}
          <strong>{doc.tipo === "ingreso" ? "ingreso" : "gasto"}</strong>
          {datos.tipo && datos.tipo !== doc.tipo && (
            <span className="warning" style={{ display: "inline" }}>
              {" "}
              — la IA lo detectó como {datos.tipo}: revisa si es correcto.
            </span>
          )}
        </p>
        {yaRevisado && (
          <p className="muted">
            Este documento ya está <strong>{doc.estado}</strong>
            {doc.motivo_rechazo && <> — motivo: {doc.motivo_rechazo}</>}. El archivo original ya no está disponible.
          </p>
        )}
        {datos.avisos?.length > 0 && (
          <>
            <p style={{ marginBottom: 4 }}>
              <strong>Avisos del análisis automático:</strong>
            </p>
            <ul style={{ marginTop: 0, paddingLeft: 18 }}>
              {datos.avisos.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          </>
        )}
      </div>

      <div className="layout">
        <div>
          {!yaRevisado && <VistaArchivo docId={id} tipoArchivo={doc.tipo_archivo} />}
        </div>

        <aside>
          <form onSubmit={aprobar} className="card">
            <h2>Datos {doc.tipo === "ingreso" ? "del ingreso" : "del gasto"}</h2>
            <Field label="Número de factura">
              <input value={form.numero} onChange={set("numero")} required disabled={yaRevisado} />
            </Field>
            <Field label="Fecha">
              <input type="date" value={form.fecha} onChange={set("fecha")} required disabled={yaRevisado} />
            </Field>
            <Field label={doc.tipo === "ingreso" ? "Nombre cobrador (emisor)" : "Nombre cobrador (proveedor)"}>
              <input value={form.emisor_nombre} onChange={set("emisor_nombre")} required disabled={yaRevisado} />
            </Field>
            <Field label="NIF/CIF cobrador">
              <input value={form.emisor_nif} onChange={set("emisor_nif")} disabled={yaRevisado} />
            </Field>
            <Field label={doc.tipo === "ingreso" ? "Nombre pagador (cliente)" : "Nombre pagador"}>
              <input value={form.receptor_nombre} onChange={set("receptor_nombre")} required disabled={yaRevisado} />
            </Field>
            <Field label="NIF/CIF pagador">
              <input value={form.receptor_nif} onChange={set("receptor_nif")} disabled={yaRevisado} />
            </Field>
            {doc.tipo === "gasto" && (
              <Field label="Categoría">
                <input
                  value={form.categoria}
                  onChange={set("categoria")}
                  required={!yaRevisado}
                  disabled={yaRevisado}
                  placeholder="suministros, software..."
                />
              </Field>
            )}
            <Field label="Base imponible (€)">
              <input
                type="number"
                step="0.01"
                value={form.base_imponible}
                onChange={set("base_imponible")}
                required
                disabled={yaRevisado}
              />
            </Field>
            <Field label="IVA (%)">
              <input type="number" step="0.01" value={form.tipo_iva} onChange={set("tipo_iva")} disabled={yaRevisado} />
            </Field>
            <Field label="IRPF (%)">
              <input
                type="number"
                step="0.01"
                value={form.retencion_irpf_pct}
                onChange={set("retencion_irpf_pct")}
                disabled={yaRevisado}
              />
            </Field>

            {!yaRevisado && (
              <div className="form-actions">
                <button type="submit" disabled={guardando}>
                  {guardando ? "Guardando..." : "Aprobar y crear"}
                </button>
                <button type="button" className="danger" onClick={rechazar} disabled={guardando}>
                  Rechazar
                </button>
              </div>
            )}
            {error && <p className="error">Error: {String(error)}</p>}
          </form>
        </aside>
      </div>
    </div>
  );
}
