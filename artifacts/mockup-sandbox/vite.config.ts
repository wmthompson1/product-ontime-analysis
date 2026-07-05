import http from "http";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";
import runtimeErrorOverlay from "@replit/vite-plugin-runtime-error-modal";
import { mockupPreviewPlugin } from "./mockupPreviewPlugin";

const rawPort = process.env.PORT;

if (!rawPort) {
  throw new Error(
    "PORT environment variable is required but was not provided.",
  );
}

const port = Number(rawPort);

if (Number.isNaN(port) || port <= 0) {
  throw new Error(`Invalid PORT value: "${rawPort}"`);
}

const basePath = process.env.BASE_PATH;

if (!basePath) {
  throw new Error(
    "BASE_PATH environment variable is required but was not provided.",
  );
}

const APP_BACKEND = process.env.APP_BACKEND_URL || "http://localhost:5000";

// Transparent pass-through: anything outside the mockup base path is served
// by the main app on port 5000 through this server (same URL, no redirect),
// so the bare-domain preview shows the app while /__mockup/* keeps serving
// canvas previews.
const appPassThroughPlugin = () => {
  const target = new URL(APP_BACKEND);
  const targetPort = target.port
    ? Number(target.port)
    : target.protocol === "https:"
      ? 443
      : 80;

  const isMockupPath = (pathname: string) =>
    pathname.startsWith(basePath) ||
    pathname.startsWith("/@") ||
    pathname.startsWith("/node_modules/");

  const forwardHeaders = (req: import("http").IncomingMessage) => ({
    ...req.headers,
    host: target.host,
    "x-forwarded-host":
      (req.headers["x-forwarded-host"] as string) || req.headers.host || "",
    "x-forwarded-proto":
      (req.headers["x-forwarded-proto"] as string) || "http",
    "x-forwarded-for":
      (req.headers["x-forwarded-for"] as string) ||
      req.socket.remoteAddress ||
      "",
  });

  return {
    name: "app-pass-through",
    configureServer(server: import("vite").ViteDevServer) {
      server.middlewares.use((req, res, next) => {
        const url = req.url || "/";
        if (isMockupPath(url.split("?")[0])) {
          return next();
        }
        const proxyReq = http.request(
          {
            hostname: target.hostname,
            port: targetPort,
            path: url,
            method: req.method,
            headers: forwardHeaders(req),
          },
          (proxyRes) => {
            res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
            proxyRes.pipe(res);
          },
        );
        proxyReq.on("error", () => {
          res.statusCode = 502;
          res.end("App on port 5000 is not responding.");
        });
        req.pipe(proxyReq);
      });

      // Forward WebSocket upgrades for non-mockup paths (Vite's own HMR
      // socket lives under the base path and is skipped here).
      server.httpServer?.on("upgrade", (req, socket, head) => {
        const pathname = (req.url || "/").split("?")[0];
        if (isMockupPath(pathname)) {
          return;
        }
        const proxyReq = http.request({
          hostname: target.hostname,
          port: targetPort,
          path: req.url,
          method: req.method,
          headers: forwardHeaders(req),
        });
        proxyReq.on("upgrade", (proxyRes, proxySocket, proxyHead) => {
          const lines = [
            `HTTP/1.1 ${proxyRes.statusCode} ${proxyRes.statusMessage}`,
          ];
          for (let i = 0; i < proxyRes.rawHeaders.length; i += 2) {
            lines.push(`${proxyRes.rawHeaders[i]}: ${proxyRes.rawHeaders[i + 1]}`);
          }
          socket.write(lines.join("\r\n") + "\r\n\r\n");
          if (proxyHead?.length) {
            socket.write(proxyHead);
          }
          proxySocket.pipe(socket);
          socket.pipe(proxySocket);
          proxySocket.on("error", () => socket.destroy());
          socket.on("error", () => proxySocket.destroy());
        });
        proxyReq.on("response", () => socket.destroy());
        proxyReq.on("error", () => socket.destroy());
        socket.on("error", () => proxyReq.destroy());
        if (head?.length) {
          socket.unshift(head);
        }
        proxyReq.end();
      });
    },
  };
};

export default defineConfig({
  base: basePath,
  plugins: [
    appPassThroughPlugin(),
    mockupPreviewPlugin(),
    react(),
    tailwindcss(),
    runtimeErrorOverlay(),
    ...(process.env.NODE_ENV !== "production" &&
    process.env.REPL_ID !== undefined
      ? [
          await import("@replit/vite-plugin-cartographer").then((m) =>
            m.cartographer({
              root: path.resolve(import.meta.dirname, ".."),
            }),
          ),
        ]
      : []),
  ],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "src"),
    },
  },
  root: path.resolve(import.meta.dirname),
  build: {
    outDir: path.resolve(import.meta.dirname, "dist"),
    emptyOutDir: true,
  },
  server: {
    port,
    strictPort: true,
    host: "0.0.0.0",
    allowedHosts: true,
    fs: {
      strict: true,
    },
    proxy: {
      "/mcp": {
        target: process.env.APP_BACKEND_URL || "http://localhost:5000",
        changeOrigin: true,
      },
    },
  },
  preview: {
    port,
    host: "0.0.0.0",
    allowedHosts: true,
  },
});
