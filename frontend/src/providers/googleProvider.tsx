import { GoogleOAuthProvider } from "@react-oauth/google";

 const GooogleProvider = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  return (
    <GoogleOAuthProvider clientId="25081310509-c1csli88rd5u8f6uvdlb8v7bmqli5a51.apps.googleusercontent.com">
      {children}
    </GoogleOAuthProvider>
  );
};

export default GooogleProvider
