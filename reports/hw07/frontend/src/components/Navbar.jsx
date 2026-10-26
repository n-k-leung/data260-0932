import React from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { logout } from "../api/vulApi.js";
import { canWrite } from "../roles.js";

export default function Navbar({ auth, setAuth }) {
  const navigate = useNavigate();
  const mayAdd = auth.loggedIn && canWrite(auth.role);

  function handleAddClick(e) {
    e.preventDefault();
    if (!auth.loggedIn) {
      alert("Please login first to add a record.");
      return;
    }
    if (!mayAdd) {
      alert("Your role (" + auth.role + ") cannot add records.");
      return;
    }
    navigate("/create");
  }
  function handleLogout() {
    logout();
    setAuth({ checked: true, loggedIn: false, username: null, role: null });
    navigate("/login");
  }
  return (
    <header className="navbar">
      <Link className="brand" to="/">
        <span className="brand-badge" />
        Open Source Package Vulnerability Manager
      </Link>

      <nav className="navlinks">
        <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
          Home
        </NavLink>
        <NavLink to="/vendors" className={({ isActive }) => (isActive ? "active" : "")}>
          Vendors
        </NavLink>
        <a
          href="/create"
          onClick={handleAddClick}
          className={mayAdd ? "" : "disabled-link"}
          aria-disabled={!mayAdd}
        >
          Add Vulnerability Record
        </a>
        {auth.loggedIn ? (
          <>
            <span style={{ opacity: 0.8 }}>
              {auth.username} ({auth.role})
            </span>
            <a href="#" onClick={(e) => { e.preventDefault(); handleLogout(); }}>
              Logout
            </a>
          </>
        ) : (
          <NavLink to="/login" className={({ isActive }) => (isActive ? "active" : "")}>
            Login
          </NavLink>
        )}
      </nav>
    </header>
  );
}