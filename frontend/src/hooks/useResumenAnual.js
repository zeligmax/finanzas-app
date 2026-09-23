import { useEffect, useState } from "react";
import api from "../api/client";

export default function useResumenAnual(anio) {
  const [modelos130, setModelos130] = useState(null);
  const [renta, setRenta] = useState(null);
  const [ivaAnual, setIvaAnual] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelado = false;
    setError(null);
    setModelos130(null);
    setRenta(null);
    setIvaAnual(null);

    Promise.all([
      api.get(`/api/taxes/modelo130/${anio}`),
      api.get(`/api/taxes/renta/${anio}`),
      ...[1, 2, 3, 4].map((t) => api.get(`/api/taxes/iva/${anio}/${t}`)),
    ])
      .then(([m130Res, rentaRes, ...ivaRes]) => {
        if (cancelado) return;
        setModelos130(m130Res.data);
        setRenta(rentaRes.data);
        setIvaAnual(ivaRes.reduce((acc, r) => acc + r.data.resultado, 0));
      })
      .catch((err) => {
        if (!cancelado) setError(err.response?.data?.detail || err.message);
      });

    return () => {
      cancelado = true;
    };
  }, [anio]);

  const cargado = modelos130 !== null && renta !== null && ivaAnual !== null;
  const totalPagosFraccionados = modelos130 ? modelos130.reduce((acc, m) => acc + m.resultado, 0) : 0;
  const totalAnual = cargado ? ivaAnual + totalPagosFraccionados + renta.resultado : 0;

  return { modelos130, renta, ivaAnual, totalPagosFraccionados, totalAnual, cargado, error };
}
