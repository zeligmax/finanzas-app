import { useEffect, useState } from "react";
import api from "../api/client";
import { nifAviso } from "../utils/nif";

const today = () => new Date().toISOString().slice(0, 10);

const emptyInvoice = {
  numero: "",
  fecha: today(),
  concepto: "",
  cliente_nombre: "",
  cliente_nif: "",
  cliente_direccion: "",
  emisor_nombre: "",
  emisor_nif: "",
  emisor_direccion: "",
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

const MAX_MB = 8;

function EnviarFactura({ tipo }) {
  const [archivo, setArchivo] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [mensaje, setMensaje] = useState(null);
  const [error, setError] = useState(null);

  const enviar = async (e) => {
    e.preventDefault();
    if (!archivo) return;
    if (archivo.size > MAX_MB * 1024 * 1024) {
      setError(`El archivo supera los ${MAX_MB} MB.`);
      return;
    }
    setError(null);
    setMensaje(null);
    setEnviando(true);
    try {
      const datos = new FormData();
      datos.append("file", archivo);
      datos.append("tipo", tipo);
      const res = await api.post("/api/documents/upload", datos);
      setMensaje(res.data.mensaje);
      setArchivo(null);
      e.target.reset();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form onSubmit={enviar} className="card" style={{ maxWidth: 480 }}>
      <h2>Enviar una factura</h2>
      <p className="muted">
        Sube un PDF o una imagen (JPG, PNG...) de {tipo === "ingreso" ? "un ingreso" : "un gasto"}. Una persona la
        revisará y la añadirá a tu cuenta en menos de 24 h. No hace falta que rellenes nada más.
      </p>
      <div className="form-actions">
        <input
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,.webp,.tif,.tiff,application/pdf,image/*"
          onChange={(e) => {
            setArchivo(e.target.files[0] || null);
            setMensaje(null);
          }}
          disabled={enviando}
          style={{ width: "auto", flex: 1, minWidth: 0 }}
        />
        <button type="submit" disabled={!archivo || enviando} style={{ whiteSpace: "nowrap" }}>
          {enviando ? "Enviando..." : "Enviar"}
        </button>
      </div>
      {mensaje && <p style={{ color: "#15803d" }}>{mensaje}</p>}
      {error && <p className="error">Error: {String(error)}</p>}
    </form>
  );
}

function ContactoSelector({ tipo, onElegir }) {
  const [items, setItems] = useState(null);

  useEffect(() => {
    api
      .get("/api/contactos/", { params: { tipo } })
      .then((res) => setItems(res.data))
      .catch(() => setItems([]));
  }, [tipo]);

  if (!items || items.length === 0) return null;

  return (
    <div className="field">
      <label>{tipo === "cliente" ? "Elegir cliente guardado" : "Elegir proveedor guardado"}</label>
      <select
        value=""
        onChange={(e) => {
          const contacto = items.find((c) => c.id === e.target.value);
          if (contacto) onElegir(contacto);
          e.target.value = "";
        }}
      >
        <option value="">— Seleccionar —</option>
        {items.map((c) => (
          <option key={c.id} value={c.id}>
            {c.nombre}
          </option>
        ))}
      </select>
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

function InvoiceForm({ initial, perfil, onSaved, onCancel }) {
  const [form, setForm] = useState(
    initial
      ? toForm(emptyInvoice, initial)
      : {
          ...emptyInvoice,
          emisor_nombre: perfil?.full_name || "",
          emisor_nif: perfil?.nif || "",
          emisor_direccion: perfil?.direccion || "",
        }
  );
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
      <Field label="Concepto (para el PDF)">
        <input value={form.concepto} onChange={set("concepto")} placeholder="Ej. Diseño web - marzo 2026" />
      </Field>

      <ContactoSelector
        tipo="cliente"
        onElegir={(c) =>
          setForm({ ...form, cliente_nombre: c.nombre, cliente_nif: c.nif || "", cliente_direccion: c.direccion || "" })
        }
      />
      <Field label="Nombre pagador (cliente)">
        <input value={form.cliente_nombre} onChange={set("cliente_nombre")} required />
      </Field>
      <Field label="NIF/CIF pagador" warning={nifAviso(form.cliente_nif)}>
        <input value={form.cliente_nif} onChange={set("cliente_nif")} />
      </Field>
      <Field label="Dirección pagador">
        <input value={form.cliente_direccion} onChange={set("cliente_direccion")} />
      </Field>

      <Field label="Nombre cobrador (emisor)">
        <input value={form.emisor_nombre} onChange={set("emisor_nombre")} required />
      </Field>
      <Field label="NIF/CIF cobrador" warning={nifAviso(form.emisor_nif)}>
        <input value={form.emisor_nif} onChange={set("emisor_nif")} />
      </Field>
      <Field label="Dirección cobrador">
        <input value={form.emisor_direccion} onChange={set("emisor_direccion")} />
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

function ExpenseForm({ initial, onSaved, onCancel }) {
  const [form, setForm] = useState(initial ? toForm(emptyExpense, initial) : emptyExpense);
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

      <ContactoSelector
        tipo="proveedor"
        onElegir={(c) => setForm({ ...form, proveedor_nombre: c.nombre, proveedor_nif: c.nif || "" })}
      />
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

function RowActions({ onEdit, onDelete, extra }) {
  return (
    <td>
      <div className="actions">
        {extra}
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

function InvoiceList({ items, editingId, onEdit, onDelete, onDescargar, soloLectura }) {
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
            {!soloLectura && (
              <RowActions
                onEdit={() => onEdit(f)}
                onDelete={() => onDelete(f)}
                extra={
                  <button type="button" className="secondary small" onClick={() => onDescargar(f)}>
                    PDF
                  </button>
                }
              />
            )}
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

export default function DocumentsPage({ soloLectura = false, perfil }) {
  const [tab, setTab] = useState("ingreso");
  const [invoices, setInvoices] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [editing, setEditing] = useState(null);
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

  const editar = (item) => {
    setEditing(item);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const guardado = () => {
    setEditing(null);
    load();
  };

  const descargarPdf = async (factura) => {
    setError(null);
    try {
      const res = await api.get(`/api/invoices/${factura.id}/pdf`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `factura-${factura.numero}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
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

      {!soloLectura && <EnviarFactura tipo={tab} />}

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
            key={editing ? editing.id : "nuevo"}
            initial={editing}
            perfil={perfil}
            onSaved={guardado}
            onCancel={() => setEditing(null)}
          />
        ) : (
          <ExpenseForm
            key={editing ? editing.id : "nuevo"}
            initial={editing}
            onSaved={guardado}
            onCancel={() => setEditing(null)}
          />
        ))}

      {tab === "ingreso" ? (
        <section className="card">
          <h2>Ingresos registrados</h2>
          <InvoiceList
            items={invoices}
            editingId={editing?.id}
            onEdit={editar}
            onDelete={borrar}
            onDescargar={descargarPdf}
            soloLectura={soloLectura}
          />
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
