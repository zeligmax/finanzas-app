import { useEffect, useState } from "react";
import api from "../api/client";

export default function TaxesPage() {
  const anio = new Date().getFullYear();
  const trimestre = Math.ceil((new Date().getMonth() + 1) / 3);

  const [iva, setIva] = useState(null);
  const [modelo130, setModelo130] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      api.get(`/api/taxes/iva/${anio}/${trimestre}`),
      api.get(`/api/taxes/modelo130/${anio}/${trimestre}`),
    ])
      .then(([ivaRes, m130Res]) => {
        setIva(ivaRes.data);
        setModelo130(m130Res.data);
      })
      .catch((err) => setError(err.message));
  }, [anio, trimestre]);

  if (error) return <p>Error cargando impuestos: {error}</p>;
  if (!iva || !modelo130) return <p>Cargando...</p>;

  return (
    <div>
      <h1>
        Trimestre {trimestre} · {anio}
      </h1>

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
        <p>Rendimiento neto acumulado: {modelo130.rendimiento_neto_acumulado.toFixed(2)} €</p>
        <p>
          <strong>A ingresar: {modelo130.resultado.toFixed(2)} €</strong>
        </p>
      </section>
    </div>
  );
}
