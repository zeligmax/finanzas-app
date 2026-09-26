import { useEffect, useState } from "react";
import api from "../api/client";
import { nifAviso } from "../utils/nif";

const today = () => new Date().toISOString().slice(0, 10);

const emptyInvoice = {
  numero: "",
  fecha: today(),
  cliente_nombre: "",
  cliente_nif: "",
  emisor_nombre: "",
  emisor_nif: "",
  base_imponible: "",
  tipo_iva: 21,
  retencion_irpf_pct: 0,
};

const emptyExpense = {
  numero_factura: "",
  fecha: today(),
  proveedor_nombre: "",
  proveedor_nif: "",
  pagador_nombre: "",
  pagador_nif: "",
  categoria: "",
  base_imponible: "",
  tipo_iva: 21,
  retencion_irpf_pct: 0,
};

const toForm = (empty, item) =>
  Object.fromEntries(Object.keys(empty).map((campo) => [campo, item[campo] ?? ""]));

const numeros = (form) => ({
  ...form,
  base_imponible: parseFloat(form.base_imponible) || 0,
  tipo_iva: parseFloat(form.tipo_iva) || 0,
  retencion_irpf_pct: parseFloat(form.retencion_irpf_pct) || 0,
});

const valor = (v) => (v === null || v === undefined ? "" : v);

function aFormulario(lectura, tipo) {
  const comunes = {
    fecha: lectura.fecha || today(),
    base_imponible: valor(lectura.base_imponible),
    tipo_iva: lectura.tipo_iva ?? 21,
    retencion_irpf_pct: lectura.retencion_irpf_pct ?? 0,
  };
  if (tipo === "ingreso") {
    return {
      ...comunes,
      numero: valor(lectura.numero),
      cliente_nombre: valor(lectura.receptor.nombre),
      cliente_nif: valor(lectura.receptor.nif),
      emisor_nombre: valor(lectura.emisor.nombre),
      emisor_nif: valor(lectura.emisor.nif),
    };
  }
  return {
    ...comunes,
    numero_factura: valor(lectura.numero),
    proveedor_nombre: valor(lectura.emisor.nombre),
    proveedor_nif: valor(lectura.emisor.nif),
    pagador_nombre: valor(lectura.receptor.nombre),
    pagador_nif: valor(lectura.receptor.nif),
  };
}

const MAX_MB = 8;

function LectorFactura({ onLeida, deshabilitado }) {
  const [archivo, setArchivo] = useState(null);
  const [leyendo, setLeyendo] = useState(false);
  const [error, setError] = useState(null);

  const leer = async (e) => {
    e.preventDefault();
    if (!archivo) return;
    if (archivo.size > MAX_MB * 1024 * 1024) {
      setError(`El archivo supera los ${MAX_MB} MB.`);
      return;
    }
    setError(null);
    setLeyendo(true);
    try {
      const datos = new FormData();
      datos.append("file", archivo);
      const res = await api.post("/api/documents/extract", datos);
      onLeida(res.data);
      setArchivo(null);
      e.target.reset();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLeyendo(false);
    }
  };

  return (
    <form onSubmit={leer} className="card" style={{ maxWidth: 480 }}>
      <h2>Leer una factura</h2>
      <p className="muted">
        Sube un PDF o una imagen (JPG, PNG...) en castellano, catalán o inglés y se rellenará el formulario para que
        lo revises. El archivo no se guarda.
      </p>
      <div className="form-actions">
        <input
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,.webp,.tif,.tiff,application/pdf,image/*"
          onChange={(e) => setArchivo(e.target.files[0] || null)}
          disabled={deshabilitado || leyendo}
          style={{ width: "auto", flex: 1, minWidth: 0 }}
        />
        <button type="submit" disabled={!archivo || leyendo || deshabilitado} style={{ whiteSpace: "nowrap" }}>
          {leyendo ? "Leyendo..." : "Leer factura"}
        </button>
      </div>
      {error && <p className="error">Error: {String(error)}</p>}
    </form>
  );
}

function ResultadoLectura({ lectura, tabActiva, onDescartar }) {
  const nombreTipo = { ingreso: "un ingreso (factura emitida)", gasto: "un gasto (factura recibida)" };
  return (
    <div className="banner" style={{ maxWidth: 480 }}>
      <strong>Datos leídos de la factura.</strong> Revísalos antes de guardar.
      {lectura.tipo ? (
        <p style={{ margin: "6px 0" }}>
          Se ha detectado como {nombreTipo[lectura.tipo]} porque tu NIF/CIF coincide con el{" "}
          {lectura.tipo === "ingreso" ? "del emisor" : "del cliente o pagador"}.
        </p>
      ) : (
        <p style={{ margin: "6px 0" }}>
          No se ha podido saber si es un ingreso o un gasto (falta tu NIF/CIF en Usuario, o no aparece en la
          factura). Se ha usado la pestaña {tabActiva === "ingreso" ? "Ingreso" : "Gasto"}; cámbiala si no es esa.
        </p>
      )}
      {tabActiva === "gasto" && (
        <p style={{ margin: "6px 0" }}>Recuerda indicar la <strong>categoría</strong> del gasto: no viene en la factura.</p>
      )}
      {lectura.avisos.length > 0 && (
        <ul style={{ margin: "6px 0", paddingLeft: 18 }}>
          {lectura.avisos.map((a, i) => (
            <li key={i}>{a}</li>
          ))}
        </ul>
      )}
      <details>
        <summary style={{ cursor: "pointer" }}>Ver el texto leído</summary>
        <pre style={{ whiteSpace: "pre-wrap", fontSize: 12, maxHeight: 220, overflow: "auto" }}>{lectura.texto}</pre>
      </details>
      <button type="button" className="secondary small" style={{ marginTop: 8 }} onClick={onDescartar}>
        Descartar y empezar en blanco
      </button>
    </div>
  );
}

function Field({ label, warning, children }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
      {warning && <small className="warning">{warning}</small>}
    </div>
  );
}

function FormActions({ editing, saving, textoAnadir, onCancel, error }) {
  return (
    <>
      <div className="form-actions">
        <button type="submit" disabled={saving}>
          {saving ? "Guardando..." : editing ? "Guardar cambios" : textoAnadir}
        </button>
        {editing && (
          <button type="button" className="secondary" onClick={onCancel}>
            Cancelar
          </button>
        )}
      </div>
      {error && <p className="error">Error: {String(error)}</p>}
    </>
  );
}

function InvoiceForm({ initial, prefill, onSaved, onCancel }) {
  const [form, setForm] = useState(initial ? toForm(emptyInvoice, initial) : { ...emptyInvoice, ...prefill });
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      if (initial) {
        await api.put(`/api/invoices/${initial.id}`, numeros(form));
      } else {
        await api.post("/api/invoices/", numeros(form));
        setForm(emptyInvoice);
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
      {initial && <h2>Editando factura {initial.numero}</h2>}
      <Field label="Número de factura">
        <input value={form.numero} onChange={set("numero")} required />
      </Field>
      <Field label="Fecha">
        <input type="date" value={form.fecha} onChange={set("fecha")} required />
      </Field>

      <Field label="Nombre pagador (cliente)">
        <input value={form.cliente_nombre} onChange={set("cliente_nombre")} required />
      </Field>
      <Field label="NIF/CIF pagador" warning={nifAviso(form.cliente_nif)}>
        <input value={form.cliente_nif} onChange={set("cliente_nif")} />
      </Field>

      <Field label="Nombre cobrador (emisor)">
        <input value={form.emisor_nombre} onChange={set("emisor_nombre")} required />
      </Field>
      <Field label="NIF/CIF cobrador" warning={nifAviso(form.emisor_nif)}>
        <input value={form.emisor_nif} onChange={set("emisor_nif")} />
      </Field>

      <Field label="Base imponible (€)">
        <input type="number" step="0.01" value={form.base_imponible} onChange={set("base_imponible")} required />
      </Field>
      <Field label="IVA cobrado (%)">
        <input type="number" step="0.01" value={form.tipo_iva} onChange={set("tipo_iva")} />
      </Field>
      <Field label="IRPF cobrado (%)">
        <input type="number" step="0.01" value={form.retencion_irpf_pct} onChange={set("retencion_irpf_pct")} />
      </Field>

      <FormActions
        editing={!!initial}
        saving={saving}
        textoAnadir="Añadir ingreso"
        onCancel={onCancel}
        error={error}
      />
    </form>
  );
}

function ExpenseForm({ initial, prefill, onSaved, onCancel }) {
  const [form, setForm] = useState(initial ? toForm(emptyExpense, initial) : { ...emptyExpense, ...prefill });
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      if (initial) {
        await api.put(`/api/expenses/${initial.id}`, numeros(form));
      } else {
        await api.post("/api/expenses/", numeros(form));
        setForm(emptyExpense);
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
      {initial && <h2>Editando gasto {initial.numero_factura || initial.proveedor_nombre}</h2>}
      <Field label="Número de factura">
        <input value={form.numero_factura} onChange={set("numero_factura")} />
      </Field>
      <Field label="Fecha">
        <input type="date" value={form.fecha} onChange={set("fecha")} required />
      </Field>

      <Field label="Nombre cobrador (proveedor)">
        <input value={form.proveedor_nombre} onChange={set("proveedor_nombre")} required />
      </Field>
      <Field label="NIF/CIF cobrador" warning={nifAviso(form.proveedor_nif)}>
        <input value={form.proveedor_nif} onChange={set("proveedor_nif")} />
      </Field>

      <Field label="Nombre pagador">
        <input value={form.pagador_nombre} onChange={set("pagador_nombre")} />
      </Field>
      <Field label="NIF/CIF pagador" warning={nifAviso(form.pagador_nif)}>
        <input value={form.pagador_nif} onChange={set("pagador_nif")} />
      </Field>

      <Field label="Categoría">
        <input value={form.categoria} onChange={set("categoria")} required placeholder="suministros, software..." />
      </Field>

      <Field label="Base imponible (€)">
        <input type="number" step="0.01" value={form.base_imponible} onChange={set("base_imponible")} required />
      </Field>
      <Field label="IVA cobrado (%)">
        <input type="number" step="0.01" value={form.tipo_iva} onChange={set("tipo_iva")} />
      </Field>
      <Field label="IRPF cobrado (%)">
        <input type="number" step="0.01" value={form.retencion_irpf_pct} onChange={set("retencion_irpf_pct")} />
      </Field>

      <FormActions
        editing={!!initial}
        saving={saving}
        textoAnadir="Añadir gasto"
        onCancel={onCancel}
        error={error}
      />
    </form>
  );
}

function RowActions({ onEdit, onDelete }) {
  return (
    <td>
      <div className="actions">
        <button type="button" className="secondary small" onClick={onEdit}>
          Editar
        </button>
        <button type="button" className="danger small" onClick={onDelete}>
          Borrar
        </button>
      </div>
    </td>
  );
}

function InvoiceList({ items, editingId, onEdit, onDelete, soloLectura }) {
  if (!items.length) return <p className="muted">Todavía no hay ingresos registrados.</p>;
  return (
    <table>
      <thead>
        <tr>
          {["Nº factura", "Fecha", "Pagador", "Base", "IVA %", "IRPF %", "Total", ...(soloLectura ? [] : [""])].map((h, i) => (
            <th key={i}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {items.map((f) => (
          <tr key={f.id} className={editingId === f.id ? "editing" : undefined}>
            <td>{f.numero}</td>
            <td>{f.fecha}</td>
            <td>{f.cliente_nombre}</td>
            <td>{f.base_imponible.toFixed(2)} €</td>
            <td>{f.tipo_iva}%</td>
            <td>{f.retencion_irpf_pct}%</td>
            <td>{f.total.toFixed(2)} €</td>
            {!soloLectura && <RowActions onEdit={() => onEdit(f)} onDelete={() => onDelete(f)} />}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ExpenseList({ items, editingId, onEdit, onDelete, soloLectura }) {
  if (!items.length) return <p className="muted">Todavía no hay gastos registrados.</p>;
  return (
    <table>
      <thead>
        <tr>
          {["Nº factura", "Fecha", "Cobrador", "Categoría", "Base", "IVA %", "IRPF %", ...(soloLectura ? [] : [""])].map((h, i) => (
            <th key={i}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {items.map((g) => (
          <tr key={g.id} className={editingId === g.id ? "editing" : undefined}>
            <td>{g.numero_factura}</td>
            <td>{g.fecha}</td>
            <td>{g.proveedor_nombre}</td>
            <td>{g.categoria}</td>
            <td>{g.base_imponible.toFixed(2)} €</td>
            <td>{g.tipo_iva}%</td>
            <td>{g.retencion_irpf_pct}%</td>
            {!soloLectura && <RowActions onEdit={() => onEdit(g)} onDelete={() => onDelete(g)} />}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function DocumentsPage({ soloLectura = false }) {
  const [tab, setTab] = useState("ingreso");
  const [invoices, setInvoices] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [editing, setEditing] = useState(null);
  const [lectura, setLectura] = useState(null);
  const [lecturaId, setLecturaId] = useState(0);
  const [error, setError] = useState(null);

  const load = () => {
    Promise.all([api.get("/api/invoices/"), api.get("/api/expenses/")])
      .then(([invRes, expRes]) => {
        setInvoices(invRes.data);
        setExpenses(expRes.data);
      })
      .catch((err) => setError(err.response?.data?.detail || err.message));
  };

  useEffect(load, []);

  const cambiarTab = (nueva) => {
    setTab(nueva);
    setEditing(null);
  };

  const factura_leida = (datos) => {
    setEditing(null);
    setLectura(datos);
    setLecturaId((n) => n + 1);
    if (datos.tipo) setTab(datos.tipo);
  };

  const editar = (item) => {
    setEditing(item);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const guardado = () => {
    setEditing(null);
    setLectura(null);
    load();
  };

  const borrar = async (item) => {
    const esIngreso = tab === "ingreso";
    const nombre = esIngreso ? `la factura ${item.numero}` : `el gasto ${item.numero_factura || item.proveedor_nombre}`;
    if (!window.confirm(`¿Borrar ${nombre}? Esta acción no se puede deshacer.`)) return;

    setError(null);
    try {
      await api.delete(`${esIngreso ? "/api/invoices" : "/api/expenses"}/${item.id}`);
      if (editing?.id === item.id) setEditing(null);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  return (
    <div>
      <h1>Documentos</h1>
      {error && <p className="error">Error: {String(error)}</p>}

      {!soloLectura && <LectorFactura onLeida={factura_leida} />}
      {!soloLectura && lectura && (
        <ResultadoLectura lectura={lectura} tabActiva={tab} onDescartar={() => setLectura(null)} />
      )}

      <div className="tabs">
        <div className={`tab ${tab === "ingreso" ? "active" : ""}`} onClick={() => cambiarTab("ingreso")}>
          Ingreso (factura emitida)
        </div>
        <div className={`tab ${tab === "gasto" ? "active" : ""}`} onClick={() => cambiarTab("gasto")}>
          Gasto (factura recibida)
        </div>
      </div>

      {!soloLectura &&
        (tab === "ingreso" ? (
          <InvoiceForm
            key={editing ? editing.id : `nuevo-${lecturaId}-${lectura ? "leida" : "vacia"}`}
            initial={editing}
            prefill={lectura ? aFormulario(lectura, "ingreso") : undefined}
            onSaved={guardado}
            onCancel={() => setEditing(null)}
          />
        ) : (
          <ExpenseForm
            key={editing ? editing.id : `nuevo-${lecturaId}-${lectura ? "leida" : "vacia"}`}
            initial={editing}
            prefill={lectura ? aFormulario(lectura, "gasto") : undefined}
            onSaved={guardado}
            onCancel={() => setEditing(null)}
          />
        ))}

      {tab === "ingreso" ? (
        <section className="card">
          <h2>Ingresos registrados</h2>
          <InvoiceList items={invoices} editingId={editing?.id} onEdit={editar} onDelete={borrar} soloLectura={soloLectura} />
        </section>
      ) : (
        <section className="card">
          <h2>Gastos registrados</h2>
          <ExpenseList items={expenses} editingId={editing?.id} onEdit={editar} onDelete={borrar} soloLectura={soloLectura} />
        </section>
      )}
    </div>
  );
}
