import React, { useEffect, useState } from "react";
import { Routes, Route, useNavigate } from "react-router-dom";

import Navbar from "./components/Navbar.jsx";

import Home from "./pages/Home.jsx";
import CreateRecord from "./pages/CreateRecord.jsx";
import UpdateRecord from "./pages/UpdateRecord.jsx";
import DeleteRecord from "./pages/DeleteRecord.jsx";
import Login from "./pages/Login.jsx";
import Vendors from"./pages/Vendors.jsx";

import { me } from "./api/vulApi.js";

function RequireAuth({ auth, children }) {
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
  return children;
}

export default function App() {
  // Auth state (cookie session is checked inside LoginBar via /auth/me)
  const [auth, setAuth] = useState({ loggedIn: false, userId: null });

  useEffect(() => {
    (async () => {
      try {
        const data = await me();
        setAuth({ loggedIn: true, userId: data.user_id });
      }catch {
      setAuth({ loggedIn: false, userId: null });
      }
    })();
  }, []);

  // Fetch records only when logged in
  // useEffect(() => {
  //   (async () => {
  //     if (!auth.loggedIn) {
  //       setRecords([]);
  //       setLoading(false);
  //       return;
  //     }

  //     try {
  //       setLoading(true);
  //       const data = await fetchVuls();
  //       setRecords(data);
  //     } catch (e) {
  //       console.error("fetchVuls failed:", e);
  //       // If session expired, backend returns 401; UI will show not logged in after next /auth/me check.
  //     } finally {
  //       setLoading(false);
  //     }
  //   })();
  // }, [auth.loggedIn]);

  // // Create (props)
  // async function onAdd(newRecord) {
  //   const created = await createVul(newRecord);
  //   setRecords((prev) => [...prev, created]);
  //   navigate("/");
  // }

  // // Update (props)
  // async function onUpdate(id, updatedRecord) {
  //   const updated = await updateVul(id, updatedRecord);
  //   setRecords((prev) => prev.map((u) => (u.id === id ? updated : u)));
  //   navigate("/");
  // }

  // // Delete (props)
  // async function onDelete(id) {
  //   await deleteVul(id);
  //   setRecords((prev) => prev.filter((u) => u.id !== id));
  //   navigate("/");
  // }

  return (
    <div className="container">
      <Navbar auth={auth} setAuth={setAuth}/>

      {/* Login session demo UI */}
      {/* <LoginBar auth={auth} setAuth={setAuth} /> */}

      <Routes>
        <Route path="/" element={<Home auth={auth} />} />
        <Route path="/login" element={<Login setAuth={setAuth}/>}/>
        <Route path="/create" element={<RequireAuth auth={auth}> <CreateRecord /></RequireAuth> }/>
        <Route path="/update/:id" element={<RequireAuth auth={auth}><UpdateRecord/></RequireAuth>} />
        <Route path="/delete/:id" element={<RequireAuth auth={auth}> <DeleteRecord /></RequireAuth>} />
        <Route path="/vendors" element={<Vendors auth={auth}/>}/>
      </Routes>
    </div>
  );
}