import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";
export default defineConfig({
  plugins: [tailwindcss()],
  resolve: { alias: { "@": new URL("./src", import.meta.url).pathname } },
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
  build: {
    outDir: "dist",
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (/node_modules\/(react|react-dom|scheduler)\//.test(id)) return "react-vendor";
        },
      },
      onwarn(warning, warn) {
        // coss/Base UI retain React Server Component hints. This Vite app is entirely client-side.
        if (
          warning.code === "MODULE_LEVEL_DIRECTIVE" &&
          warning.message.includes("use client")
        )
          return;
        if (
          warning.code === "SOURCEMAP_ERROR" &&
          warning.id?.includes("/src/components/ui/") &&
          warning.message.includes("Can't resolve original location")
        )
          return;
        warn(warning);
      },
    },
  },
});
