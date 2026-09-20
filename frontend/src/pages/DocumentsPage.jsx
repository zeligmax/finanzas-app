import { useEffect, useState } from "react";
import api from "../api/client";

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

function Field({ label, children }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
    </div>
  );
}

function InvoiceForm({ onCreated }) {
  const [form, setForm] = useState(emptyInvoice);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await api.post("/api/invoices/", {
        ...form,
        base_imponible: parseFloat(form.base_imponible) || 0,
        tipo_iva: parseFloat(form.tipo_iva) || 0,
        retencion_irpf_pct: parseFloat(form.retencion_irpf_pct) || 0,
      });
      setForm(emptyInvoice);
      onCreated();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="card" style={{ maxWidth: 480 }}>
      <Field label="Número de factura">
        <input value={form.numero} onChange={set("numero")} required />
      </Field>
      <Field label="Fecha">
        <input type="date" value={form.fecha} onChange={set("fecha")} required />
      </Field>

      <Field label="Nombre pagador (cliente)">
        <input value={form.cliente_nombre} onChange={set("cliente_nombre")} required />
      </Field>
      <Field label="NIF pagador">
        <input value={form.cliente_nif} onChange={set("cliente_nif")} />
      </Field>

      <Field label="Nombre cobrador (emisor)">
        <input value={form.emisor_nombre} onChange={set("emisor_nombre")} required />
      </Field>
      <Field label="NIF cobrador">
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

      <button type="submit" disabled={saving}>
        {saving ? "Guardando..." : "Añadir ingreso"}
      </button>
      {error && <p className="error">Error: {String(error)}</p>}
    </form>
  );
}

function ExpenseForm({ onCreated }) {
  const [form, setForm] = useState(emptyExpense);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await api.post("/api/expenses/", {
        ...form,
        base_imponible: parseFloat(form.base_imponible) || 0,
        tipo_iva: parseFloat(form.tipo_iva) || 0,
        retencion_irpf_pct: parseFloat(form.retencion_irpf_pct) || 0,
      });
      setForm(emptyExpense);
      onCreated();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="card" style={{ maxWidth: 480 }}>
      <Field label="Número de factura">
        <input value={form.numero_factura} onChange={set("numero_factura")} />
      </Field>
      <Field label="Fecha">
        <input type="date" value={form.fecha} onChange={set("fecha")} required />
      </Field>

      <Field label="Nombre cobrador (proveedor)">
        <input value={form.proveedor_nombre} onChange={set("proveedor_nombre")} required />
      </Field>
      <Field label="NIF cobrador">
        <input value={form.proveedor_nif} onChange={set("proveedor_nif")} />
      </Field>

      <Field label="Nombre pagador">
        <input value={form.pagador_nombre} onChange={set("pagador_nombre")} />
      </Field>
      <Field label="NIF pagador">
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

      <button type="submit" disabled={saving}>
        {saving ? "Guardando..." : "Añadir gasto"}
      </button>
      {error && <p className="error">Error: {String(error)}</p>}
    </form>
  );
}

function InvoiceList({ items }) {
  if (!items.length) return <p className="muted">Todavía no hay ingresos registrados.</p>;
  return (
    <table>
      <thead>
        <tr>
          {["Nº factura", "Fecha", "Pagador", "Base", "IVA %", "IRPF %", "Total"].map((h) => (
            <th key={h}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {items.map((f) => (
          <tr key={f.id}>
            <td>{f.numero}</td>
            <td>{f.fecha}</td>
            <td>{f.cliente_nombre}</td>
            <td>{f.base_imponible.toFixed(2)} €</td>
            <td>{f.tipo_iva}%</td>
            <td>{f.retencion_irpf_pct}%</td>
            <td>{f.total.toFixed(2)} €</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ExpenseList({ items }) {
  if (!items.length) return <p className="muted">Todavía no hay gastos registrados.</p>;
  return (
    <table>
      <thead>
        <tr>
          {["Nº factura", "Fecha", "Cobrador", "Categoría", "Base", "IVA %", "IRPF %"].map((h) => (
            <th key={h}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {items.map((g) => (
          <tr key={g.id}>
            <td>{g.numero_factura}</td>
            <td>{g.fecha}</td>
            <td>{g.proveedor_nombre}</td>
            <td>{g.categoria}</td>
            <td>{g.base_imponible.toFixed(2)} €</td>
            <td>{g.tipo_iva}%</td>
            <td>{g.retencion_irpf_pct}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function DocumentsPage() {
  const [tab, setTab] = useState("ingreso");
  const [invoices, setInvoices] = useState([]);
  const [expenses, setExpenses] = useState([]);
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

  return (
    <div>
      <h1>Documentos</h1>
      {error && <p className="error">Error: {String(error)}</p>}

      <div className="tabs">
        <div className={`tab ${tab === "ingreso" ? "active" : ""}`} onClick={() => setTab("ingreso")}>
          Ingreso (factura emitida)
        </div>
        <div className={`tab ${tab === "gasto" ? "active" : ""}`} onClick={() => setTab("gasto")}>
          Gasto (factura recibida)
        </div>
      </div>

      {tab === "ingreso" ? <InvoiceForm onCreated={load} /> : <ExpenseForm onCreated={load} />}

      {tab === "ingreso" ? (
        <section className="card">
          <h2>Ingresos registrados</h2>
          <InvoiceList items={invoices} />
        </section>
      ) : (
        <section className="card">
          <h2>Gastos registrados</h2>
          <ExpenseList items={expenses} />
        </section>
      )}
    </div>
  );
}
