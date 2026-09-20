import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import TaxesPage from "./pages/TaxesPage";
import RentaPage from "./pages/RentaPage";
import DocumentsPage from "./pages/DocumentsPage";
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

  return (
    <BrowserRouter>
      <div style={{ padding: 20, fontFamily: "Arial, sans-serif" }}>
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h1>
            <Link to="/">Finanzas Autónomo</Link>
          </h1>
          <nav>
            <Link to="/">Inicio</Link> | <Link to="/documents">Documentos</Link> |{" "}
            <Link to="/taxes">Impuestos</Link> | <Link to="/renta">Renta</Link> |{" "}
            <Link to="/login">Login</Link>
            {token && <button style={{ marginLeft: 8 }} onClick={handleLogout}>Cerrar sesión</button>}
          </nav>
        </header>

        <main style={{ marginTop: 20 }}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/documents" element={token ? <DocumentsPage /> : <Login onLogin={setToken} />} />
            <Route path="/taxes" element={token ? <TaxesPage /> : <Login onLogin={setToken} />} />
            <Route path="/renta" element={token ? <RentaPage /> : <Login onLogin={setToken} />} />
            <Route path="/login" element={<Login onLogin={setToken} />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
