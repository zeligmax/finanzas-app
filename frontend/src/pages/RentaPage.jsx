import { useEffect, useState } from "react";
import api from "../api/client";

const anioActual = new Date().getFullYear();

export default function RentaPage() {
  const [anio, setAnio] = useState(anioActual);
  const [modelos130, setModelos130] = useState(null);
  const [renta, setRenta] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setError(null);
    setModelos130(null);
    setRenta(null);
    Promise.all([api.get(`/api/taxes/modelo130/${anio}`), api.get(`/api/taxes/renta/${anio}`)])
      .then(([m130Res, rentaRes]) => {
        setModelos130(m130Res.data);
        setRenta(rentaRes.data);
      })
      .catch((err) => setError(err.response?.data?.detail || err.message));
  }, [anio]);

  const totalPagosFraccionados = modelos130 ? modelos130.reduce((acc, m) => acc + m.resultado, 0) : 0;

  return (
    <div>
      <h1>Renta</h1>

      <div style={{ marginBottom: 20 }}>
        <label>
          Año{" "}
          <input
            type="number"
            value={anio}
            onChange={(e) => setAnio(parseInt(e.target.value, 10) || anioActual)}
            style={{ width: 80 }}
          />
        </label>
      </div>

      {error && <p style={{ color: "crimson" }}>Error: {String(error)}</p>}
      {!error && (!modelos130 || !renta) && <p>Cargando...</p>}

      {modelos130 && (
        <section>
          <h2>Modelo 130 · pagos fraccionados del año</h2>
          <table style={{ borderCollapse: "collapse", width: "100%", marginBottom: 12 }}>
            <thead>
              <tr>
                {["Trimestre", "Rendimiento neto trim.", "Acumulado", "Resultado ingresado"].map((h) => (
                  <th key={h} style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: 4 }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {modelos130.map((m) => (
                <tr key={m.trimestre}>
                  <td style={{ padding: 4 }}>T{m.trimestre}</td>
                  <td style={{ padding: 4 }}>{m.rendimiento_neto_trimestre.toFixed(2)} €</td>
                  <td style={{ padding: 4 }}>{m.rendimiento_neto_acumulado.toFixed(2)} €</td>
                  <td style={{ padding: 4 }}>{m.resultado.toFixed(2)} €</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p>
            <strong>Total pagos fraccionados ingresados en el año: {totalPagosFraccionados.toFixed(2)} €</strong>
          </p>
        </section>
      )}

      {renta && (
        <section>
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
    </div>
  );
}
