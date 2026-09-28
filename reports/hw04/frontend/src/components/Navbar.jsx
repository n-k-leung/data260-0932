import React from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";

export default function Navbar({ auth }) {
  const navigate = useNavigate();

  function handleAddClick(e) {
    if (!auth.loggedIn) {
      e.preventDefault();
      alert("Please login first to add a user.");
      return;
    }
    navigate("/create");
  }

  async function handleLogout() {
    await logout();
    setAuth({ loggedIn: false, userId: null });
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

        {/* Guarded Add User */}
        <a
          href="/create"
          onClick={handleAddClick}
          className={auth.loggedIn ? "" : "disabled-link"}
          aria-disabled={!auth.loggedIn}
        >
          Add Vulnerability Record
        </a>
        {auth. loggedIn ? (
          <a href="#" onClick={(e) => {e.preventDefault(); handleLogout(); }}>
          Logout
          </a>) : (
            <NavLink to="/login" className={({ isActive }) => (isActive ? "active" : "")}>
            Login
            </NavLink>
          )
        }
      </nav>
    </header>
  );
}