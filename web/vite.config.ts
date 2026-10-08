import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vite";

const server = "http://127.0.0.1:3000";

export default defineConfig({
  plugins: [svelte()],
  server: {
    fs: { allow: [".."] },
    proxy: {
      "/api": server,
      "/idiot.png": server,
      "/live": { target: server, ws: true },
    },
  },
});
