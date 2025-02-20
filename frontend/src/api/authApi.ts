import axiosInstance from "@/api/axiosClient";
import { loginCredentials, RegisterUserData } from "@/types";
import { TokenResponse } from "@react-oauth/google";
import axios from "axios";

// POST: Login the registered user.
export const loginUserService = async (credentials: loginCredentials) => {
  // Sends login credentials to the server and returns the response data.
  const response = await axiosInstance.post(
    "/api/authentication/v1/login/",
    credentials
  );
  return response.data;
};

// POST: Register a new user.
export const registerUserService = async (
  data: RegisterUserData
): Promise<any> => {
  // Sends registration data to the server and returns the response data.
  const response = await axiosInstance.post(
    "/api/authentication/v1/register/",
    data
  );
  return response.data;
};

// Auth token refresh route.
export const tokenRefresh = async (refresh: string) => {
  // Sends a request to refresh the authentication token using the refresh token.
  const response = await axiosInstance.post(
    "/api/authentication/v1/token/refresh/",
    { refresh }
  );
  return response;
};

// GET: Obtain a guest token. TODO: This will be implemented in the future after I get updates from Ayodeji regarding the app design on figma.
export const getGuestToken = async (email: { email: string }) => {
  // Sends a request to obtain a guest token using the provided email.
  const response = await axiosInstance.post(
    "/api/authentication/v1/guest-token/",
    email
  );
  return response.data;
};

// GET: Fetch user information.
export const getUserInfo = async () => {
  // Sends a request to fetch the authenticated user's information.
  const response = await axiosInstance.get("/api/authentication/v1/user-info/");
  return response.data;
};

// GET: Fetch user profile.
export const getUserProfile = async () => {
  // Sends a request to fetch the authenticated user's profile.
  const response = await axiosInstance.get(
    "/api/authentication/v1/user-profile/"
  );
  return response.data;
};

// POST: Additional user registration endpoint.
export const userRegistration = async (data: any) => {
  // Sends additional user registration data to the server and returns the response data.
  const response = await axiosInstance.post(
    "/api/authentication/v1/user-registration/",
    data
  );
  return response.data;
};

// GET: Fetch Google user information.
export const axiosGoogleLogin = async (tokenResponse: TokenResponse) => {
  // Sends a request to fetch Google user information using the provided token.
  const { data } = await axios.get(
    "https://www.googleapis.com/oauth2/v3/userinfo",
    {
      headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
    }
  );
  return data;
};
