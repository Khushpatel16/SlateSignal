import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "image.tmdb.org",
        pathname: "/t/p/**",
      },
    ],
  },
  async rewrites() {
    const apiOrigin = process.env.INFERENCE_API_URL ?? "http://127.0.0.1:8000";

    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiOrigin}/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
