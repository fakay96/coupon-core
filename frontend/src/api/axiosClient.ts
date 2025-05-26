import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import Cookies from "js-cookie";
import { tokenRefresh } from "@/api/authApi";
import { queryClient } from "@/providers/queryclientProvider";
import { toast } from "sonner";

// Base URL for the API
const apiUrl = import.meta.env.VITE_API_URL;

// List of public endpoints that don't require authentication
const publicEndpoints = [
  '/api/authentication/v1/login/',
  '/api/authentication/v1/register/',
  '/api/authentication/v1/guest-token/',
  '/api/geodiscounts/v1/discounts/',
  '/api/geodiscounts/v1/discounts/categories/',
  '/api/geodiscounts/v1/discounts/search/',
];

// Create an axios instance with the base URL
const api = axios.create({
  baseURL: apiUrl,
});

// Queue for storing requests that need to be retried after token refresh
let refreshSubscribers: ((token: string) => void)[] = [];

// Function to execute all queued requests with the new token
const onRefreshed = (token: string) => {
  refreshSubscribers.forEach((callback) => callback(token));
  refreshSubscribers = [];
};

// Function to add a request to the queue
const addRefreshSubscriber = (callback: (token: string) => void) => {
  refreshSubscribers.push(callback);
};

// Request interceptor to add the Authorization header with the access token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Check if the endpoint is public
    const isPublicEndpoint = publicEndpoints.some(endpoint => 
      config.url?.includes(endpoint)
    );

    // Only add auth header if not a public endpoint
    if (!isPublicEndpoint) {
      const accessToken = Cookies.get("access");
      if (accessToken) {
        config.headers.Authorization = `Bearer ${accessToken}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

let isRefreshing = false;

// Define error response type
interface ErrorResponse {
  message: string;
  [key: string]: any;
}

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
  async (error: AxiosError<ErrorResponse>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // If the response status is 401 (Unauthorized) and the request has not been retried yet
    if (error?.response?.status === 401 && !originalRequest._retry) {
      const refresh = Cookies.get("refresh");
      
      // If no refresh token or already refreshing, reject
      if (!refresh || isRefreshing) {
        // If already refreshing, queue this request
        if (isRefreshing) {
          return new Promise((resolve) => {
            addRefreshSubscriber((token: string) => {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              resolve(api(originalRequest));
            });
          });
        }
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
          
          // Execute all queued requests with the new token
          onRefreshed(response.data.access);
          
          // Retry the original request
          originalRequest.headers.Authorization = `Bearer ${response.data.access}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // If the token refresh fails, clear the cookies and notify user
        Cookies.remove("access", { path: "/" });
        Cookies.remove("refresh", { path: "/" });
        toast.error("Your session has expired. Please log in again.");
        
        // Redirect to login page if not already there
        if (!window.location.pathname.includes('/auth')) {
          window.location.href = '/auth/login';
        }
      } finally {
        isRefreshing = false;
      }
    }

    // Handle other errors
    const errorMessage = error.response?.data?.message || error.message || 'An error occurred';
    toast.error(errorMessage);

    return Promise.reject(error.response);
  }
);

export default api;
