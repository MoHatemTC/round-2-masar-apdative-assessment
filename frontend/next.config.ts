import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Required for the multi-stage Docker build: bundles a minimal server + only the node_modules
  // actually needed at runtime into .next/standalone, instead of shipping the whole node_modules.
  output: "standalone",
};

export default nextConfig;