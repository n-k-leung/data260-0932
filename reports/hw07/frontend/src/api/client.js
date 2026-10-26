import axios from "axios";
const client = axios.create({
  baseURL: "http://localhost:8032",
});

//make sure bearer token is saved bc need for authentication
client.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLoginRequest = error.config && error.config.url === "/auth/login";
    if (error.response && error.response.status === 401 && !isLoginRequest) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export function errorText(err) {
  const status = err.response && err.response.status;
  if (status === 403) {
    return "You do not have permission to do this (403).";
  }
  const detail = err.response && err.response.data && err.response.data.detail;
  if (typeof detail === "string") {
    return detail;
  }
  return "Request failed. Please check the input fields.";
}

export default client;
// import axios from "axios";

// const client = axios.create({ baseURL: "http://localhost:8032",});
// client.interceptors.request.use((config) => {
//     const token = localStorage.getItem("token");
//     if (token)
//         config.headers.Authorization = `Bearer ${token}`;
//     return config;
// });

// client.interceptors.response.use(
//     (response) => response,
//     (error) => {
//     const isLoginRequest = error.config && error.config.url === "/auth/login";
//     if (error.response && error.response.status === 401 && !isLoginRequest) {
//         localStorage.removeItem("token");
//         window.location.href = "/login";
//     }
//     return Promise.reject(error);
//     }
// );
// export function errorText(err) {
//     const status = err.response && err.response.status;
//     if (status === 403) 
//         return "You do not have permission to do this (403).";

//     const detail = err.response && err.response.data && err.response.data.detail;
//     if (typeof detail === "string") 
//         return detail;

//     return "Request failed. Please check the input fields.";
// }
// export default client;