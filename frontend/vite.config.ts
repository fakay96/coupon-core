import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
import dotenv from "dotenv";
import fs from "fs";

// Load OS environment variables first
dotenv.config();

// Check if the "./env" directory exists before trying to load
const envDirPath = path.resolve(__dirname, './env');
const env = fs.existsSync(envDirPath) ? loadEnv(process.env.NODE_ENV as string, envDirPath) : process.env;


export default defineConfig({
  plugins: [react()], // Enables React support
  envDir: './env', // Specify the directory containing your .env files

  define: {
    'import.meta.env.VITE_API_URL': JSON.stringify(env.VITE_API_URL || process.env.VITE_API_URL),
  },

  server: {
    host: true, 
  },

  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"), // Creates a shorthand for importing from "src"
    },
  },
});
