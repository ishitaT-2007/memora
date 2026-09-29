import type { IncomingMessage, ServerResponse } from "node:http";
import { defineConfig, type ProxyOptions } from "vite";
import react from "@vitejs/plugin-react";

const apiProxy: ProxyOptions = {
  target: "http://127.0.0.1:8000",
  changeOrigin: true,
  configure(proxy) {
    proxy.on("error", (_err, _req: IncomingMessage, res) => {
      const response = res as ServerResponse;
      if (response && !response.headersSent && typeof response.writeHead === "function") {
        response.writeHead(502, { "Content-Type": "application/json" });
        response.end(
          JSON.stringify({
            message: "API returned empty response. Is the backend running on port 8000?",
          })
        );
      }
    });
  },
};

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": apiProxy,
    },
  },
});
