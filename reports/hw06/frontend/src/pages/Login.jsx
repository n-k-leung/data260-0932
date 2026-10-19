import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api/vulApi.js";

export default function Login({ setAuth }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      const res = await login(email, password);
      setAuth({ loggedIn: true, userId: res.user_id });
      navigate("/");
    } catch (err) {
      setError("Invalid email or password.");
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
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)} />

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