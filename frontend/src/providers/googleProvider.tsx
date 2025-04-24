import { GoogleOAuthProvider } from "@react-oauth/google";
import { FC, ReactNode } from "react";

interface GoogleProviderProps {
  children: ReactNode;
}

/**
 * GoogleAuthProvider component that wraps the application with Google OAuth functionality
 * Provides Google authentication context to child components
 * Fails gracefully if client ID is not available
 *
 * @param {GoogleProviderProps} props - Component props containing children
 * @returns {JSX.Element | ReactNode} Wrapped children with Google OAuth context or children without context
 */


const GoogleAuthProvider: FC<GoogleProviderProps> = ({ children }: GoogleProviderProps): JSX.Element | ReactNode => {
  const clientId = import.meta.env.VITE_GOOGLE_API_CLIENT_ID;

  // If clientId is not available, render children without Google OAuth context
  if (!clientId) {
    console.warn('Google OAuth client ID is not configured. Google authentication will not be available.');
    return <>{children}</>;
  }

  return (
    <GoogleOAuthProvider clientId={clientId}>
      {children}
    </GoogleOAuthProvider>
  );
};

export default GoogleAuthProvider;
