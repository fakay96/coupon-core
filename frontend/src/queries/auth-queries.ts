import {
  getUserInfo,
  loginUserService,
  registerUserService,
  resendEmailVerificationToken,
  resendPasswordVerificationToken,
  updateUserProfile,
  verifyEmailToken,
} from "@/api/authApi";
import { geodiscountApi } from "@/api/geoDiscountApi";
import { loginCredentials, RegisterUserData } from "@/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

/**
 * Custom hook to fetch authenticated user information
 * @returns {UseQueryResult} Query result containing user information
 * @throws {Error} If user info fetch fails
 * @example
 * const { data: userInfo, isLoading } = getUserInfoQuery();
 */
export const getUserInfoQuery = () => {
  return useQuery({
    queryKey: ["userInfo"],
    queryFn: async () => await getUserInfo(),
    refetchOnWindowFocus: false,
    retry: false,
    gcTime: 1 * 60 * 60 * 1000,
    staleTime: 1 * 60 * 60 * 1000,
  });
};

/**
 * Custom hook to handle user login mutation
 * @returns {UseMutationResult} Mutation result for login operation
 * @throws {Error} If login fails
 * @example
 * const { mutate: login, isLoading } = loginUserMutation();
 * login({ email: 'user@example.com', password: '123456' });
 */ export const loginUserMutation = () => {
  const queryClient = useQueryClient();
  return useMutation<unknown, Error, loginCredentials>({
    mutationKey: ["loginUserMutation"],
    mutationFn: async (value: loginCredentials) =>
      await loginUserService(value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["userInfo"] });
    },
  });
};

/**
 * Custom hook to handle user registration mutation
 * @returns {UseMutationResult} Mutation result for registration operation
 * @throws {Error} If registration fails
 * @example
 * const { mutate: register, isLoading } = registerUserMutation();
 * register({ email: 'user@example.com', password: '123456', name: 'John Doe' });
 */
export const registerUserMutation = () => {
  const queryClient = useQueryClient();
  return useMutation<unknown, Error, RegisterUserData>({
    mutationKey: ["registerUserMutation"],
    mutationFn: async (value) => await registerUserService(value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["userInfo"] });
    },
  });
};

export const retryEmailTokenMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationKey: ["retryEmailTokenMutation"],
    mutationFn: async (value: { email: string; force_resend: boolean }) =>
      await resendEmailVerificationToken(value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["userInfo"] });
    },
  });
};

export const retryPasswordTokenMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationKey: ["retryPasswordTokenMutation"],
    mutationFn: async (value: { password: string; force_resend: boolean }) =>
      await resendPasswordVerificationToken(value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["userInfo"] });
    },
  });
};

export const verifyEmailTokenMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationKey: ["verifyEmailTokenMutation"],
    mutationFn: async (value: { email: string; token: string }) =>
      await verifyEmailToken(value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["userInfo"] });
    },
  });
};


export const updateUserProfileMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationKey: ["updateUserProfileMutation"],
    mutationFn: async (value: any) => await updateUserProfile(value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["userInfo"] });
    },
  });
};


export const geodiscountApiMutation = () => {
  // const queryClient = useQueryClient();
  return useMutation({
    mutationKey: ["geodiscountApiMutation"],
    mutationFn: async (value: any) => await geodiscountApi(value),
    // onSuccess: () => {
    //   queryClient.invalidateQueries({ queryKey: ["userInfo"] });
    // },
  });
};
