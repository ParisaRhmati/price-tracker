/** @type {import('next').NextConfig} */

// API calls go to a RELATIVE /api/ path; Next.js rewrites them to the local
// Django backend. This means one ngrok URL serves both the pages and the API.
const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,

  // IMPORTANT: do NOT use `trailingSlash: true` here. That option made Next.js
  // rewrite/redirect proxied /api/ paths in a way that dropped the trailing
  // slash on the request actually sent to Django, which then answered 301 and
  // broke fetch() over ngrok ("Failed to fetch").
  //
  // Instead we tell Next.js to leave trailing slashes exactly as the client
  // sent them and not issue its own redirects. The frontend API client already
  // includes the trailing slash (e.g. /api/products/), so Django receives the
  // slash and responds 200 directly - no redirect, no broken fetch.
  skipTrailingSlashRedirect: true,

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
