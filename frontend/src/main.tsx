import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { BrowserRouter } from "react-router-dom";
import "./lib/i18n/i18n";
import ReactQueryClientProvider from "./providers/queryclientProvider.tsx";
import { AuthProvider } from "./context/authContext.tsx";
import { Toaster } from "sonner";
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN ?? "",
});

createRoot(document.getElementById("root")!).render(
  <ReactQueryClientProvider>
    <BrowserRouter>
      <AuthProvider>
        <Toaster richColors />
        <App />
      </AuthProvider>
    </BrowserRouter>
  </ReactQueryClientProvider>
);
