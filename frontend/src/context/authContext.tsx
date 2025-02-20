import React, { createContext, useContext, useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { authContextDefault } from "@/constants";
import { authContextType, userT } from "@/types";
import Cookies from "js-cookie";
import { getUserInfoQuery } from "@/queries/auth-queries";
import { useNavigate } from "react-router-dom";

// Create an AuthContext with a default value
const AuthContext = createContext<authContextType>(authContextDefault);

// AuthProvider component to provide authentication context to its children
export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<userT | null | undefined>(undefined);
  const navigate = useNavigate();
  const { isLoading, data, isFetched, isError } = getUserInfoQuery();

  // Effect to update the user state based on the query result
  useEffect(() => {
    if (data && isFetched) {
      setUser(data);
    }
    if (isError) setUser(null);
  }, [isFetched, isLoading, data]);

  // Logout function to clear user data, cookies, and navigate to login page
  const logout = () => {
    setUser(null);
    queryClient.clear();
    Cookies.remove("access", { path: "/" });
    Cookies.remove("refresh", { path: "/" });
    navigate("/auth/login", { replace: true });
  };

  // Values to be provided by the AuthContext
  const values = { user, logout, isLoading, setUser };

  return <AuthContext.Provider value={values}>{children}</AuthContext.Provider>;
};

// Custom hook to use the AuthContext
export const useAuth = () => {
  return useContext(AuthContext);
};
