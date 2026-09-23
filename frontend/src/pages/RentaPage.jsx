import { useState } from "react";
import useResumenAnual from "../hooks/useResumenAnual";

const anioActual = new Date().getFullYear();

export default function RentaPage() {
  const [anio, setAnio] = useState(anioActual);
  const { modelos130, renta, ivaAnual, totalPagosFraccionados, totalAnual, error } = useResumenAnual(anio);

  return (
    <div>
      <h1>Renta</h1>

      <div className="card">
        <label className="field" style={{ marginBottom: 0 }}>
          Año
          <input
            type="number"
            value={anio}
            onChange={(e) => setAnio(parseInt(e.target.value, 10) || anioActual)}
            style={{ width: 90 }}
          />
        </label>
      </div>

      {error && <p className="error">Error: {String(error)}</p>}
      {!error && (!modelos130 || !renta) && <p className="muted">Cargando...</p>}

      {modelos130 && (
        <section className="card">
          <h2>Modelo 130 · pagos fraccionados del año</h2>
          <table>
            <thead>
              <tr>
                {["Trimestre", "Rendimiento neto trim.", "Acumulado", "Resultado ingresado"].map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {modelos130.map((m) => (
                <tr key={m.trimestre}>
                  <td>T{m.trimestre}</td>
                  <td>{m.rendimiento_neto_trimestre.toFixed(2)} €</td>
                  <td>{m.rendimiento_neto_acumulado.toFixed(2)} €</td>
                  <td>{m.resultado.toFixed(2)} €</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ marginTop: 12 }}>
            <strong>Total pagos fraccionados ingresados en el año: {totalPagosFraccionados.toFixed(2)} €</strong>
          </p>
        </section>
      )}

      {renta && (
        <section className="card">
          <h2>Modelo 100 · declaración anual (estimación)</h2>
          <p>Base liquidable: {renta.base_liquidable.toFixed(2)} €</p>
          <p>Cuota íntegra: {renta.cuota_integra.toFixed(2)} €</p>
          <p>
            <strong>
              Resultado: {renta.resultado.toFixed(2)} € ({renta.a_pagar ? "a pagar" : "a devolver"})
            </strong>
          </p>
        </section>
      )}

      {renta && ivaAnual !== null && (
        <section className="card">
          <h2>Cómputo total de impuestos del año</h2>
          <table>
            <tbody>
              <tr>
                <td>IVA (suma de los 4 modelos 303)</td>
                <td>{ivaAnual.toFixed(2)} €</td>
              </tr>
              <tr>
                <td>IRPF ya ingresado (suma de los 4 modelos 130)</td>
                <td>{totalPagosFraccionados.toFixed(2)} €</td>
              </tr>
              <tr>
                <td>Declaración de la Renta (modelo 100)</td>
                <td>{renta.resultado.toFixed(2)} €</td>
              </tr>
            </tbody>
          </table>
          <p style={{ marginTop: 12 }}>
            <strong>
              Total: {totalAnual.toFixed(2)} € ({totalAnual >= 0 ? "a abonar" : "a favor / a compensar"})
            </strong>
          </p>
          {totalAnual < 0 && (
            <p className="muted">
              Un IVA negativo se compensa en trimestres posteriores o se solicita su devolución en el cuarto
              trimestre; no se cobra automáticamente.
            </p>
          )}
        </section>
      )}
    </div>
  );
}
