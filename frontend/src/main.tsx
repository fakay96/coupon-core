import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { BrowserRouter } from "react-router-dom";
import "./lib/i18n/i18n";
import ReactQueryClientProvider from "./providers/queryclientProvider.tsx";
import GooogleProvider from "./providers/googleProvider.tsx";
import { AuthProvider } from "./context/authContext.tsx";
import { Toaster } from 'sonner'

createRoot(document.getElementById("root")!).render(
  <ReactQueryClientProvider>
    <BrowserRouter>
      <AuthProvider>
          <GooogleProvider>
            <Toaster richColors  />
            <App />
          </GooogleProvider>
      </AuthProvider>
    </BrowserRouter>
  </ReactQueryClientProvider>
);
