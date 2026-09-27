import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Link, NavLink, Navigate } from "react-router-dom";
import api, { clienteActivoGuardado } from "./api/client";
import TaxesPage from "./pages/TaxesPage";
import RentaPage from "./pages/RentaPage";
import DocumentsPage from "./pages/DocumentsPage";
import UserPage from "./pages/UserPage";
import AccesoPage from "./pages/AccesoPage";
import ClientesPage from "./pages/ClientesPage";
import ContactosPage from "./pages/ContactosPage";
import LoginScreen from "./pages/LoginScreen";
import BuilderLoginScreen from "./pages/BuilderLoginScreen";
import BuilderQueuePage from "./pages/BuilderQueuePage";
import BuilderReviewPage from "./pages/BuilderReviewPage";
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
  const esBuilder = perfil?.role === "builder";

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

  // Páginas de datos: un gestor necesita haber elegido a un cliente y las ve en solo lectura.
  const datos = (pagina) => {
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
      <Routes>
        {!token && (
          <>
            <Route path="/builder-login" element={<BuilderLoginScreen onLogin={handleLogin} />} />
            <Route path="*" element={<LoginScreen onLogin={handleLogin} />} />
          </>
        )}

        {token && !perfil && (
          <Route
            path="*"
            element={
              <div className="app">
                <p className="muted">Cargando...</p>
              </div>
            }
          />
        )}

        {token && perfil && esBuilder && (
          <Route
            path="*"
            element={
              <div className="app">
                <header className="app-header">
                  <h1>
                    <Link to="/builder">Finanzas Autónomo · Builder</Link>
                  </h1>
                  <nav className="nav">
                    <NavLink to="/builder" className={navClass} end>
                      Cola
                    </NavLink>
                    <button className="secondary" onClick={handleLogout}>
                      Cerrar sesión
                    </button>
                  </nav>
                </header>
                <main>
                  <Routes>
                    <Route path="/builder" element={<BuilderQueuePage />} />
                    <Route path="/builder/:id" element={<BuilderReviewPage />} />
                    <Route path="*" element={<Navigate to="/builder" replace />} />
                  </Routes>
                </main>
              </div>
            }
          />
        )}

        {token && perfil && !esBuilder && (
          <Route
            path="*"
            element={
              <div className="app">
                <header className="app-header">
                  <h1>
                    <Link to="/">Finanzas Autónomo</Link>
                  </h1>
                  <nav className="nav">
                    <NavLink to="/" className={navClass} end>
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
                    {!esGestor && (
                      <NavLink to="/contactos" className={navClass}>
                        Contactos
                      </NavLink>
                    )}
                    <NavLink to="/taxes" className={navClass}>
                      Impuestos
                    </NavLink>
                    <NavLink to="/renta" className={navClass}>
                      Renta
                    </NavLink>
                    <NavLink to="/usuario" className={navClass}>
                      Usuario
                    </NavLink>
                    {!esGestor && (
                      <NavLink to="/acceso" className={navClass}>
                        Gestor
                      </NavLink>
                    )}
                    <button className="secondary" onClick={handleLogout}>
                      Cerrar sesión
                    </button>
                  </nav>
                </header>
                <main>
                  <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/documents" element={datos(<DocumentsPage soloLectura={esGestor} perfil={perfil} />)} />
                    <Route path="/contactos" element={<ContactosPage />} />
                    <Route path="/taxes" element={datos(<TaxesPage />)} />
                    <Route path="/renta" element={datos(<RentaPage />)} />
                    <Route path="/usuario" element={<UserPage />} />
                    <Route path="/acceso" element={<AccesoPage />} />
                    <Route
                      path="/clientes"
                      element={
                        <ClientesPage esGestor={esGestor} clienteActivo={clienteActivo} onElegirCliente={elegirCliente} />
                      }
                    />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </main>
              </div>
            }
          />
        )}
      </Routes>
    </BrowserRouter>
  );
}
