import type { NextConfig } from "next";
import path from "path";
import { fileURLToPath } from "url";

const appDir = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  // Standalone output for production Docker (node server.js). Not a static export.
  output: "standalone",
  // Keep standalone layout flat (`server.js` at `.next/standalone/`) even inside the monorepo.
  outputFileTracingRoot: appDir,
  poweredByHeader: false,
  reactStrictMode: true,
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
