import axios from "axios";
import Cookies from "js-cookie";
import { tokenRefresh } from "@/api/authApi";
import { queryClient } from "@/providers/queryclientProvider";

// Base URL for the API
const apiUrl = import.meta.env.VITE_API_URL;

// Create an axios instance with the base URL
const api = axios.create({
  baseURL: apiUrl,
});

// Request interceptor to add the Authorization header with the access token
api.interceptors.request.use(
  (config) => {
    const accessToken = Cookies.get("access");
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) =>
    Promise.reject({
      message: error.response.data.error,
      status: error.response.status,
      statusText: error.response.statusText,
    })
);

let isRefreshing = false;

// Response interceptor to handle token refresh and error responses
api.interceptors.response.use(
  (response) => {
    // If the response contains a new access token, update the cookies and invalidate the user info query
    if (response?.data?.access) {
      Cookies.set("access", response?.data?.access, { expires: 1, path: "/" });
      Cookies.set("refresh", response?.data?.refresh, {
        expires: 1,
        path: "/",
      });
      queryClient.invalidateQueries({ queryKey: ["userInfo"] });
    }
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // If the response status is 401 (Unauthorized) and the request has not been retried yet
    if (error?.response?.status === 401 && !originalRequest._retry) {
      const refresh = Cookies.get("refresh");
      if (!refresh || isRefreshing) {
        return Promise.reject(error);
      }
      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Attempt to refresh the token using the refresh token
        const response = await tokenRefresh(refresh);
        if (response?.data.access) {
          // If the token refresh is successful, update the cookies and retry the original request
          Cookies.set("access", response?.data?.access, {
            expires: 1,
            path: "/",
          });
          Cookies.set("refresh", response?.data?.refresh, {
            expires: 1,
            path: "/",
          });
          queryClient.invalidateQueries({ queryKey: ["userInfo"] });
          originalRequest.headers[
            "Authorization"
          ] = `Bearer ${response?.data?.access}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // If the token refresh fails, clear the cookies and log a warning
        Cookies.remove("access", { path: "/" });
        Cookies.remove("refresh", { path: "/" });
        console.warn("Token refresh failed, clearing up now. Try again.");
      } finally {
        isRefreshing = false;
      }
    }
    // Return the error response with additional error information
    return Promise.reject({
      message: error.response.data.error,
      status: error.response.status,
      statusText: error.response.statusText,
    });
  }
);

export default api;
