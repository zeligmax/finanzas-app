import { useNavigate } from "react-router-dom";
import Login from "./Login";

export default function LoginScreen({ onLogin }) {
  const navigate = useNavigate();

  return (
    <div className="app">
      <header className="app-header">
        <h1>Finanzas Autónomo</h1>
        <button className="secondary" onClick={() => navigate("/builder-login")}>
          Builder
        </button>
      </header>
      <main>
        <Login onLogin={onLogin} />
      </main>
    </div>
  );
}
