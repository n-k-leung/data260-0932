import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, me } from "../api/vulApi.js";

export default function Login({ setAuth }) {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await login(username, password);
      const data = await me();
      setAuth({
        checked: true,
        loggedIn: true,
        username: data.username,
        role: data.role,
      });
        navigate("/");
      } catch {
        setError("Invalid username or password.");
      }
    }

return (
      <div className="card">
        <div className="card-header">
          <div className="page-title">Login</div>
          <div className="subtitle">Log in to view and manage vulnerability records</div>
        </div>

        <div className="card-body">
          <form className="form" onSubmit={handleSubmit}>
            <label>
              Username
              <input value={username} onChange={(e) => setUsername(e.target.value)} />
            </label>

            <label>
              Password

              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)} />
            </label>

            {error && <div className="notice">{error}</div>}

            <button className="btn primary" type="submit">
              Login
            </button>
          </form>
        </div>
      </div>
    );
  }