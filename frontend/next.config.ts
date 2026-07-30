import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Required for the multi-stage Docker build: bundles a minimal server + only the node_modules
  // actually needed at runtime into .next/standalone, instead of shipping the whole node_modules.
  output: "standalone",

  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;