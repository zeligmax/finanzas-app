import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
});

const RUTAS_DE_DATOS = /^\/api\/(invoices|expenses|taxes)/;

export const clienteActivoGuardado = () => {
  try {
    return JSON.parse(localStorage.getItem("clienteActivo"));
  } catch {
    return null;
  }
};

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  // Un gestor que está viendo a un cliente solo lee: el parámetro se añade únicamente a los GET de datos.
  const cliente = clienteActivoGuardado();
  if (cliente && config.method === "get" && RUTAS_DE_DATOS.test(config.url || "")) {
    config.params = { ...config.params, cliente_id: cliente.id };
  }
  return config;
});

export default api;
