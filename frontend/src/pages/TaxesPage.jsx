import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";
import useResumenAnual from "../hooks/useResumenAnual";

const anioActual = new Date().getFullYear();
const trimestreActual = Math.ceil((new Date().getMonth() + 1) / 3);

function ResumenRenta({ anio }) {
  const { renta, ivaAnual, totalPagosFraccionados, totalAnual, cargado, error } = useResumenAnual(anio);

  return (
    <section className="card">
      <h2>Resumen Renta {anio}</h2>
      {error && <p className="error">Error: {String(error)}</p>}
      {!error && !cargado && <p className="muted">Cargando...</p>}
      {cargado && (
        <>
          <table>
            <tbody>
              <tr>
                <td>IVA anual</td>
                <td>{ivaAnual.toFixed(2)} €</td>
              </tr>
              <tr>
                <td>IRPF ingresado</td>
                <td>{totalPagosFraccionados.toFixed(2)} €</td>
              </tr>
              <tr>
                <td>Modelo 100</td>
                <td>{renta.resultado.toFixed(2)} €</td>
              </tr>
              <tr>
                <td>IRPF medio</td>
                <td>{renta.tipo_medio_pct.toFixed(2)} %</td>
              </tr>
            </tbody>
          </table>
          <p style={{ marginTop: 12 }}>
            <strong>
              Total: {totalAnual.toFixed(2)} € ({totalAnual >= 0 ? "a abonar" : "a favor"})
            </strong>
          </p>
          <Link to="/renta">Ver detalle en Renta →</Link>
        </>
      )}
    </section>
  );
}

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

      <div className="card row">
        <label className="field" style={{ marginBottom: 0 }}>
          Año
          <input
            type="number"
            value={anio}
            onChange={(e) => setAnio(parseInt(e.target.value, 10) || anioActual)}
            style={{ width: 90 }}
          />
        </label>
        <label className="field" style={{ marginBottom: 0 }}>
          Trimestre
          <select value={trimestre} onChange={(e) => setTrimestre(parseInt(e.target.value, 10))}>
            {[1, 2, 3, 4].map((t) => (
              <option key={t} value={t}>
                T{t}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="layout">
        <div>
          {error && <p className="error">Error: {String(error)}</p>}
          {!error && (!iva || !modelo130) && <p className="muted">Cargando...</p>}

          {iva && modelo130 && (
            <>
              <section className="card">
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

              <section className="card">
                <h2>IRPF · pago fraccionado (modelo 130)</h2>
                <p>
                  Rendimiento neto del trimestre (tras cuota de autónomos):{" "}
                  {modelo130.rendimiento_neto_trimestre.toFixed(2)} €
                </p>
                <p>Rendimiento neto acumulado en el año: {modelo130.rendimiento_neto_acumulado.toFixed(2)} €</p>
                <p>
                  <strong>A ingresar: {modelo130.resultado.toFixed(2)} €</strong>
                </p>
              </section>

              <section className="card">
                <h2>Cómputo total de impuestos a abonar</h2>
                <table>
                  <tbody>
                    <tr>
                      <td>IVA (modelo 303)</td>
                      <td>{iva.resultado.toFixed(2)} €</td>
                    </tr>
                    <tr>
                      <td>IRPF (modelo 130)</td>
                      <td>{modelo130.resultado.toFixed(2)} €</td>
                    </tr>
                  </tbody>
                </table>
                <p style={{ marginTop: 12 }}>
                  <strong>
                    Total: {(iva.resultado + modelo130.resultado).toFixed(2)} € (
                    {iva.resultado + modelo130.resultado >= 0 ? "a ingresar" : "a favor / a compensar"})
                  </strong>
                </p>
                {iva.resultado + modelo130.resultado < 0 && (
                  <p className="muted">
                    Un IVA negativo no se cobra en el momento: se compensa en trimestres posteriores (o se solicita
                    su devolución en el cuarto trimestre).
                  </p>
                )}
              </section>
            </>
          )}
        </div>

        <aside>
          <ResumenRenta anio={anio} />
        </aside>
      </div>
    </div>
  );
}
