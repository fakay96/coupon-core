import { GoogleOAuthProvider } from "@react-oauth/google";

 const GooogleProvider = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const clientId = import.meta.env.VITE_GOOGLE_API_CLIENT_ID
  return (
    <GoogleOAuthProvider clientId={clientId}>
      {children}
    </GoogleOAuthProvider>
  );
};

export default GooogleProvider
