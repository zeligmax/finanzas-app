import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Link, NavLink } from "react-router-dom";
import api, { clienteActivoGuardado } from "./api/client";
import TaxesPage from "./pages/TaxesPage";
import RentaPage from "./pages/RentaPage";
import DocumentsPage from "./pages/DocumentsPage";
import UserPage from "./pages/UserPage";
import AccesoPage from "./pages/AccesoPage";
import ClientesPage from "./pages/ClientesPage";
import Login from "./pages/Login";
import Home from "./pages/Home";

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [perfil, setPerfil] = useState(null);
  const [clienteActivo, setClienteActivo] = useState(clienteActivoGuardado());

  const elegirCliente = (cliente) => {
    if (cliente) {
      localStorage.setItem("clienteActivo", JSON.stringify(cliente));
    } else {
      localStorage.removeItem("clienteActivo");
    }
    setClienteActivo(cliente);
  };

  useEffect(() => {
    if (token) {
      localStorage.setItem("token", token);
      api
        .get("/api/users/me")
        .then((res) => setPerfil(res.data))
        .catch((err) => {
          if (err.response?.status === 401) setToken(null);
        });
    } else {
      localStorage.removeItem("token");
      setPerfil(null);
    }
  }, [token]);

  const esGestor = perfil?.role === "gestor";

  useEffect(() => {
    if (perfil && !esGestor && clienteActivo) elegirCliente(null);
  }, [perfil]);

  const handleLogin = (nuevoToken) => {
    elegirCliente(null);
    setToken(nuevoToken);
  };

  const handleLogout = () => {
    elegirCliente(null);
    setToken(null);
  };

  const navClass = ({ isActive }) => (isActive ? "active" : undefined);

  const login = <Login onLogin={handleLogin} />;

  // Páginas de datos: un gestor necesita haber elegido a un cliente y las ve en solo lectura.
  const datos = (pagina) => {
    if (!token) return login;
    if (!perfil) return <p className="muted">Cargando...</p>;
    if (esGestor && !clienteActivo) {
      return (
        <div className="card">
          <h2>Elige un cliente</h2>
          <p className="muted">
            Para ver documentos, impuestos o Renta, elige primero a un cliente en <Link to="/clientes">Clientes</Link>.
          </p>
        </div>
      );
    }
    return (
      <>
        {esGestor && (
          <div className="banner">
            Viendo los datos de <strong>{clienteActivo.nombre || clienteActivo.email}</strong> · solo lectura ·{" "}
            <Link to="/clientes">Cambiar cliente</Link>
          </div>
        )}
        {pagina}
      </>
    );
  };

  return (
    <BrowserRouter>
      <div className="app">
        <header className="app-header">
          <h1>
            <Link to="/">Finanzas Autónomo</Link>
          </h1>
          <nav className="nav">
            <NavLink to="/" className={navClass}>
              Inicio
            </NavLink>
            {esGestor && (
              <NavLink to="/clientes" className={navClass}>
                Clientes
              </NavLink>
            )}
            <NavLink to="/documents" className={navClass}>
              Documentos
            </NavLink>
            <NavLink to="/taxes" className={navClass}>
              Impuestos
            </NavLink>
            <NavLink to="/renta" className={navClass}>
              Renta
            </NavLink>
            <NavLink to="/usuario" className={navClass}>
              Usuario
            </NavLink>
            {token && !esGestor && (
              <NavLink to="/acceso" className={navClass}>
                Gestor
              </NavLink>
            )}
            <NavLink to="/login" className={navClass}>
              Login
            </NavLink>
            {token && (
              <button className="secondary" onClick={handleLogout}>
                Cerrar sesión
              </button>
            )}
          </nav>
        </header>

        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/documents" element={datos(<DocumentsPage soloLectura={esGestor} />)} />
            <Route path="/taxes" element={datos(<TaxesPage />)} />
            <Route path="/renta" element={datos(<RentaPage />)} />
            <Route path="/usuario" element={token ? <UserPage /> : login} />
            <Route path="/acceso" element={token ? <AccesoPage /> : login} />
            <Route
              path="/clientes"
              element={
                token ? (
                  <ClientesPage esGestor={esGestor} clienteActivo={clienteActivo} onElegirCliente={elegirCliente} />
                ) : (
                  login
                )
              }
            />
            <Route path="/login" element={login} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
