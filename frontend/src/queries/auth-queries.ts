// Import necessary functions and types from external modules
import {
  getUserInfo,
  loginUserService,
  registerUserService,
} from "@/api/authApi";
import { loginCredentials, RegisterUserData } from "@/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

// Define a query to fetch user information
export const getUserInfoQuery = () => {
  return useQuery({
    queryKey: ["userInfo"],
    queryFn: async () => await getUserInfo(),
    refetchOnWindowFocus: false,
    retry: false,
    gcTime: 1 * 60 * 60 * 1000, // Cache time: 1 hour
    staleTime: 1 * 60 * 60 * 1000, // Stale time: 1 hour
  });
};

// Define a mutation to handle user login
export const loginUserQuery = () => {
  const queryClient = useQueryClient();
  return useMutation<unknown, Error, loginCredentials>({
    mutationFn: async (value: loginCredentials) =>
      await loginUserService(value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["userInfo"] }); // Invalidate user info query on success
    },
  });
};

// Define a mutation to handle user registration
export const registerUserQuery = () => {
  const queryClient = useQueryClient();
  return useMutation<unknown, Error, RegisterUserData>({
    mutationFn: async (value) => await registerUserService(value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["userInfo"] }); // Invalidate user info query on success
    },
  });
};
