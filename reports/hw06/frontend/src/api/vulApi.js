import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8032",
  withCredentials: true,
});

// export async function fetchVuls() {
//   const res = await api.get("/vuls");
//   return res.data;
// }

export async function fetchVulById(id) {
  const res = await api.get(`/vuls/${id}`);
  return res.data;
}

// export async function createVul(payload) {
//   const res = await api.post("/vuls", payload);
//   return res.data;
// }

// export async function updateVul(id, payload) {
//   const res = await api.put(`/vuls/${id}`, payload);
//   return res.data;
// }

// export async function deleteVul(id) {
//   const res = await api.delete(`/vuls/${id}`);
//   return res.data;
// }
export async function fetchVendors() {
  const res = await api.get("/vendors");
  return res.data;
}
export async function createVendor(payload) {
  const res = await api.post("/vendors", payload);
  return res.data;
}
export async function login(email, password) {
  const res = await api.post("/auth/login", { email, password });
  return res.data;
}
export async function logout() {
  const res = await api.post("/auth/logout");
  return res.data;
}

export async function me() {
  const res = await api.get("/auth/me");
  return res.data;
}