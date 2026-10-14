// The page is a static export: Vercel serves it from its CDN, and /api/* goes to the Python
// function (vercel.json). In `next dev` the same paths are proxied to a local API on port 8000.
const dev = process.env.NODE_ENV === "development";

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: dev ? undefined : "export",
  reactStrictMode: true,
  poweredByHeader: false,
  ...(dev && {
    async rewrites() {
      return [{ source: "/api/:path*", destination: "http://127.0.0.1:8000/api/:path*" }];
    },
  }),
};

export default nextConfig;
