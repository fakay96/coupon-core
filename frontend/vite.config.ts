import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Vite configuration file
export default defineConfig({
  plugins: [react()], // Enables React support
  envDir: './env', // Specify the directory containing your .env files]

  
  server: {
  host: true, // Allows network access to the dev server
  // proxy: {
  //   "/api": {
  //     target: "https://api.dishpal.ai", // Redirects API requests to the backend
  //     changeOrigin: true, // Modifies the origin header for CORS handling
  //   },
  // },
  },

  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"), // Creates a shorthand for importing from "src"
    },
  },
});
