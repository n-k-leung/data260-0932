import React, { useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import Home from "./pages/Home.jsx";
import CreateRecord from "./pages/CreateRecord.jsx";
import UpdateRecord from "./pages/UpdateRecord.jsx";
import DeleteRecord from "./pages/DeleteRecord.jsx";
import Login from "./pages/Login.jsx";
import Vendors from "./pages/Vendors.jsx";
import { me } from "./api/vulApi.js";
import { canWrite, canDelete } from "./roles.js";

function RequireAuth({ auth, allow, children }) {
  if (!auth.checked) {
    return <p>Checking login ...</p>;
  }
  if (!auth.loggedIn) {
    return (
      <div className="card">
        <div className="card-header">
          <div className="page-title">Login Required</div>
        </div>
        <div className="card-body">
          <div className="notice">Please login to access this page.</div>
        </div>
      </div>
    );
  }
  if (allow && !allow(auth.role)) {
    return (
      <div className="card">
        <div className="card-header">
          <div className="page-title">Not Allowed</div>
        </div>
        <div className="card-body">
          <div className="notice">
            Your role ( {auth.role}) does not have permission to open this page.
          </div>
        </div>
      </div>
    );
  }
  return children;
}

export default function App() {
  const [auth, setAuth] = useState({
    checked: false,
    loggedIn: false,
    username: null,
    role: null,
  });
  useEffect(() => {
    async function checkLogin() {
      if (!localStorage.getItem("token")) {
        setAuth({ checked: true, loggedIn: false, username: null, role: null });
        return;
      }
      try {
        const data = await me();
        setAuth({
          checked: true,
          loggedIn: true,
          username: data.username,
          role: data.role,
        })
      } catch {
        setAuth({ checked: true, loggedIn: false, username: null, role: null });
      }
    }
    checkLogin();
  }, []);

  return (
    <div className="container">
      <Navbar auth={auth} setAuth={setAuth} />

      <Routes>
        <Route path="/" element={<Home auth={auth} />} />
        <Route path="/login" element={<Login setAuth={setAuth} />} />
        <Route
          path="/create"
          element={<RequireAuth auth={auth} allow={canWrite}><CreateRecord /></RequireAuth>}
        />
        <Route
          path="/update/:id"
          element={<RequireAuth auth={auth} allow={canWrite}><UpdateRecord /></RequireAuth>}
        />
        <Route
          path="/delete/:id"
          element={<RequireAuth auth={auth} allow={canDelete}><DeleteRecord /></RequireAuth>}
        />
        <Route path="/vendors" element={<Vendors auth={auth} />} />
      </Routes>
    </div>
  );
}