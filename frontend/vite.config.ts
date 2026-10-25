import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Dev rejimida /api so'rovlari Django serveriga yo'naltiriladi, shuning uchun CORS kerak emas.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
