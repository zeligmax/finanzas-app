import { useEffect, useState } from "react";
import api from "../api/client";

const anioActual = new Date().getFullYear();
const trimestreActual = Math.ceil((new Date().getMonth() + 1) / 3);

export default function TaxesPage() {
  const [anio, setAnio] = useState(anioActual);
  const [trimestre, setTrimestre] = useState(trimestreActual);
  const [iva, setIva] = useState(null);
  const [modelo130, setModelo130] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setError(null);
    setIva(null);
    setModelo130(null);
    Promise.all([
      api.get(`/api/taxes/iva/${anio}/${trimestre}`),
      api.get(`/api/taxes/modelo130/${anio}/${trimestre}`),
    ])
      .then(([ivaRes, m130Res]) => {
        setIva(ivaRes.data);
        setModelo130(m130Res.data);
      })
      .catch((err) => setError(err.response?.data?.detail || err.message));
  }, [anio, trimestre]);

  return (
    <div>
      <h1>Impuestos</h1>

      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 20 }}>
        <label>
          Año{" "}
          <input
            type="number"
            value={anio}
            onChange={(e) => setAnio(parseInt(e.target.value, 10) || anioActual)}
            style={{ width: 80 }}
          />
        </label>
        <label>
          Trimestre{" "}
          <select value={trimestre} onChange={(e) => setTrimestre(parseInt(e.target.value, 10))}>
            {[1, 2, 3, 4].map((t) => (
              <option key={t} value={t}>
                T{t}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && <p style={{ color: "crimson" }}>Error: {String(error)}</p>}
      {!error && (!iva || !modelo130) && <p>Cargando...</p>}

      {iva && modelo130 && (
        <>
          <section>
            <h2>IVA (modelo 303)</h2>
            <p>IVA devengado: {iva.iva_devengado.toFixed(2)} €</p>
            <p>Prorrata: {iva.prorrata_pct.toFixed(0)}%</p>
            <p>IVA soportado deducible: {iva.iva_soportado_deducible.toFixed(2)} €</p>
            <p>
              <strong>
                Resultado: {iva.resultado.toFixed(2)} € ({iva.a_ingresar ? "a ingresar" : "a compensar"})
              </strong>
            </p>
          </section>

          <section>
            <h2>IRPF · pago fraccionado (modelo 130)</h2>
            <p>Rendimiento neto del trimestre: {modelo130.rendimiento_neto_trimestre.toFixed(2)} €</p>
            <p>Rendimiento neto acumulado en el año: {modelo130.rendimiento_neto_acumulado.toFixed(2)} €</p>
            <p>
              <strong>A ingresar: {modelo130.resultado.toFixed(2)} €</strong>
            </p>
          </section>
        </>
      )}
    </div>
  );
}
