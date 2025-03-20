import axiosInstance from "@/api/axiosClient";
import { loginCredentials, RegisterUserData } from "@/types";
import { TokenResponse } from "@react-oauth/google";
import axios from "axios";

/**
 * Authenticates user with provided credentials
 * @param credentials User login credentials containing email and password
 * @returns Promise containing authentication tokens and user data
 * @throws {ApiError} If authentication fails
 */
export const loginUserService = async (credentials: loginCredentials) => {
  const response = await axiosInstance.post(
    "/api/authentication/v1/login/",
    credentials
  );
  return response.data;
};

/**
 * Updates the authenticated user's profile information
 * @param userProfile Object containing user profile data to update
 * @returns Promise containing updated user profile data
 * @throws {ApiError} If update fails or user is not authenticated
 */
export const updateUserProfile = async (userProfile: any) => {
  console.log(userProfile);
  const response = await axiosInstance.put(
    "/api/authentication/v1/user-profile/",
    userProfile
  );
  return response.data;
};

/**
 * Registers a new user in the system
 * @param data User registration data including email, password and profile info
 * @returns Promise containing new user data
 * @throws {ApiError} If registration fails or validation errors occur
 */
export const registerUserService = async (
  data: RegisterUserData
): Promise<any> => {
  const response = await axiosInstance.post(
    "/api/authentication/v1/register/",
    data
  );
  return response.data;
};

/**
 * Permanently deletes the authenticated user's account
 * @returns Promise indicating successful deletion
 * @throws {ApiError} If deletion fails or user is not authenticated
 */
export const DeleteUserAccountService = async (): Promise<any> => {
  const response = await axiosInstance.delete(
    "/api/authentication/v1/user-delete/"
  );
  return response.data;
};

/**
 * Refreshes the authentication token using a refresh token
 * @param refresh Valid refresh token
 * @returns Promise containing new access token
 * @throws {ApiError} If refresh fails or token is invalid
 */
export const tokenRefresh = async (refresh: string) => {
  const response = await axiosInstance.post(
    "/api/authentication/v1/token/refresh/",
    { refresh }
  );
  return response;
};

/**
 * Generates a guest access token for limited system access
 * @param email Guest user email address
 * @returns Promise containing guest access token
 * @throws {ApiError} If token generation fails
 */
export const getGuestToken = async (email: string) => {
  const response = await axiosInstance.post(
    "/api/authentication/v1/guest-token/",
    email
  );
  return response.data;
};

/**
 * Retrieves basic information about the authenticated user
 * @returns Promise containing user information
 * @throws {ApiError} If fetching fails or user is not authenticated
 */
export const getUserInfo = async () => {
  const response = await axiosInstance.get(
    "/api/authentication/v1/user-profile/"
  );
  return response.data;
};

/**
 * Retrieves detailed profile information of the authenticated user
 * @returns Promise containing user profile data
 * @throws {ApiError} If fetching fails or user is not authenticated
 */
export const getUserProfile = async () => {
  const response = await axiosInstance.get(
    "/api/authentication/v1/user-profile/"
  );
  return response.data;
};

/**
 * Completes user registration process with additional data
 * @param data Additional user registration information
 * @returns Promise containing completed registration data
 * @throws {ApiError} If registration completion fails
 */
export const userRegistration = async (data: {
  email: string;
  password: string;
  confirm_password: string;
}) => {
  const response = await axiosInstance.post(
    "/api/authentication/v1/user-registration/",
    data
  );
  return response.data;
};

export const resendVerificationToken = async (data: {
  email: string;
  force_resend: boolean; // default it to true.
}) => {
  const response = await axiosInstance.put(
    "/api/authentication/v1/activate/",
    data
  );
  return response.data;
};

export const verifyEmailToken = async ({
  email,
  token,
}: {
  email: string;
  token: string; // default it to true.
}) => {
  const response = await axiosInstance.get(
    `/api/authentication/v1/activate/?email=${email}&token=${token}`
  );
  return response.data;
};

/**
 * Retrieves user information from Google OAuth API
 * @param tokenResponse Google OAuth token response containing access token
 * @returns Promise containing Google user information
 * @throws {ApiError} If Google API request fails or token is invalid
 */
export const axiosGoogleLogin = async (tokenResponse: TokenResponse) => {
  const { data } = await axios.get(
    "https://www.googleapis.com/oauth2/v3/userinfo",
    {
      headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
    }
  );
  return data;
};
