import axios from 'axios';
import store from '../store';
import { refreshTokenThunk, logout } from '../redux/authSlice';

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
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const result = await store.dispatch(refreshTokenThunk());

        if (refreshTokenThunk.fulfilled.match(result)) {
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
