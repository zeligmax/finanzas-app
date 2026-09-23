import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Link, NavLink } from "react-router-dom";
import TaxesPage from "./pages/TaxesPage";
import RentaPage from "./pages/RentaPage";
import DocumentsPage from "./pages/DocumentsPage";
import UserPage from "./pages/UserPage";
import Login from "./pages/Login";
import Home from "./pages/Home";

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("token"));

  useEffect(() => {
    if (token) {
      localStorage.setItem("token", token);
    } else {
      localStorage.removeItem("token");
    }
  }, [token]);

  const handleLogout = () => setToken(null);

  const navClass = ({ isActive }) => (isActive ? "active" : undefined);

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
            <Route path="/documents" element={token ? <DocumentsPage /> : <Login onLogin={setToken} />} />
            <Route path="/taxes" element={token ? <TaxesPage /> : <Login onLogin={setToken} />} />
            <Route path="/renta" element={token ? <RentaPage /> : <Login onLogin={setToken} />} />
            <Route path="/usuario" element={token ? <UserPage /> : <Login onLogin={setToken} />} />
            <Route path="/login" element={<Login onLogin={setToken} />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
