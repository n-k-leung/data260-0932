import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8032",
  withCredentials: true,
});

export async function fetchVuls() {
  const res = await api.get("/vuls");
  return res.data;
}

export async function fetchVulById(id) {
  const res = await api.get(`/vuls/${id}`);
  return res.data;
}

export async function createVul(payload) {
  const res = await api.post("/vuls", payload);
  return res.data;
}

export async function updateVul(id, payload) {
  const res = await api.put(`/vuls/${id}`, payload);
  return res.data;
}

export async function deleteVul(id) {
  const res = await api.delete(`/vuls/${id}`);
  return res.data;
}