import axios from "axios";
import { store } from "../redux/store";
import { refreshTokenThunk } from "../redux/authentication";

const API_URL = import.meta.env.VITE_API_BASE_URL;


const api = axios.create({
  baseURL: API_URL,
});

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // console.log("Interceptor - Error status:", error.response?.status, "URL:", error.config?.url);

    if (error.response?.status === 401 && !originalRequest._retry) {
      // console.log("401 detected, attempting token refresh");

      if (isRefreshing) {
        // console.log("Refresh in progress, queuing request:", originalRequest.url);
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            // console.log("Retrying with new token:", token);
            originalRequest.headers["Authorization"] = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => {
            console.error("Queued request failed:", err);
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { access } = await store.dispatch(refreshTokenThunk()).unwrap();
        // console.log("New access token:", access);

        api.defaults.headers.common["Authorization"] = `Bearer ${access}`;
        originalRequest.headers["Authorization"] = `Bearer ${access}`;
        // console.log("Retrying original request:", originalRequest.url);
        processQueue(null, access);

        return api(originalRequest);
      } catch (refreshError) {
        // console.error("Token refresh failed:", refreshError);
        processQueue(refreshError, null);
        store.dispatch({ type: "auth/logout" });
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    // console.error("Non-401 error or retry failed:", error.message);
    return Promise.reject(error);
  }
);

export default api;