import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // -------------------------------------------------------------
      // OPTION 1: Google Colab Cloud GPU Backend (Active)
      // -------------------------------------------------------------
      "/api": {
        target: "https://hash-phoniness-freely.ngrok-free.dev",
        changeOrigin: true,
        secure: false,
        headers: {
          "ngrok-skip-browser-warning": "true",
        },
        timeout: 300000,
      },
      "/ws": {
        target: "wss://hash-phoniness-freely.ngrok-free.dev",
        ws: true,
        secure: false,
        changeOrigin: true,
      },

      // -------------------------------------------------------------
      // OPTION 2: Local Backend Server (Uncomment for Local Python Server)
      // -------------------------------------------------------------
      // "/api": {
      //   target: "http://localhost:8000",
      //   changeOrigin: true,
      //   timeout: 300000,
      // },
      // "/ws": {
      //   target: "ws://localhost:8000",
      //   ws: true,
      // },
    },
  },
});
