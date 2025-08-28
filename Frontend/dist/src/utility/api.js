import axios from 'axios';
import {store} from "../redux/store"
import { logout, refreshTokenThunk } from '../redux/authentication';
import apiList from '../../api.json';


const API_URL = import.meta.env.VITE_API_BASE_URL;

const api = axios.create({
  baseURL: API_URL,
});

// Request interceptor → attach token
api.interceptors.request.use(
  (config) => {
    const state = store.getState();
    const token = state.auth.token;
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor → refresh token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
     console.log("❌ Interceptor caught error:", error.response?.status, error.config.url);
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      // Prevent infinite retry loop
      if (originalRequest.url.includes(apiList.auth.refresh)) {
        return Promise.reject(error);
      }

      originalRequest._retry = true;

      try {
        const result = await store.dispatch(refreshTokenThunk());

        if (refreshTokenThunk.fulfilled.match(result)) {
          // ✅ update token in headers
          originalRequest.headers['Authorization'] = `Bearer ${result.payload.access}`;
          return api(originalRequest);
        }
      } catch (err) {
        store.dispatch(logout());
      }
    }
    return Promise.reject(error);
  }
);

export default api;
